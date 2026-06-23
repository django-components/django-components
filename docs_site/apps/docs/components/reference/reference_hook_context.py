"""
``ReferenceHookContext`` - renders one hook context object (feature 4.31).

The context objects (``OnComponentInputContext`` etc.) are NamedTuples. Rather
than the full member treatment ``ReferenceClass`` gives, these render compactly:
heading + class docstring + a ``Field | Type | Description`` table of their
fields. Rendered at ``<h3>`` under the page's ``## Objects`` section.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.docs.reference.badges import symbol_badge
from apps.docs.reference.crossrefs import make_type_resolver
from apps.docs.reference.discovery.walk import resolve
from apps.docs.reference.docstring import render_docstring_html
from apps.docs.reference.fields import render_fields_table

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry


@register("reference_hook_context")
class ReferenceHookContext(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    template: types.django_html = """
        <div class="doc doc-object doc-hook-context">
            <h3 id="{{ canonical_anchor }}" class="doc doc-heading">
                <span id="{{ legacy_anchor }}" class="doc doc-legacy-anchor"></span>
                {{ badge_html|safe }}<span class="doc doc-object-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ canonical_anchor }}" title="Permanent link">¤</a>
            </h3>
            <div class="doc doc-contents">
                {{ body_html|safe }}
                {{ fields_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        current_url = kwargs.current_url
        obj = resolve(entry.dotted_path)
        resolver = make_type_resolver(current_url)

        body_html, _unresolved = render_docstring_html(obj, current_url=current_url, resolve=resolver, base_level=3)

        return {
            "display_name": entry.display_name,
            "canonical_anchor": entry.canonical_anchor,
            "legacy_anchor": entry.legacy_anchor,
            "badge_html": symbol_badge("class"),
            "body_html": body_html,
            "fields_html": render_fields_table(obj, resolve=resolver, current_url=current_url, title="Fields"),
        }
