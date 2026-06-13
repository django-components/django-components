"""
Tests for the Phase 4 API reference (the mkdocstrings replacement).

Exercises all three layers on the exceptions proof-of-concept page:
discovery (Layer 1), the griffe walker + extensions, and the per-kind
renderers (Layer 2), plus the end-to-end render of the generated page.
"""

from __future__ import annotations

import json

import griffe
import pytest
from apps.docs.build.pipeline import render_page
from apps.docs.build.reference import _page_markdown
from apps.docs.build.toc import merge_html_headings_into_toc
from apps.docs.components.reference.crossrefs import resolve_crossrefs
from apps.docs.components.reference.render import render_entry
from apps.docs.discovery.kinds import ReferenceEntry
from apps.docs.discovery.pages import exceptions
from apps.docs.discovery.registry import discover_pages, entry_index
from apps.docs.discovery.walk import resolve

EXPECTED_EXCEPTIONS = ["AlreadyRegistered", "NotRegistered", "TagProtectedError"]
EXCEPTIONS_URL = "docs/reference/exceptions/"


# --- Discovery (Layer 1) -----------------------------------------------------


def test_exceptions_discovery_finds_public_exception_classes() -> None:
    page = exceptions.discover()
    assert page.slug == "exceptions"
    assert page.title == "Exceptions"
    # Sorted, exactly the public Exception subclasses, all rendered as "class".
    assert [e.display_name for e in page.entries] == EXPECTED_EXCEPTIONS
    assert [e.dotted_path for e in page.entries] == [f"django_components.{n}" for n in EXPECTED_EXCEPTIONS]
    assert {e.kind for e in page.entries} == {"class"}


def test_entry_index_keys_by_both_path_and_short_name() -> None:
    index = entry_index()
    assert "django_components.AlreadyRegistered" in index  # dotted path ({% docstring %})
    assert "AlreadyRegistered" in index  # short name (docstring cross-refs)
    assert index["AlreadyRegistered"].kind == "class"


def test_reference_page_is_json_serializable() -> None:
    data = discover_pages()[0].as_dict()
    assert data["slug"] == "exceptions"
    assert data["entries"][0]["display_name"] == "AlreadyRegistered"
    # Must round-trip through JSON (snapshot/diff-ability is the point of Layer 1).
    json.dumps(data)


# --- Walker + griffe extensions ----------------------------------------------


def test_resolve_follows_alias_to_defining_object() -> None:
    obj = resolve("django_components.AlreadyRegistered")
    # The top-level export is an alias; resolve() returns the defining object.
    assert obj.canonical_path == "django_components.component_registry.AlreadyRegistered"
    assert obj.kind is griffe.Kind.CLASS


def test_extensions_inject_bases_and_source_exactly_once() -> None:
    # force_inspection must not double-fire the docstring-enriching hooks.
    docstring = resolve("django_components.AlreadyRegistered").docstring
    assert docstring is not None
    value = docstring.value
    assert value.count("doc-class-bases") == 1
    assert value.count("See source code") == 1
    assert "Bases: <code>Exception</code>" in value
    assert "blob/master/src/django_components/component_registry.py#L" in value


# --- Cross-ref resolution (Chunk-A subset) -----------------------------------


def test_crossrefs_strip_unknown_refs_to_plain_text() -> None:
    # Component isn't a discovered symbol yet (it's on the api page, Chunk B),
    # so it degrades to plain text rather than a broken [x][y] literal.
    md, unresolved = resolve_crossrefs("See [Component][Component] now.", current_url=EXCEPTIONS_URL)
    assert md == "See Component now."
    assert "Component" in unresolved


def test_crossrefs_resolve_known_symbol_to_link() -> None:
    md, unresolved = resolve_crossrefs("See [AlreadyRegistered][AlreadyRegistered].", current_url=EXCEPTIONS_URL)
    assert "[AlreadyRegistered](#AlreadyRegistered)" in md
    assert not unresolved


# --- Rendering (Layer 2) -----------------------------------------------------


def test_render_entry_emits_dual_anchors_bases_and_source() -> None:
    entry = entry_index()["django_components.AlreadyRegistered"]
    html = render_entry(entry, current_url=EXCEPTIONS_URL)
    assert 'id="AlreadyRegistered"' in html  # canonical (new short) anchor
    assert 'id="django_components.AlreadyRegistered"' in html  # legacy anchor (feature 4.58)
    assert 'href="#AlreadyRegistered"' in html  # permalink
    assert "Bases:" in html and "Exception" in html  # RuntimeBasesExtension
    assert "See source code" in html  # SourceCodeExtension


def test_render_entry_unknown_kind_raises() -> None:
    # A symbol whose kind has no registered renderer must fail loudly, not skip.
    bad = ReferenceEntry(kind="signal", dotted_path="django_components.x", display_name="x")
    with pytest.raises(ValueError, match="No reference renderer"):
        render_entry(bad, current_url="")


# --- TOC integration ---------------------------------------------------------


def test_toc_merge_folds_raw_headings_under_the_h1() -> None:
    content = (
        '<h1 id="exceptions">Exceptions</h1>'
        '<div class="doc doc-object"><h2 id="Foo" class="doc doc-heading">Foo</h2></div>'
    )
    toc = [{"level": 1, "id": "exceptions", "name": "Exceptions", "children": []}]
    merged = merge_html_headings_into_toc(content, toc)
    assert merged[0]["id"] == "exceptions"
    assert [child["id"] for child in merged[0]["children"]] == ["Foo"]


def test_toc_merge_leaves_markdown_only_pages_untouched() -> None:
    # No raw doc-heading headings -> the markdown toc is returned as-is.
    content = '<h2 id="intro">Intro</h2>'
    toc = [{"level": 2, "id": "intro", "name": "Intro", "children": []}]
    assert merge_html_headings_into_toc(content, toc) is toc


# --- End-to-end --------------------------------------------------------------


def test_generated_exceptions_page_renders_end_to_end() -> None:
    md = _page_markdown(discover_pages()[0])
    result = render_page(md, context={"version": "0.0.0"}, current_path=EXCEPTIONS_URL, wrap_in_layout=False)
    html = result.html

    for name in EXPECTED_EXCEPTIONS:
        assert f'id="{name}"' in html
        assert f'id="django_components.{name}"' in html
    # One bases line and one source link per documented exception.
    assert html.count("doc-class-bases") == len(EXPECTED_EXCEPTIONS)
    assert html.count("See source code") == len(EXPECTED_EXCEPTIONS)

    # Every symbol reaches the TOC (the right-rail + scroll-spy key off these).
    toc_ids = {child["id"] for token in result.toc_tokens for child in token.get("children", [])}
    assert set(EXPECTED_EXCEPTIONS) <= toc_ids
