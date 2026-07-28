"""
``ReferenceTagFormatter`` - renders one TagFormatter class (feature 4.26).

A "naked class card": heading + docstring only. Unlike ``ReferenceClass`` it
shows no signature, no members and no symbol badge (the old page set
``members: false`` / ``show_signature: false``) - a tag formatter's docstring
already carries everything worth documenting (its example tag syntax).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.docs.reference.crossrefs import make_type_resolver
from apps.docs.reference.discovery.walk import resolve
from apps.docs.reference.docstring import render_docstring_html

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry


@register("reference_tag_formatter")
class ReferenceTagFormatter(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    template: types.django_html = """
        <div class="doc doc-object doc-class doc-tag-formatter">
            <h2 id="{{ canonical_anchor }}" class="doc doc-heading">
                <span id="{{ legacy_anchor }}" class="doc doc-legacy-anchor"></span>
                <span class="doc doc-object-name doc-class-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ canonical_anchor }}" title="Permanent link">¤</a>
            </h2>
            <div class="doc doc-contents">
                {{ body_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        current_url = kwargs.current_url
        obj = resolve(entry.dotted_path)
        resolver = make_type_resolver(current_url)
        body_html, _unresolved = render_docstring_html(obj, current_url=current_url, resolve=resolver)
        return {
            "display_name": entry.display_name,
            "canonical_anchor": entry.canonical_anchor,
            "legacy_anchor": entry.legacy_anchor,
            "body_html": body_html,
        }
