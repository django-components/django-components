"""
Tests for Phase 5c Chunk 5 HTML minification (feature 5c.14).

Focus on the load-bearing safety properties: the pass shrinks output but must
preserve <pre> whitespace and JSON-LD, and must degrade gracefully when
minify-html isn't installed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import lxml.html
from apps.docs.build.minify import minify_site

if TYPE_CHECKING:
    import pytest

PAGE = (
    "<!DOCTYPE html>\n<html>   <head>   <title>T</title>\n"
    '<script type="application/ld+json">{"@context": "https://schema.org", "@type": "TechArticle"}</script>\n'
    "</head>\n<body>\n"
    "<pre><code>def f(x):\n    return  x +  1\n</code></pre>\n"
    "<p>Some    prose   with   spaces.</p>\n"
    "</body>\n</html>\n"
)


def _write(tmp_path: Path, html: str = PAGE) -> Path:
    page = tmp_path / "index.html"
    page.write_text(html, encoding="utf-8")
    return page


def test_minify_shrinks_and_counts(tmp_path: Path) -> None:
    _write(tmp_path)
    out = minify_site(tmp_path)
    assert out.files == 1
    assert out.after < out.before and out.before > 0


def test_minify_preserves_pre_whitespace(tmp_path: Path) -> None:
    page = _write(tmp_path)
    minify_site(tmp_path)
    result = page.read_text()
    # The exact whitespace inside <pre><code> must survive (double spaces, indent).
    assert "def f(x):\n    return  x +  1\n" in result
    # ...while collapsible prose whitespace is reduced.
    assert "Some    prose   with   spaces." not in result


def test_minify_preserves_json_ld(tmp_path: Path) -> None:
    page = _write(tmp_path)
    minify_site(tmp_path)
    dom = lxml.html.fromstring(page.read_text())
    blocks = dom.xpath('//script[@type="application/ld+json"]')
    assert len(blocks) == 1
    data = json.loads(blocks[0].text_content())
    assert data["@type"] == "TechArticle" and data["@context"] == "https://schema.org"


def test_minify_skips_gracefully_when_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    page = _write(tmp_path)
    original = page.read_text()
    # Make `import minify_html` raise ImportError inside minify_site.
    monkeypatch.setitem(sys.modules, "minify_html", None)
    out = minify_site(tmp_path)
    assert out.skipped_reason == "minify-html-missing"
    assert out.files == 0
    assert page.read_text() == original  # untouched
