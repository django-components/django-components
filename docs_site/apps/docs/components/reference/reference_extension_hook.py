"""
``ReferenceExtensionHook`` - renders one ``ComponentExtension`` hook (feature 4.30).

A hook is an ``on_*`` method whose single ``ctx`` argument is a context object.
The renderer shows the method signature + docstring, then an "Available data"
table built from that context's fields. Rendered at ``<h3>`` because hooks sit
under the page's ``## Hooks`` section.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.docs.reference.badges import symbol_badge
from apps.docs.reference.crossrefs import make_type_resolver
from apps.docs.reference.discovery.walk import resolve
from apps.docs.reference.docstring import render_docstring_html
from apps.docs.reference.fields import render_fields_table
from apps.docs.reference.signatures import render_signature

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry

_CONTEXT_MODULE = "django_components.extension"


@register("reference_extension_hook")
class ReferenceExtensionHook(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    template: types.django_html = """
        <div class="doc doc-object doc-hook">
            <h3 id="{{ canonical_anchor }}" class="doc doc-heading">
                <span id="{{ legacy_anchor }}" class="doc doc-legacy-anchor"></span>
                {{ badge_html|safe }}<span class="doc doc-object-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ canonical_anchor }}" title="Permanent link">¤</a>
            </h3>
            <div class="doc doc-contents">
                {{ signature_html|safe }}
                {{ body_html|safe }}
                {{ available_data_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        current_url = kwargs.current_url
        method = resolve(entry.dotted_path)
        resolver = make_type_resolver(current_url)

        body_html, _unresolved = render_docstring_html(method, current_url=current_url, resolve=resolver, base_level=3)

        return {
            "display_name": entry.display_name,
            "canonical_anchor": entry.canonical_anchor,
            "legacy_anchor": entry.legacy_anchor,
            "badge_html": symbol_badge("method"),
            "signature_html": render_signature(method, display_name=entry.display_name, resolve=resolver),
            "body_html": body_html,
            "available_data_html": _available_data(method, resolver, current_url),
        }


def _available_data(method: Any, resolver: Any, current_url: str) -> str:
    ctx_param = next((p for p in getattr(method, "parameters", []) if p.name == "ctx"), None)
    if ctx_param is None or ctx_param.annotation is None:
        return ""
    ctx_name = str(ctx_param.annotation).split(".")[-1]
    try:
        context_obj = resolve(f"{_CONTEXT_MODULE}.{ctx_name}")
    except KeyError:
        return ""
    return render_fields_table(context_obj, resolve=resolver, current_url=current_url, title="Available data")
