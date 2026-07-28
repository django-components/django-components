"""
Tests for the custom 404 page (Phase 5a, feature 5a.6).

Covers the NotFoundPage component markup and the generate_not_found builder
step that writes 404.html in DocPage chrome.
"""

from __future__ import annotations

from pathlib import Path

from apps.docs.build.builder import generate_not_found
from apps.docs.components.not_found_page.not_found_page import DEFAULT_DESTINATIONS, NotFoundPage


def test_component_renders_destinations_and_search_button() -> None:
    html = NotFoundPage.render()
    # The search button opens the shared modal via the data-search-open hook.
    assert "data-search-open" in html
    assert "djc-notfound__search" in html
    for dest in DEFAULT_DESTINATIONS:
        assert f'href="{dest["path"]}"' in html
        assert dest["label"] in html


def test_component_accepts_custom_destinations() -> None:
    html = NotFoundPage.render(
        kwargs={"destinations": [{"label": "Only", "path": "/only/"}], "issues_url": "https://example.com/issues"}
    )
    assert 'href="/only/"' in html
    assert 'href="https://example.com/issues"' in html
    assert "Documentation home" not in html


def test_generate_writes_404_html_in_chrome(tmp_path: Path) -> None:
    generate_not_found(tmp_path, nav_tree=None, version="1.2.3")
    out = tmp_path / "404.html"
    assert out.is_file()
    html = out.read_text(encoding="utf-8")

    # Headline injected from the page title (exactly one H1).
    assert html.count("<h1>") == 1
    assert "Page not found" in html
    # DocPage chrome is present (header trigger + modal).
    assert "djc-search-trigger" in html
    assert "djc-search__overlay" in html


def test_404_is_noindex_and_not_searchable(tmp_path: Path) -> None:
    generate_not_found(tmp_path, nav_tree=None, version="1.2.3")
    html = (tmp_path / "404.html").read_text(encoding="utf-8")
    # Kept out of search engines...
    assert "noindex" in html
    # ...and out of the Pagefind index (no body marker -> page is skipped).
    assert "data-pagefind-body" not in html
