"""
Discovery for the Extension commands reference page (feature 4.15).

Port of ``gen_reference_extension_commands``: the objects used to define an
extension's CLI commands (``ComponentCommand``, ``CommandArg``, ...), detected by
the same marker the package itself uses (``is_extension_command_api``). Each
renders via ``ReferenceClass`` (kind ``"class"``). The dotted path is the
top-level ``django_components.<name>`` export, matching the old anchors.
"""

from __future__ import annotations

import django_components
from apps.docs.reference.discovery import introspect
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage

_INTRO = (
    "Overview of all classes, functions, and other objects related to defining "
    "extension commands.\n\nRead more on [Extensions](../concepts/advanced/extensions.md)."
)


def discover() -> ReferencePage:
    """Build the Extension commands ``ReferencePage`` from the marker-tagged API."""
    entries = [
        ReferenceEntry(
            kind="class",
            dotted_path=f"django_components.{name}",
            display_name=name,
            options={"show_if_no_docstring": True},
        )
        for name in sorted(introspect.public_names())
        if introspect.is_extension_command_api(getattr(django_components, name, None))
    ]
    return ReferencePage(
        slug="extension_commands",
        title="Extension commands",
        preface_md=_INTRO,
        entries=tuple(entries),
        description="API reference - Extension commands.",
    )
