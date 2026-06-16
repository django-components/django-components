"""
``ReferenceComponentClass`` - renders one predefined Component subclass (feature 4.24).

Like ``ReferenceClass`` but without the call signature, and showing only the
subclass's *own* members - not the ~60 it inherits from ``Component``. griffe's
static ``.members`` is already own-only, so no explicit base-class filtering is
needed (the old page used ``_get_unique_methods`` because it walked ``dir()``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.docs.reference.badges import symbol_badge
from apps.docs.reference.crossrefs import make_type_resolver
from apps.docs.reference.discovery.walk import resolve
from apps.docs.reference.docstring import render_docstring_html
from apps.docs.reference.members import render_members

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry


@register("reference_component_class")
class ReferenceComponentClass(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    template: types.django_html = """
        <div class="doc doc-object doc-class doc-component">
            <h2 id="{{ canonical_anchor }}" class="doc doc-heading">
                <span id="{{ legacy_anchor }}" class="doc doc-legacy-anchor"></span>
                {{ badge_html|safe }}<span class="doc doc-object-name doc-class-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ canonical_anchor }}" title="Permanent link">¤</a>
            </h2>
            <div class="doc doc-contents">
                {{ body_html|safe }}
                {{ members_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        current_url = kwargs.current_url
        obj = resolve(entry.dotted_path)
        resolver = make_type_resolver(current_url)

        body_html, _unresolved = render_docstring_html(obj, current_url=current_url, resolve=resolver)
        members_html = render_members(
            obj,
            parent_name=entry.display_name,
            parent_path=entry.dotted_path,
            current_url=current_url,
            resolve=resolver,
        )

        return {
            "display_name": entry.display_name,
            "canonical_anchor": entry.canonical_anchor,
            "legacy_anchor": entry.legacy_anchor,
            "badge_html": symbol_badge("class"),
            "body_html": body_html,
            "members_html": members_html,
        }
