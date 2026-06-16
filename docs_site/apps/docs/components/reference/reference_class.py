"""
``ReferenceClass`` - the workhorse entry renderer (feature 4.23).

Renders one class-like symbol: a heading (new short anchor + legacy dotted-path
anchor + symbol badge), the call/init signature with cross-linked types, the
structured docstring (Google sections), and - for classes - the grouped members.
Covers kinds 1-6, 15, 18-19 (general classes, functions, decorators, instances,
NamedTuples, exceptions, the testing entrypoint, extension command / URL objects).

What renders depends on the griffe kind:
- class    -> init signature + docstring + members
- function -> call signature (with return) + docstring
- attribute/instance -> typed line + docstring
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.docs.reference.annotation import render_annotation
from apps.docs.reference.badges import symbol_badge
from apps.docs.reference.crossrefs import make_type_resolver
from apps.docs.reference.discovery.walk import resolve
from apps.docs.reference.docstring import render_docstring_html
from apps.docs.reference.members import render_members
from apps.docs.reference.signatures import render_signature

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry

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

    # The legacy dotted-path anchor (e.g. id="django_components.Component") sits
    # inside the heading so old inbound links still land here, alongside the new
    # short anchor (id="Component"). Verified against the deployed site: the old
    # anchor was the top-level dotted path (feature 4.58).
    template: types.django_html = """
        <div class="doc doc-object doc-class">
            <h2 id="{{ canonical_anchor }}" class="doc doc-heading">
                <span id="{{ legacy_anchor }}" class="doc doc-legacy-anchor"></span>
                {{ badge_html|safe }}<span class="doc doc-object-name doc-class-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ canonical_anchor }}" title="Permanent link">¤</a>
            </h2>
            <div class="doc doc-contents">
                {{ signature_html|safe }}
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
        kind = getattr(obj.kind, "value", "class")

        signature_html = ""
        annotation = getattr(obj, "annotation", None)
        if kind in ("class", "function"):
            signature_html = render_signature(obj, display_name=entry.display_name, resolve=resolver)
        elif annotation is not None:
            type_html = render_annotation(annotation, resolver)
            signature_html = (
                f'<div class="doc-signature highlight"><pre><code>{entry.display_name}: {type_html}</code></pre></div>'
            )

        body_html, _unresolved = render_docstring_html(obj, current_url=current_url, resolve=resolver)

        members_html = ""
        if kind == "class":
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
            "badge_html": symbol_badge(_GRIFFE_KIND_TO_CSS.get(kind, "class")),
            "signature_html": signature_html,
            "body_html": body_html,
            "members_html": members_html,
        }
