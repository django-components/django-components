"""
Tests for the Phase 5b version picker (feature 5b.11).

Covers the VersionPicker component markup and its wiring into DocPage. The
client-side behavior (manifest fetch + redirect) lives in static/js/site.js and
is exercised by hand / future E2E, not here.
"""

from __future__ import annotations

from apps.docs.components.doc_page.doc_page import DocPage
from apps.docs.components.version_picker.version_picker import VersionPicker


def test_picker_renders_select_seeded_with_current_version() -> None:
    html = VersionPicker.render(kwargs={"current_version": "0.151.0"})
    assert "data-version-picker" in html
    assert 'data-current="0.151.0"' in html
    assert "<select" in html
    assert ">0.151.0</option>" in html  # seeded so it degrades to a static label


def test_picker_renders_nothing_without_a_version() -> None:
    # The header always emits the picker tag; with no version it must collapse
    # to nothing rather than a broken empty dropdown.
    html = VersionPicker.render(kwargs={"current_version": ""})
    assert "data-version-picker" not in html
    assert "<select" not in html


def test_doc_page_uses_picker_not_static_badge() -> None:
    html = DocPage.render(kwargs={"content_html": "<h1>X</h1>", "title": "X", "version": "0.151.0"})
    assert "data-version-picker" in html
    assert 'data-current="0.151.0"' in html
    # The old static badge markup is fully replaced.
    assert "djc-version-badge" not in html


def test_doc_page_without_version_has_no_picker() -> None:
    html = DocPage.render(kwargs={"content_html": "<h1>X</h1>", "title": "X"})
    assert "data-version-picker" not in html
