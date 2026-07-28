"""
Discovery for the Components reference page (feature 4.6).

The predefined Component subclasses live in ``django_components.components``
(``DynamicComponent``, ``ErrorFallback``, ...). Each becomes an entry rendered by
``ReferenceComponentClass``. The dotted path is the class's canonical module path
(matching the old page's anchors).
"""

from __future__ import annotations

import inspect

import django_components.components as components_module
from apps.docs.reference.discovery import introspect
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage
from django_components.util.misc import get_import_path

_INTRO = (
    "django-components ships these ready-to-use components. Register them like any "
    "other component, then use them in your templates."
)


def discover() -> ReferencePage:
    """Build the Components ``ReferencePage`` from the predefined Component subclasses."""
    entries: list[ReferenceEntry] = []
    seen: set[str] = set()
    for name, obj in inspect.getmembers(components_module):
        if not introspect.is_component_cls(obj):
            continue
        path = get_import_path(obj)
        if path in seen:
            continue
        seen.add(path)
        entries.append(ReferenceEntry(kind="component_class", dotted_path=path, display_name=name))

    entries.sort(key=lambda e: e.display_name)
    return ReferencePage(
        slug="components",
        title="Components",
        preface_md=_INTRO,
        entries=tuple(entries),
        description="API reference - the predefined django-components components.",
    )
