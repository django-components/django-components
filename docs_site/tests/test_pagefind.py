"""
Tests for the Phase 5a search retrieval layer (feature 5a.1).

Covers the three pieces that scope and feed the Pagefind index:

- the `boost:` front-matter field (apps/docs/build/frontmatter.py),
- the `data-pagefind-body` / `data-pagefind-weight` markup emitted by DocPage,
- the `run_pagefind` post-build runner (apps/docs/build/pagefind.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from apps.docs.build.frontmatter import DEFAULT_BOOST, parse_page
from apps.docs.build.pagefind import run_pagefind
from apps.docs.components.doc_page.doc_page import DocPage

# -- boost front-matter --------------------------------------------------------


def test_boost_defaults_to_neutral_weight() -> None:
    meta = parse_page("# Title\n\nBody.")
    assert meta.boost == DEFAULT_BOOST


def test_boost_parsed_from_frontmatter() -> None:
    meta = parse_page("---\nboost: 2.0\n---\n# Title\n\nBody.")
    assert meta.boost == 2.0


def test_boost_is_a_known_field_under_strict() -> None:
    # Strict mode (the CI guardrail) must accept `boost:` rather than reject it
    # as an unknown front-matter key.
    meta = parse_page("---\nboost: 0.5\n---\n# Title", strict=True)
    assert meta.boost == 0.5


# -- DocPage Pagefind markup ---------------------------------------------------


def test_article_always_carries_pagefind_body() -> None:
    html = DocPage.render(kwargs={"content_html": "<h1>X</h1><p>hi</p>", "title": "X"})
    assert "data-pagefind-body" in html


def test_weight_attribute_emitted_only_when_boosted() -> None:
    boosted = DocPage.render(kwargs={"content_html": "<h1>X</h1>", "title": "X", "boost": 2.0})
    assert 'data-pagefind-weight="2.0"' in boosted

    neutral = DocPage.render(kwargs={"content_html": "<h1>X</h1>", "title": "X"})
    assert "data-pagefind-weight" not in neutral


def test_chrome_is_excluded_from_the_indexed_body() -> None:
    # data-pagefind-body sits on the article, so the header/sidebar chrome is
    # outside the indexed region even though it is present in the page.
    html = DocPage.render(kwargs={"content_html": "<h1>X</h1>", "title": "X"})
    body_start = html.index("data-pagefind-body")
    assert "djc-header" in html  # chrome is rendered...
    assert html.index("djc-header") < body_start  # ...but before the indexed body opens


# -- run_pagefind runner -------------------------------------------------------


def test_run_pagefind_missing_dir_fails_gracefully(tmp_path: Path) -> None:
    outcome = run_pagefind(tmp_path / "does-not-exist")
    assert not outcome.ok
    assert "not found" in outcome.message


def test_run_pagefind_indexes_a_built_page(tmp_path: Path) -> None:
    page = tmp_path / "page" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        "<!DOCTYPE html><html><body>"
        "<article data-pagefind-body><h1>Fragments</h1>"
        "<p>How to install and use fragments in django-components.</p></article>"
        "</body></html>",
        encoding="utf-8",
    )

    outcome = run_pagefind(tmp_path)
    if not outcome.ok:
        pytest.fail(f"pagefind failed: {outcome.message}\n{outcome.output}")
    assert (tmp_path / "pagefind").is_dir()
    assert (tmp_path / "pagefind" / "pagefind.js").is_file()
