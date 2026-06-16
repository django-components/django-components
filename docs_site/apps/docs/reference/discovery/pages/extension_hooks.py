"""
Discovery for the Extension Hooks reference page (features 4.14, 4.59).

Two groups of entries:

- **Hooks** - the ``on_*`` methods of ``ComponentExtension``. Each receives a
  single ``ctx`` argument whose type is the hook's context object; the renderer
  turns that into an "Available data" table.
- **Objects** - the hook context classes, detected by the ``_extension_hook_api``
  marker that ``@mark_extension_hook_api`` sets (feature 4.59). The same marker
  is what excludes them from the general API page.

Anchors use the full module path (``django_components.extension.X``), matching the
deployed site - the old ``:::`` directives targeted the ``extension`` module, not
the top-level re-export.
"""

from __future__ import annotations

import django_components
from apps.docs.reference.discovery import introspect
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage
from django_components.extension import ComponentExtension

_MODULE = "django_components.extension"
_PREFACE = (
    "Extensions hook into the component lifecycle by subclassing "
    "[`ComponentExtension`][ComponentExtension] and implementing the `on_*` "
    "methods below. Each hook receives a single context object whose fields are "
    "listed under **Available data**."
)


def discover() -> ReferencePage:
    """Build the Extension Hooks ``ReferencePage`` (hook methods + context objects)."""
    hooks = [
        ReferenceEntry(
            kind="extension_hook",
            dotted_path=f"{_MODULE}.ComponentExtension.{name}",
            display_name=name,
        )
        for name in sorted(n for n in dir(ComponentExtension) if n.startswith("on_"))
    ]
    contexts = [
        ReferenceEntry(
            kind="hook_context",
            dotted_path=f"{_MODULE}.{name}",
            display_name=name,
        )
        for name in sorted(introspect.public_names())
        if introspect.is_extension_hook_api(getattr(django_components, name, None))
    ]
    return ReferencePage(
        slug="extension_hooks",
        title="Extension hooks",
        preface_md=_PREFACE,
        entries=(*hooks, *contexts),
        layout="hooks_plus_objects",
        description="API reference - extension lifecycle hooks and their context objects.",
    )
