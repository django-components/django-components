"""Tests for the base-path rewrite (subpath deploys, e.g. GitHub project Pages)."""

from __future__ import annotations

from pathlib import Path

from apps.docs.build.base_path import apply_base_path


def _write(tmp_path: Path, name: str, html: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p


def test_empty_base_is_noop(tmp_path: Path) -> None:
    page = _write(tmp_path, "index.html", '<head></head><a href="/docs/">x</a>')
    assert apply_base_path(tmp_path, "") == 0
    assert page.read_text(encoding="utf-8") == '<head></head><a href="/docs/">x</a>'


def test_prefixes_root_absolute_urls(tmp_path: Path) -> None:
    page = _write(
        tmp_path,
        "index.html",
        "<head></head>"
        '<link rel="stylesheet" href="/static/css/site.css">'
        '<a href="/docs/">Docs</a>'
        '<script src="/static/js/site.js"></script>'
        '<div data-pagefind-path="/pagefind/pagefind.js"></div>',
    )
    changed = apply_base_path(tmp_path, "/django-components")
    assert changed == 1
    out = page.read_text(encoding="utf-8")
    assert 'href="/django-components/static/css/site.css"' in out
    assert 'href="/django-components/docs/"' in out
    assert 'src="/django-components/static/js/site.js"' in out
    assert 'data-pagefind-path="/django-components/pagefind/pagefind.js"' in out


def test_minified_unquoted_attrs(tmp_path: Path) -> None:
    page = _write(tmp_path, "index.html", "<head></head><a href=/docs/ class=x>D</a><img src=/static/img/a.png>")
    apply_base_path(tmp_path, "/django-components")
    out = page.read_text(encoding="utf-8")
    assert "href=/django-components/docs/" in out
    assert "src=/django-components/static/img/a.png" in out


def test_leaves_external_protocol_relative_and_relative_untouched(tmp_path: Path) -> None:
    html = (
        "<head></head>"
        '<a href="https://example.com/docs/">ext</a>'
        '<a href="//cdn.example.com/x.js">proto</a>'
        '<a href="../assets/main.css">rel</a>'
        '<a href="concepts/slots/">rel2</a>'
    )
    page = _write(tmp_path, "v/0.92/index.html", html)  # frozen-style relative links
    apply_base_path(tmp_path, "/django-components")
    out = page.read_text(encoding="utf-8")
    # Only the meta tag is added; none of the external / protocol-relative /
    # relative URLs are rewritten.
    expected = html.replace("<head>", '<head><meta name="djc-base-path" content="/django-components">')
    assert expected == out


def test_injects_base_path_meta(tmp_path: Path) -> None:
    page = _write(tmp_path, "index.html", "<head></head><body></body>")
    apply_base_path(tmp_path, "/django-components")
    assert '<meta name="djc-base-path" content="/django-components">' in page.read_text(encoding="utf-8")


def test_idempotent(tmp_path: Path) -> None:
    page = _write(tmp_path, "index.html", '<head></head><a href="/docs/">x</a>')
    apply_base_path(tmp_path, "/django-components")
    once = page.read_text(encoding="utf-8")
    apply_base_path(tmp_path, "/django-components")  # second run must not double-prefix
    assert page.read_text(encoding="utf-8") == once
    assert "/django-components/django-components" not in once
