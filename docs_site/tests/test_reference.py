"""
Tests for the Phase 4 API reference (the mkdocstrings replacement).

Exercises all three layers on the exceptions proof-of-concept page:
discovery (Layer 1), the griffe walker + extensions, and the per-kind
renderers (Layer 2), plus the end-to-end render of the generated page.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import griffe
import pytest
from apps.docs.build.pipeline import render_page
from apps.docs.build.reference import _page_markdown, write_objects_inv
from apps.docs.build.toc import merge_html_headings_into_toc
from apps.docs.components.doc_page.doc_page import _flatten_toc
from apps.docs.reference.annotation import render_annotation
from apps.docs.reference.commands import parse_command_args, strip_ansi
from apps.docs.reference.crossrefs import (
    _inventory_candidates,
    make_type_resolver,
    resolve_crossrefs,
    resolve_crossrefs_in_prose,
    symbol_url_index,
)
from apps.docs.reference.discovery.kinds import ReferenceEntry
from apps.docs.reference.discovery.pages import api as api_page
from apps.docs.reference.discovery.pages import commands as commands_page
from apps.docs.reference.discovery.pages import components as components_page
from apps.docs.reference.discovery.pages import exceptions
from apps.docs.reference.discovery.pages import extension_commands as extcmd_page
from apps.docs.reference.discovery.pages import extension_hooks as hooks_page
from apps.docs.reference.discovery.pages import extension_urls as exturl_page
from apps.docs.reference.discovery.pages import settings as settings_page
from apps.docs.reference.discovery.pages import signals as signals_page
from apps.docs.reference.discovery.pages import tag_formatters as tagfmt_page
from apps.docs.reference.discovery.pages import template_tags as tags_page
from apps.docs.reference.discovery.pages import template_variables as vars_page
from apps.docs.reference.discovery.pages import testing as testing_page
from apps.docs.reference.discovery.pages import urls as urls_page
from apps.docs.reference.discovery.registry import discover_pages, entry_index
from apps.docs.reference.discovery.walk import resolve
from apps.docs.reference.inventory import build_objects_inv, external_inventory, parse_objects_inv
from apps.docs.reference.render import render_entry
from apps.docs.reference.signatures import render_signature

from django_components.commands.components import ComponentsRootCommand
from django_components.util.command import setup_parser_from_command

API_URL = "docs/reference/api/"

EXPECTED_EXCEPTIONS = ["AlreadyRegistered", "NotRegistered", "TagProtectedError"]
EXCEPTIONS_URL = "docs/reference/exceptions/"


def _page_by_slug(slug: str):
    return next(page for page in discover_pages() if page.slug == slug)


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
    data = _page_by_slug("exceptions").as_dict()
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
    # A symbol that's documented nowhere (not a project symbol, not in any
    # inventory) degrades to plain text rather than a broken [x][y] literal.
    md, unresolved = resolve_crossrefs("See [NoSuchThing][NoSuchThing] now.", current_url=EXCEPTIONS_URL)
    assert md == "See NoSuchThing now."
    assert "NoSuchThing" in unresolved


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


def test_toc_merge_lifts_members_with_their_kind() -> None:
    # A class heading (h2) and its member (h4) are both lifted, each tagged with
    # the symbol kind read off the doc-symbol badge; the member nests under it.
    content = (
        '<h1 id="api">API</h1>'
        '<h2 id="Foo" class="doc doc-heading">'
        '<span class="doc-symbol doc-symbol-class"></span><span class="doc-object-name">Foo</span></h2>'
        '<h4 id="Foo.bar" class="doc-member-heading">'
        '<span class="doc-symbol doc-symbol-method"></span><span class="doc-object-name">bar</span>'
        '<span class="doc-label">classmethod</span></h4>'
    )
    toc = [{"level": 1, "id": "api", "name": "API", "children": []}]
    foo = merge_html_headings_into_toc(content, toc)[0]["children"][0]
    assert foo["id"] == "Foo"
    assert foo["kind"] == "class"
    assert foo["name"] == "Foo"  # doc-object-name only, no badge/label text
    assert [(c["id"], c["name"], c["kind"]) for c in foo["children"]] == [("Foo.bar", "bar", "method")]


def test_flatten_toc_unwraps_h1_and_marks_member_classes_collapsible() -> None:
    toc = [
        {
            "level": 1,
            "id": "api",
            "name": "API",
            "kind": "",
            "children": [
                {
                    "level": 2,
                    "id": "Foo",
                    "name": "Foo",
                    "kind": "class",
                    "children": [{"level": 4, "id": "Foo.bar", "name": "bar", "kind": "method", "children": []}],
                },
                {"level": 2, "id": "Bar", "name": "Bar", "kind": "class", "children": []},
            ],
        }
    ]
    items = _flatten_toc(toc)
    assert [i["name"] for i in items] == ["Foo", "Bar"]  # H1 "API" unwrapped, classes top-level
    assert items[0]["collapsible"] is True  # Foo has members -> collapsible
    assert items[0]["kind"] == "class"
    assert [c["name"] for c in items[0]["children"]] == ["bar"]
    assert items[1]["collapsible"] is False  # Bar has no members


def test_flatten_toc_keeps_content_subsections_non_collapsible() -> None:
    # A content page (section -> subsection, no symbol kinds) is never collapsed.
    toc = [
        {
            "level": 2,
            "id": "intro",
            "name": "Intro",
            "kind": "",
            "children": [{"level": 3, "id": "details", "name": "Details", "kind": "", "children": []}],
        }
    ]
    items = _flatten_toc(toc)
    assert items[0]["collapsible"] is False
    assert [c["name"] for c in items[0]["children"]] == ["Details"]


# --- End-to-end --------------------------------------------------------------


def test_generated_exceptions_page_renders_end_to_end() -> None:
    md = _page_markdown(_page_by_slug("exceptions"))
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


def test_page_preface_crossrefs_resolve_through_the_pipeline() -> None:
    # Preface `[X][Key]` refs are resolved by the render pipeline (same path as
    # content pages), not at generation - so the generated markdown still carries
    # the raw ref but the rendered HTML carries a real link.
    page = _page_by_slug("extension_hooks")
    result = render_page(
        _page_markdown(page),
        context={"version": "0.0.0"},
        current_path="docs/reference/extension_hooks/",
        wrap_in_layout=False,
    )
    assert "[`ComponentExtension`][ComponentExtension]" not in result.html  # raw ref gone
    assert "../api/#ComponentExtension" in result.html  # resolved to the API page anchor


def test_resolve_crossrefs_in_prose_resolves_skips_code_and_keeps_unknown() -> None:
    md = "See [`Component`][Component], `arr[i][j]`.\n\n```python\ny = a[i][j]\n```\n"
    out, _ = resolve_crossrefs_in_prose(md, current_url="docs/guides/x/")
    assert "[`Component`][Component]" not in out  # known symbol -> resolved to a link
    assert "](" in out  # ...as a markdown link
    assert "`arr[i][j]`" in out  # inline-code index left literal (unknown key)
    assert "y = a[i][j]" in out  # fenced code untouched


def test_symbol_index_resolves_class_members_and_qualified_fields() -> None:
    idx = symbol_url_index()
    assert idx["Component.get_js_data"].endswith("api/#Component.get_js_data")  # class member anchor
    assert idx["ComponentsSettings.cache"].endswith("settings/#cache")  # dedicated field beats api member


# --- Chunk B: api discovery, signatures, cross-refs, inventory, members --------


def _member(class_path: str, member_name: str) -> Any:
    obj = resolve(class_path)
    member = obj.members[member_name]
    return member.final_target if isinstance(member, griffe.Alias) else member


def test_api_discovery_includes_classes_excludes_categorized() -> None:
    names = {entry.display_name for entry in api_page.discover().entries}
    assert {"Component", "ComponentRegistry"} <= names
    # These live on other reference pages, not the general API page.
    assert "AlreadyRegistered" not in names  # exception -> exceptions page
    assert "DynamicComponent" not in names  # predefined component -> components page


def test_inventory_parse_roundtrip() -> None:
    data = build_objects_inv([("django_components.Component", "reference/api/#Component")], project="djc", version="1")
    parsed = parse_objects_inv(data, "https://x.test/")
    assert parsed["django_components.Component"] == "https://x.test/reference/api/#Component"


def test_inventory_public_path_bridging() -> None:
    # griffe's module path -> Django's public re-export path is among the candidates.
    assert "django.http.HttpRequest" in list(_inventory_candidates("django.http.request.HttpRequest"))


def test_type_resolver_links_project_then_external() -> None:
    resolve_url = make_type_resolver(API_URL)
    # Project symbol by short name -> same-page anchor.
    assert resolve_url("Component", "django_components.component.Component") == "#Component"
    # External resolution needs the fetched inventory (network/cache); skip if offline.
    if external_inventory():
        python_url = resolve_url("Any", "typing.Any")
        assert python_url is not None
        assert python_url.startswith("https://docs.python.org/")


def test_render_annotation_links_types_and_keeps_structure() -> None:
    resolve_url = make_type_resolver(API_URL)
    ctx_param = next(p for p in _member("django_components.Component", "render").parameters if p.name == "context")
    rendered = render_annotation(ctx_param.annotation, resolve_url)
    assert "doc-type-link" in rendered  # at least one type linked
    assert " | None" in rendered  # union operator rendered as text


def test_render_signature_includes_params_and_return() -> None:
    render = _member("django_components.Component", "render")
    sig = render_signature(render, display_name="render", resolve=make_type_resolver(API_URL))
    assert "render(" in sig
    assert "-> " in sig  # return annotation present
    assert "self" not in sig  # implicit first parameter dropped


def test_component_entry_renders_signature_members_and_crossref() -> None:
    entry = ReferenceEntry(kind="class", dotted_path="django_components.Component", display_name="Component")
    html = render_entry(entry, current_url=API_URL)
    assert "doc-signature" in html  # signature block
    assert "doc-params" in html  # parameters table
    assert "doc-members" in html  # grouped members
    assert 'id="Component.render"' in html  # member canonical anchor
    assert 'id="django_components.Component.render"' in html  # member legacy anchor
    assert 'href="#ComponentRegistry"' in html  # project cross-ref resolved in-signature


def test_write_objects_inv_emits_parseable_inventory(tmp_path: Path) -> None:
    write_objects_inv(tmp_path, version="0.0.0")
    inventory = parse_objects_inv((tmp_path / "objects.inv").read_bytes(), "https://x.test/")
    assert "django_components.Component" in inventory
    assert inventory["django_components.Component"].endswith("docs/reference/api/#Component")


# --- Chunk C: commands -------------------------------------------------------

EXPECTED_COMMANDS = [
    "components",
    "components create",
    "components upgrade",
    "components ext",
    "components ext list",
    "components ext run",
    "components list",
]


def test_command_discovery_walks_the_tree_depth_first() -> None:
    entries = commands_page.discover().entries
    assert [e.display_name for e in entries] == EXPECTED_COMMANDS
    assert {e.kind for e in entries} == {"management_command"}


def test_parse_command_args_extracts_options_and_subcommands() -> None:
    parsed = parse_command_args(setup_parser_from_command(ComponentsRootCommand))
    assert "options" in parsed
    sub_names = {str(arg["names"][0]) for arg in parsed["subcommands"]}  # type: ignore[index]
    assert {"create", "upgrade", "ext", "list"} <= sub_names


def test_command_entry_renders_usage_source_and_subcommand_links() -> None:
    entry = next(e for e in commands_page.discover().entries if e.display_name == "components")
    html = render_entry(entry, current_url="docs/reference/commands/")
    assert 'id="components"' in html
    assert "python manage.py components" in html  # usage shows the full invocation
    assert "See source code" in html
    assert 'href="#components-create"' in html  # subcommand links to its own section


def test_strip_ansi_removes_color_codes() -> None:
    assert strip_ansi("\x1b[1;34musage: \x1b[0mcreate \x1b[32m-h\x1b[0m") == "usage: create -h"


def test_command_args_parse_when_argparse_colorizes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Python 3.14's argparse colorizes help output under FORCE_COLOR; the escape
    # codes used to break the "subcommands:" split and sink the group commands.
    monkeypatch.setenv("FORCE_COLOR", "1")
    parsed = parse_command_args(setup_parser_from_command(ComponentsRootCommand))
    assert any("create" in a["names"] for a in parsed.get("subcommands", []))  # subcommands survive


def test_group_command_renders_clean_under_color(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("FORCE_COLOR", "1")
    entry = next(e for e in commands_page.discover().entries if e.display_name == "components")
    html = render_entry(entry, current_url="docs/reference/commands/")
    assert "\x1b" not in html  # no leaked ANSI color codes [bug 2]
    assert "could not be generated" not in html  # the group command renders, no fallback [bug 1]
    assert 'href="#components-create"' in html  # ...and its subcommand links survive


# --- Chunk D: extension hooks ------------------------------------------------

HOOKS_URL = "docs/reference/extension_hooks/"


def test_extension_hooks_discovery_finds_hooks_and_contexts() -> None:
    page = hooks_page.discover()
    assert page.layout == "hooks_plus_objects"
    assert len([e for e in page.entries if e.kind == "extension_hook"]) == 16
    assert len([e for e in page.entries if e.kind == "hook_context"]) == 16
    # dotted_path uses the full module path, matching the deployed anchors.
    on_input = next(e for e in page.entries if e.display_name == "on_component_input")
    assert on_input.legacy_anchor == "django_components.extension.ComponentExtension.on_component_input"


def test_extension_hook_entry_renders_signature_and_available_data() -> None:
    entry = next(e for e in hooks_page.discover().entries if e.display_name == "on_component_input")
    html = render_entry(entry, current_url=HOOKS_URL)
    assert 'id="on_component_input"' in html  # canonical (short) anchor
    assert 'id="django_components.extension.ComponentExtension.on_component_input"' in html  # legacy
    assert "doc-signature" in html
    assert "Available data" in html  # the context fields table from its ctx


def test_hook_context_entry_renders_fields_table() -> None:
    entry = next(e for e in hooks_page.discover().entries if e.display_name == "OnComponentInputContext")
    html = render_entry(entry, current_url=HOOKS_URL)
    assert 'id="OnComponentInputContext"' in html
    assert 'id="django_components.extension.OnComponentInputContext"' in html  # legacy
    assert "doc-fields" in html
    assert "<code>component_id</code>" in html  # a documented field


# --- Chunk E: template tags --------------------------------------------------


def test_template_tag_discovery_finds_tags() -> None:
    entries = tags_page.discover().entries
    assert {"component", "fill", "slot", "provide", "html_attrs"} <= {e.display_name for e in entries}
    assert {e.kind for e in entries} == {"template_tag"}


def test_template_tag_entry_renders_tag_signature() -> None:
    entry = next(e for e in tags_page.discover().entries if e.display_name == "component")
    html = render_entry(entry, current_url="docs/reference/template_tags/")
    assert 'id="component"' in html
    assert "{% component" in html  # the {% tag … %} signature block
    assert "{% endcomponent %}" in html  # the end tag
    assert "See source code" in html


def test_codemodded_crossref_resolves_to_template_tags_page() -> None:
    # The Chunk-A docstring codemod turned `[`{% fill %}`](#fill)` into a bracket
    # cross-ref; now that the template-tags page exists, it resolves there.
    md, unresolved = resolve_crossrefs("See [`{% fill %}`][fill].", current_url=API_URL)
    assert "../template_tags/#fill" in md
    assert "fill" not in unresolved


# --- Chunk F: settings + template variables ----------------------------------


def test_settings_discovery_has_fields_and_defaults_panel() -> None:
    page = settings_page.discover()
    assert {"autodiscover", "dirs", "cache", "context_behavior"} <= {e.display_name for e in page.entries}
    assert {e.kind for e in page.entries} == {"setting"}
    assert "Settings defaults" in page.preface_md  # the defaults panel
    assert "autodiscover=True" in page.preface_md  # the cleaned snippet content


def test_template_variables_discovery() -> None:
    assert [e.display_name for e in vars_page.discover().entries] == ["args", "kwargs", "slots", "is_filled"]


def test_setting_entry_renders_type_and_dual_anchors_without_badge() -> None:
    entry = next(e for e in settings_page.discover().entries if e.display_name == "autodiscover")
    html = render_entry(entry, current_url="docs/reference/settings/")
    assert 'id="autodiscover"' in html  # canonical
    assert 'id="django_components.app_settings.ComponentsSettings.autodiscover"' in html  # legacy
    assert "doc-signature" in html  # the `name: type` line
    assert "doc-symbol-heading" not in html  # settings carry no symbol-type badge


# --- Chunk G: tag formatters -------------------------------------------------


def test_tag_formatter_discovery() -> None:
    page = tagfmt_page.discover()
    assert [e.display_name for e in page.entries] == ["ComponentFormatter", "ShorthandComponentFormatter"]
    assert {e.kind for e in page.entries} == {"tag_formatter"}
    assert "Available tag formatters" in page.preface_md  # the instances list
    assert "component_formatter" in page.preface_md  # an instance mapped to its class


def test_tag_formatter_entry_renders_naked_card() -> None:
    entry = next(e for e in tagfmt_page.discover().entries if e.display_name == "ComponentFormatter")
    html = render_entry(entry, current_url="docs/reference/tag_formatters/")
    assert 'id="ComponentFormatter"' in html  # canonical
    assert 'id="django_components.tag_formatter.ComponentFormatter"' in html  # legacy
    assert "doc-members" not in html  # naked card: no members
    assert "Bases:" in html  # docstring still carries the bases line


# --- Chunk H: components page -------------------------------------------------


def test_components_discovery_finds_predefined_subclasses() -> None:
    page = components_page.discover()
    assert [e.display_name for e in page.entries] == ["DynamicComponent", "ErrorFallback"]
    assert {e.kind for e in page.entries} == {"component_class"}
    df = next(e for e in page.entries if e.display_name == "DynamicComponent")
    assert df.legacy_anchor == "django_components.components.dynamic.DynamicComponent"  # canonical module path


def test_component_class_entry_shows_only_unique_members() -> None:
    entry = next(e for e in components_page.discover().entries if e.display_name == "ErrorFallback")
    html = render_entry(entry, current_url="docs/reference/components/")
    assert 'id="ErrorFallback"' in html  # canonical
    assert 'id="ErrorFallback.on_render"' in html  # its own member
    assert 'id="ErrorFallback.render"' not in html  # NOT Component's inherited render


# --- Chunk J: hardening (discovery snapshot + anchor scheme) ------------------


def test_discovery_snapshot(snapshot) -> None:  # type: ignore[no-untyped-def]
    # Locks the documented API surface: every page, its layout, and every entry
    # with both of its anchors. A symbol added / removed / renamed, or an
    # anchor-scheme change, shows up as a reviewable diff rather than slipping
    # through. Update the baseline with: uv run pytest --snapshot-update.
    surface = {
        page.slug: {
            "title": page.title,
            "layout": page.layout,
            "entries": [
                {
                    "kind": e.kind,
                    "dotted_path": e.dotted_path,
                    "display_name": e.display_name,
                    "canonical_anchor": e.canonical_anchor,
                    "legacy_anchor": e.legacy_anchor,
                }
                for e in page.entries
            ],
        }
        for page in discover_pages()
    }
    assert surface == snapshot


def test_command_anchor_is_slugified_and_alias_free() -> None:
    entry = next(e for e in commands_page.discover().entries if e.display_name == "components ext run")
    # The readable label keeps its spaces; the anchor is the heading slug.
    assert entry.canonical_anchor == "components-ext-run"
    # Commands were hand-written (`## {command}`), never via `:::`, so there is no
    # separate dotted-path legacy anchor - legacy == canonical.
    assert entry.legacy_anchor == entry.canonical_anchor


def test_template_tag_legacy_anchor_is_the_tag_name() -> None:
    entry = next(e for e in tags_page.discover().entries if e.display_name == "fill")
    assert entry.canonical_anchor == "fill"
    assert entry.legacy_anchor == "fill"  # the tag name, NOT the Node-class dotted path


# --- Chunk I: testing / extension commands+urls (fold-ins) + urls + signals ---


def test_testing_discovery_keeps_submodule_path() -> None:
    page = testing_page.discover()
    assert [e.display_name for e in page.entries] == ["djc_test"]
    assert {e.kind for e in page.entries} == {"class"}  # functions fold into ReferenceClass
    # The legacy anchor keeps the `.testing.` segment, matching the old `:::` path.
    assert page.entries[0].legacy_anchor == "django_components.testing.djc_test"


def test_testing_function_entry_renders_signature_without_members() -> None:
    entry = testing_page.discover().entries[0]
    html = render_entry(entry, current_url="docs/reference/testing_api/")
    assert 'id="djc_test"' in html  # canonical
    assert 'id="django_components.testing.djc_test"' in html  # legacy (submodule path)
    assert "doc-signature" in html  # a function still gets a signature block
    assert "doc-members" not in html  # ...but a function has no members section


def test_extension_commands_discovery_uses_marker_and_toplevel_path() -> None:
    page = extcmd_page.discover()
    names = {e.display_name for e in page.entries}
    assert {"CommandArg", "ComponentCommand"} <= names
    assert {e.kind for e in page.entries} == {"class"}
    # Detected via the package's own marker -> top-level export path (no submodule segment).
    cmd = next(e for e in page.entries if e.display_name == "ComponentCommand")
    assert cmd.legacy_anchor == "django_components.ComponentCommand"


def test_extension_urls_discovery() -> None:
    page = exturl_page.discover()
    assert [e.display_name for e in page.entries] == ["URLRoute", "URLRouteHandler"]
    assert {e.kind for e in page.entries} == {"class"}


def test_urls_page_lists_only_core_library_routes() -> None:
    page = urls_page.discover()
    assert page.entries == ()  # a URL route has no docstring -> no per-symbol entries
    assert "## List of URLs" in page.preface_md
    assert "- `components/cache/" in page.preface_md  # the library's own cache routes
    # NOT the per-component View endpoints that loaded components register at
    # import time (app-specific, not part of the library's URL API).
    assert "ext/view" not in page.preface_md


def test_signals_page_is_hand_authored_island() -> None:
    page = signals_page.discover()
    assert page.entries == ()  # nothing to introspect; the body is prose
    assert "template_rendered" in page.preface_md
    assert not page.preface_md.lstrip().startswith("# ")  # the generator supplies the h1 title
