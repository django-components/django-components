"""
Discovery for the Tag Formatters reference page (features 4.8, 4.33).

Two pieces: the predefined ``TagFormatter`` *classes* (each an entry rendered by
``ReferenceTagFormatter``) and an "Available tag formatters" list that maps each
predefined *instance* (e.g. ``component_formatter``) to its class. The instances
list (feature 4.33) is page-level, so it goes in the preface as same-page anchor
links - the §7.6 layout bug (no blank line before the first entry) doesn't recur
because the page generator separates entries with blank lines.
"""

from __future__ import annotations

import django_components
from apps.docs.reference.discovery import introspect
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage

_MODULE = "django_components.tag_formatter"
_INTRO = (
    "A [`TagFormatter`][TagFormatterABC] controls the start/end tag names a "
    "component is rendered with. django-components ships these predefined "
    "formatters."
)


def discover() -> ReferencePage:
    """Build the Tag Formatters ``ReferencePage`` (instances list + class cards)."""
    classes: dict[str, type] = {}
    instances: dict[str, object] = {}
    for name in introspect.public_names():
        obj = getattr(django_components, name, None)
        if introspect.is_tag_formatter_instance(obj):
            instances[name] = obj
        elif introspect.is_tag_formatter_cls(obj):
            classes[name] = obj

    entries = [
        ReferenceEntry(kind="tag_formatter", dotted_path=f"{_MODULE}.{name}", display_name=name)
        for name in sorted(classes)
    ]
    return ReferencePage(
        slug="tag_formatters",
        title="Tag formatters",
        preface_md=f"{_INTRO}\n\n{_instances_list(instances)}",
        entries=tuple(entries),
        description="API reference - the predefined django-components tag formatters.",
    )


def _instances_list(instances: dict[str, object]) -> str:
    lines = ["## Available tag formatters", ""]
    for name, instance in sorted(instances.items()):
        class_name = type(instance).__name__
        # Same-page anchor link (the class card's canonical anchor is its name).
        lines.append(f"- `django_components.{name}` &rarr; [`{class_name}`](#{class_name})")
    return "\n".join(lines)
