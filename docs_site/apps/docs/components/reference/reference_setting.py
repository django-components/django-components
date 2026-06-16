"""
``ReferenceSetting`` - renders one settings / template-variable field (feature 4.25).

A setting (a ``ComponentsSettings`` field) and a template variable (a
``ComponentVars`` field) are both NamedTuple attributes: a name, a type, and a
docstring. This renders them compactly - heading + ``name: type`` line +
docstring - with no symbol-type badge (per spike 5 section 3.2). The page-level
defaults panel is separate (it lives in the settings page preface).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.docs.reference.annotation import render_annotation
from apps.docs.reference.crossrefs import make_type_resolver
from apps.docs.reference.discovery.walk import resolve
from apps.docs.reference.docstring import render_docstring_html

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry


@register("reference_setting")
class ReferenceSetting(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    template: types.django_html = """
        <div class="doc doc-object doc-setting">
            <h2 id="{{ canonical_anchor }}" class="doc doc-heading">
                <span id="{{ legacy_anchor }}" class="doc doc-legacy-anchor"></span>
                <span class="doc doc-object-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ canonical_anchor }}" title="Permanent link">¤</a>
            </h2>
            <div class="doc doc-contents">
                {{ signature_html|safe }}
                {{ body_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        current_url = kwargs.current_url
        obj = resolve(entry.dotted_path)
        resolver = make_type_resolver(current_url)

        annotation = getattr(obj, "annotation", None)
        signature_html = ""
        if annotation is not None:
            type_html = render_annotation(annotation, resolver)
            signature_html = (
                f'<div class="doc-signature highlight"><pre><code>{entry.display_name}: {type_html}</code></pre></div>'
            )

        body_html, _unresolved = render_docstring_html(obj, current_url=current_url, resolve=resolver)

        return {
            "display_name": entry.display_name,
            "canonical_anchor": entry.canonical_anchor,
            "legacy_anchor": entry.legacy_anchor,
            "signature_html": signature_html,
            "body_html": body_html,
        }
