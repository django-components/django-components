"""
Discovery for the API reference page (feature 4.4).

Port of ``gen_reference_api``: every public symbol exported from
``django_components`` except those that have their own dedicated page
(components, exceptions, tag formatters, extension command/hook/URL APIs). All of
them render via ``ReferenceClass`` (kind ``"class"``), which dispatches on the
griffe kind internally (class / function / attribute).
"""

from __future__ import annotations

import inspect

import django_components
from apps.docs.reference.discovery import introspect
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage

# Symbols handled on other reference pages, excluded from the general API page.
_EXCLUDE = (
    introspect.is_component_cls,
    introspect.is_error_cls,
    introspect.is_tag_formatter_cls,
    introspect.is_tag_formatter_instance,
    introspect.is_extension_hook_api,
    introspect.is_extension_command_api,
    introspect.is_extension_url_api,
)


def discover() -> ReferencePage:
    """Build the API ``ReferencePage`` from the public API surface."""
    entries = [
        ReferenceEntry(
            kind="class",
            dotted_path=f"django_components.{name}",
            display_name=name,
            options={"show_if_no_docstring": True},
        )
        for name in sorted(introspect.public_names())
        if _is_api_symbol(getattr(django_components, name, None))
    ]
    return ReferencePage(
        slug="api",
        title="API",
        preface_md="",
        entries=tuple(entries),
        description="The django-components Python API reference.",
    )


def _is_api_symbol(obj: object) -> bool:
    if obj is None or inspect.ismodule(obj):
        return False
    return not any(is_excluded(obj) for is_excluded in _EXCLUDE)
