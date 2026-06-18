"""
Discovery for the Exceptions reference page (feature 4.5).

This is the proof-of-concept page: the smallest distinct reference page (3
entries, all plain classes), used to validate the discovery -> rendering
contract end-to-end before scaling to the other 13 pages. Port of
``gen_reference_exceptions`` (``the old mkdocs scripts/reference.py``).
"""

from __future__ import annotations

import inspect

import django_components
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage


def _public_names() -> list[str]:
    """Public names exported from the package (the ``__init__`` contract)."""
    names = getattr(django_components, "__all__", None)
    if names:
        return list(names)
    return [n for n in dir(django_components) if not n.startswith("_")]


def discover() -> ReferencePage:
    """Build the Exceptions ``ReferencePage`` from the public API."""
    entries = [
        ReferenceEntry(
            kind="class",
            dotted_path=f"django_components.{name}",
            display_name=name,
            # The old per-`:::` block set show_if_no_docstring: true for this
            # page, so docstring-less exceptions would still appear.
            options={"show_if_no_docstring": True},
        )
        # Sorted to match the old inspect.getmembers() ordering (alphabetical).
        for name in sorted(_public_names())
        if _is_public_exception(getattr(django_components, name, None))
    ]

    return ReferencePage(
        slug="exceptions",
        title="Exceptions",
        preface_md="",
        entries=tuple(entries),
        layout="repeater",
        description="API reference - Exceptions.",
    )


def _is_public_exception(obj: object) -> bool:
    return inspect.isclass(obj) and issubclass(obj, Exception)
