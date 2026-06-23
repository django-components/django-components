"""
Discovery for the Template Variables reference page (feature 4.12).

The variables available inside a component's template (under ``component_vars``)
are the fields of ``ComponentVars``. Each field renders via ``ReferenceSetting``
(name + type + docstring), the same shape as a setting. Port of
``gen_reference_template_variables``.
"""

from __future__ import annotations

from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage
from django_components.component import ComponentVars

_CLASS = "django_components.component.ComponentVars"
_INTRO = (
    "These variables are available inside a component's template via the "
    "`component_vars` object (e.g. `{{ component_vars.args }}`). They are the "
    "fields of [`ComponentVars`][ComponentVars]."
)


def discover() -> ReferencePage:
    """Build the Template Variables ``ReferencePage`` from the ``ComponentVars`` fields."""
    entries = [
        ReferenceEntry(kind="setting", dotted_path=f"{_CLASS}.{field}", display_name=field)
        for field in ComponentVars._fields
    ]
    return ReferencePage(
        slug="template_variables",
        title="Template variables",
        preface_md=_INTRO,
        entries=tuple(entries),
        description="API reference - the variables available inside component templates.",
    )
