"""
API-reference symbol coverage guards (features 4.62, 4.63).

Two checks over the discovered reference entries vs the public API surface:

- Forward (4.62, ERROR): every documented symbol must resolve. Each reference
  entry's dotted path is what the ``{% docstring %}`` tag feeds to griffe at
  build time; if griffe can't resolve it, the tag renders an error stub instead
  of real docs. We catch that here, loudly, before it ships.
- Reverse (4.63, WARNING): every public export should be documented somewhere. A
  symbol exported from ``django_components`` but absent from every reference page
  is almost always an omission - a new export nobody routed to a page. Two
  categories are excluded by design: re-exported *modules* (a namespace is not a
  documentable symbol) and tag-formatter *instances* (documented in the
  tag-formatters page preface as a name->class mapping, not as their own entry).

Both directions read only the discovery registry plus the package, so this runs
pre-build with no SiteIndex.

Spec: docs_site/design/DESIGN_features.md rows 4.62-4.63.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from typing import TYPE_CHECKING

import django_components
from apps.docs.reference.discovery import introspect
from apps.docs.reference.discovery.registry import discover_pages
from apps.docs.reference.discovery.walk import resolve

from .base import GuardResult

if TYPE_CHECKING:
    from .base import GuardContext


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    pages = discover_pages()

    # --- Forward (4.62): every documented symbol resolves. ---
    # resolve() raises (KeyError for a missing path, AliasResolutionError for a
    # broken re-export) rather than returning None, and the same failure is what
    # makes render_entry fall back to an error stub. Mirror that: any exception
    # here means the symbol won't render.
    for page in pages:
        for entry in page.entries:
            try:
                resolve(entry.dotted_path)
            except Exception as exc:  # any resolution failure means the documented symbol won't render
                yield GuardResult.error(
                    guard="api_symbols",
                    message=(
                        f"Documented symbol {entry.dotted_path!r} does not resolve "
                        f"({type(exc).__name__}) - its {{% docstring %}} tag would render an error stub."
                    ),
                    source=f"docs/reference/{page.slug}",
                )

    # --- Reverse (4.63): every public export is documented somewhere. ---
    documented_names = {entry.display_name for page in pages for entry in page.entries}
    documented_paths = {entry.dotted_path for page in pages for entry in page.entries}

    for name in sorted(getattr(django_components, "__all__", ())):
        obj = getattr(django_components, name, None)
        if obj is None or inspect.ismodule(obj):
            continue  # a re-exported module namespace is not a documentable symbol
        if introspect.is_tag_formatter_instance(obj):
            continue  # documented in the tag-formatters page preface, not as an entry
        if name in documented_names or f"django_components.{name}" in documented_paths:
            continue
        yield GuardResult.warning(
            guard="api_symbols",
            message=(
                f"Public API symbol {name!r} is exported from django_components but is not "
                f"documented on any reference page."
            ),
            source="django_components/__init__.py",
        )
