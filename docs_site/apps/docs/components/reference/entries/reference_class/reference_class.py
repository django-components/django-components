"""
``ReferenceClass`` - the workhorse entry renderer (feature 4.23).

Renders one class-like symbol: a heading (with the new short anchor + the legacy
dotted-path anchor + a symbol badge) followed by the docstring body. In the full
phase this covers kinds 1-6, 15, 18-19 (general classes, functions, decorators,
instances, NamedTuples, exceptions, the testing entrypoint, extension command /
URL objects). Chunk A exercises it on the three exception classes.

Not yet handled here (deferred to the Component/api escalation, Chunk B, where a
symbol with real members exists to test them): the parameter/signature block,
member grouping, and inherited members. Exceptions have none of these, so adding
them now would be untested speculation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.docs.components.reference.badges import symbol_badge
from apps.docs.components.reference.docstring import render_docstring_html
from apps.docs.discovery.walk import resolve

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.discovery.kinds import ReferenceEntry

# griffe object kind -> CSS symbol class used by the heading badge.
_GRIFFE_KIND_TO_CSS = {
    "class": "class",
    "function": "function",
    "attribute": "attribute",
    "module": "module",
}


@register("reference_class")
class ReferenceClass(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    # The legacy dotted-path anchor (e.g. id="django_components.AlreadyRegistered")
    # sits inside the heading so old inbound links still land here, alongside the
    # new short anchor (id="AlreadyRegistered"). Verified against the deployed
    # site: the old anchor was the top-level dotted path (feature 4.58).
    template: types.django_html = """
        <div class="doc doc-object doc-class">
            <h2 id="{{ canonical_anchor }}" class="doc doc-heading">
                <span id="{{ legacy_anchor }}" class="doc doc-legacy-anchor"></span>
                {{ badge_html|safe }}<span class="doc doc-object-name doc-class-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ canonical_anchor }}" title="Permanent link">¤</a>
            </h2>
            <div class="doc doc-contents">
                {{ body_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        obj = resolve(entry.dotted_path)

        docstring_value = obj.docstring.value if obj.docstring else ""
        body_html, _unresolved = render_docstring_html(docstring_value, current_url=kwargs.current_url)

        css_kind = _GRIFFE_KIND_TO_CSS.get(obj.kind.value, "class")

        return {
            "display_name": entry.display_name,
            "canonical_anchor": entry.canonical_anchor,
            "legacy_anchor": entry.legacy_anchor,
            "badge_html": symbol_badge(css_kind),
            "body_html": body_html,
        }
