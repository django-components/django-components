"""
Discovery for the Testing API reference page (feature 4.13).

Port of ``gen_reference_testing_api``: every public symbol exported from
``django_components.testing`` (currently just ``djc_test``). Each renders via
``ReferenceClass`` (kind ``"class"``), which dispatches on the griffe kind - so a
decorator *function* like ``djc_test`` renders as a signature + docstring with no
members, exactly like the functions on the API page. The dotted path keeps the
``django_components.testing.<name>`` module segment to match the old anchors.
"""

from __future__ import annotations

import inspect

import django_components.testing as testing_module
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage


def discover() -> ReferencePage:
    """Build the Testing API ``ReferencePage`` from ``django_components.testing``."""
    entries = [
        ReferenceEntry(
            kind="class",
            dotted_path=f"django_components.testing.{name}",
            display_name=name,
            # Match the old per-`:::` block, which set show_if_no_docstring.
            options={"show_if_no_docstring": True},
        )
        # inspect.getmembers returns names alphabetically, matching the old page.
        for name, obj in inspect.getmembers(testing_module)
        if not name.startswith("_") and not inspect.ismodule(obj)
    ]
    return ReferencePage(
        slug="testing_api",
        title="Testing API",
        preface_md="",
        entries=tuple(entries),
        description="API reference - Testing API.",
    )
