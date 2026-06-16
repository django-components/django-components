"""
Discovery for the Template Tags reference page (feature 4.10).

Port of ``gen_reference_template_tags``: the tags are ``BaseNode`` subclasses
registered in the ``django_components/templatetags`` modules. Each entry's display
name is the tag itself (e.g. ``component``, ``fill``) - which is also its anchor,
so docstring cross-refs like ``[`{% fill %}`][fill]`` resolve here.

The renderer reads the metaclass-set ``_signature`` at runtime (force_inspection
isn't needed for that), so discovery only needs to point at the node class.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import django_components.templatetags as templatetags_pkg
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage
from django_components.node import BaseNode

_PREFACE = (
    "django-components provides the following template tags. Load them with "
    "`{% load component_tags %}` (or add the library to your template builtins)."
)


def discover() -> ReferencePage:
    """Build the Template Tags ``ReferencePage`` from the ``BaseNode`` subclasses."""
    entries: list[ReferenceEntry] = []
    seen: set[str] = set()
    for module_info in pkgutil.iter_modules(templatetags_pkg.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"django_components.templatetags.{module_info.name}")
        for _, obj in inspect.getmembers(module):
            if not (inspect.isclass(obj) and issubclass(obj, BaseNode) and obj is not BaseNode):
                continue
            tag = getattr(obj, "tag", None)
            if not tag or tag in seen:
                continue
            seen.add(tag)
            entries.append(
                ReferenceEntry(
                    kind="template_tag",
                    dotted_path=f"{obj.__module__}.{obj.__qualname__}",
                    display_name=tag,
                )
            )

    entries.sort(key=lambda e: e.display_name)
    return ReferencePage(
        slug="template_tags",
        title="Template tags",
        preface_md=_PREFACE,
        entries=tuple(entries),
        description="API reference - the django-components template tags.",
    )
