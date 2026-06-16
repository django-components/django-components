"""
Tests for the Phase 5a search UI (Chunk 2: features 5a.2 / 5a.3 / 5a.4).

Asserts the markup contract that static/js/search.js relies on: the SearchModal
component renders the overlay, input, state containers, and quick links, and
DocPage wires in the header trigger, the modal, and the search assets.

The interactive behavior (open/close, querying, keyboard nav) is exercised
end-to-end against a built site + Pagefind index in the browser; that lives
outside this unit suite because it needs a running static server.
"""

from __future__ import annotations

from apps.docs.components.doc_page.doc_page import DocPage
from apps.docs.components.search_modal.search_modal import DEFAULT_QUICK_LINKS, SearchModal

# -- SearchModal component -----------------------------------------------------


def test_modal_renders_hidden_overlay_with_pagefind_path() -> None:
    html = SearchModal.render()
    assert 'class="djc-search__overlay"' in html
    # Starts hidden; opened by search.js
    assert "hidden" in html
    # Default index path search.js dynamically imports
    assert 'data-pagefind-path="/pagefind/pagefind.js"' in html


def test_modal_renders_input_and_state_containers() -> None:
    html = SearchModal.render()
    assert 'class="djc-search__input"' in html
    # The four regions search.js toggles between
    assert "data-search-empty" in html
    assert "data-search-noresults" in html
    assert "data-search-error" in html
    assert "data-search-list" in html


def test_modal_renders_default_quick_links() -> None:
    html = SearchModal.render()
    for link in DEFAULT_QUICK_LINKS:
        assert f'href="{link["path"]}"' in html
        assert link["label"] in html


def test_modal_accepts_custom_quick_links_and_path() -> None:
    html = SearchModal.render(
        kwargs={
            "quick_links": [{"label": "Custom", "path": "/custom/"}],
            "pagefind_path": "/v/0.150.0/pagefind/pagefind.js",
        }
    )
    assert 'href="/custom/"' in html
    assert "Custom" in html
    assert 'data-pagefind-path="/v/0.150.0/pagefind/pagefind.js"' in html
    # The default links should not appear when overridden
    assert "Your first component" not in html


# -- DocPage integration -------------------------------------------------------


def test_doc_page_wires_in_search_trigger_modal_and_assets() -> None:
    html = DocPage.render(kwargs={"content_html": "<h1>X</h1>", "title": "X"})
    # Header trigger that opens the modal
    assert "djc-search-trigger" in html
    assert "data-search-open" in html
    # The modal markup is included
    assert "djc-search__overlay" in html
    # Both search assets are linked
    assert "/static/css/search.css" in html
    assert "/static/js/search.js" in html
