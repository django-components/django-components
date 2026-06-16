"""
The discovery -> rendering contract.

A ``ReferencePage`` describes one page in the API reference (``exceptions``,
``api``, ``commands``, ...). It carries an ordered list of ``ReferenceEntry``
objects, each describing one documented symbol and which renderer should draw
it. Both types are plain, JSON-serializable data: discovery (Layer 1) produces
them, the per-kind components (Layer 2) consume them, and nothing in here
renders HTML.

Spec: ``docs_site/design/DESIGN_spike_5.md`` sections 5.1-5.2.
"""

from __future__ import annotations

import re
from typing import Any, Literal, NamedTuple

# Kinds whose pages were hand-written (a ``## {heading}`` per symbol) on both the
# old and new sites, rather than rendered through mkdocstrings ``:::``. Their
# anchor is the heading slug, not a dotted path, so the old and new anchors are
# identical (there is no legacy dotted-path alias to preserve).
_HAND_WRITTEN_KINDS = frozenset({"template_tag", "management_command"})

_ANCHOR_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_anchor(text: str) -> str:
    """Turn a heading into an anchor id (``"components ext run"`` -> ``"components-ext-run"``)."""
    return _ANCHOR_SLUG_RE.sub("-", text.lower()).strip("-")


# The renderer to dispatch an entry to. These map to the per-kind component
# shells under ``apps/docs/components/reference/`` (spike 5 section 3.2). Several
# inventory "kinds" fold into one renderer - e.g. exceptions, functions,
# decorators, NamedTuples and the testing entrypoint all render as ``"class"``
# (the ``ReferenceClass`` workhorse). New values are added as later chunks land
# their renderers; until then an entry of an unknown kind is a build error, not
# a silent skip (see the ``{% docstring %}`` tag).
EntryKind = Literal[
    "class",  # general class / exception / NamedTuple / function / decorator / instance -> ReferenceClass
    "component_class",  # predefined Component subclass -> ReferenceComponentClass
    "setting",  # ComponentsSettings field / ComponentVars field -> ReferenceSetting
    "tag_formatter",  # TagFormatter class -> ReferenceTagFormatter
    "management_command",  # CLI command -> ReferenceManagementCommand
    "template_tag",  # {% tag %} -> ReferenceTemplateTag
    "url_pattern",  # URL route -> ReferenceURLPattern
    "extension_hook",  # ComponentExtension.on_* hook -> ReferenceExtensionHook
    "hook_context",  # On*Context NamedTuple -> ReferenceHookContext
    "signal",  # Django signal -> ReferenceSignal (hand-authored island)
]

# Page-level layout. Most pages are a flat repeater of entries; a few need
# bespoke arrangement (command tree, hooks-plus-context-objects, settings with a
# defaults panel). The page-layout components key off this.
PageLayout = Literal["repeater", "command_tree", "hooks_plus_objects", "settings"]


class ReferenceEntry(NamedTuple):
    """
    One documented symbol on a reference page.

    Attributes:
        kind: Which Layer-2 renderer draws this entry (see ``EntryKind``).
        dotted_path: The public, top-level import path, e.g.
            ``"django_components.AlreadyRegistered"``. This is what the
            ``{% docstring %}`` tag resolves; for most kinds it is also the
            legacy anchor (see ``legacy_anchor``). NOT griffe's canonical path
            (``django_components.component_registry.AlreadyRegistered``).
        display_name: The leaf name shown in the heading and used for the
            canonical anchor, e.g. ``"AlreadyRegistered"``.
        options: Per-entry rendering flags (e.g. ``{"show_if_no_docstring":
            True}``). These descend from the old mkdocstrings per-``:::`` option
            blocks. ``None`` means "no overrides"; read via ``opts()``.
        members_filter: When set, only these member names are rendered (used by
            pages that show a curated subset of a class's members). ``None``
            means "use the renderer's default member selection".

    """

    kind: EntryKind
    dotted_path: str
    display_name: str
    options: dict[str, Any] | None = None
    members_filter: tuple[str, ...] | None = None

    def opts(self) -> dict[str, Any]:
        """Rendering options as a plain dict (``None`` normalized to ``{}``)."""
        return dict(self.options) if self.options else {}

    @property
    def legacy_anchor(self) -> str:
        """
        The anchor id the old mkdocs site used, e.g.
        ``"django_components.AlreadyRegistered"``. Emitted alongside the
        canonical ``display_name`` anchor so inbound links keep resolving
        (feature 4.58). Verified against the deployed site: the old anchor was
        the top-level dotted path, without the module segment.

        Hand-written pages (template tags, management commands) are the
        exception: they were never rendered through mkdocstrings ``:::``. The old
        page hand-wrote ``## {tag}`` / ``## {command}``, so the old anchor is the
        heading slug - identical to the canonical anchor. There is no separate
        dotted-path alias to preserve (the dotted path is only used internally,
        to resolve the symbol for griffe).
        """
        if self.kind in _HAND_WRITTEN_KINDS:
            return self.canonical_anchor
        return self.dotted_path

    @property
    def canonical_anchor(self) -> str:
        """
        The new, short anchor id, e.g. ``"AlreadyRegistered"``.

        Management commands slugify their multi-word display name to match the
        heading the renderer emits (``"components ext run"`` ->
        ``"components-ext-run"``). Template-tag names are already slug-safe and a
        plain symbol's display name is its leaf name, so both pass through.
        """
        if self.kind == "management_command":
            return slugify_anchor(self.display_name)
        return self.display_name


class ReferencePage(NamedTuple):
    """
    One page of the API reference.

    Attributes:
        slug: URL/file slug, e.g. ``"exceptions"``. The page is built to
            ``docs/reference/<slug>/`` to match the content tree.
        title: Human page title, e.g. ``"Exceptions"``.
        preface_md: Markdown rendered above the entries (intro prose). May be
            empty.
        entries: Ordered symbols to render on the page.
        layout: Page-level arrangement (see ``PageLayout``).
        description: Optional front-matter description for the page ``<head>``.

    """

    slug: str
    title: str
    preface_md: str
    entries: tuple[ReferenceEntry, ...]
    layout: PageLayout = "repeater"
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        """JSON-serializable form (for dumping/diffing/snapshot tests)."""
        return {
            "slug": self.slug,
            "title": self.title,
            "preface_md": self.preface_md,
            "layout": self.layout,
            "description": self.description,
            "entries": [
                {
                    "kind": e.kind,
                    "dotted_path": e.dotted_path,
                    "display_name": e.display_name,
                    "options": e.opts(),
                    "members_filter": list(e.members_filter) if e.members_filter else None,
                }
                for e in self.entries
            ],
        }
