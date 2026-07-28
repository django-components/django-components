"""
``ReferenceTemplateTag`` - renders one template tag (feature 4.28).

Builds the ``{% tag … %}`` signature block from the node class's runtime
attributes (``_signature`` set by ``BaseNodeMeta``, plus ``tag`` / ``end_tag`` /
``allowed_flags``), then the source link and the tag's docstring. The heading
anchor is the tag name (single anchor - the old page used ``## <tag>``).
"""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Any

from apps.docs.reference.docstring import render_markdown
from apps.docs.reference.runtime import import_symbol, source_link

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry


@register("reference_template_tag")
class ReferenceTemplateTag(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    template: types.django_html = """
        <div class="doc doc-object doc-template-tag">
            <h2 id="{{ anchor }}" class="doc doc-heading">
                <span class="doc doc-object-name doc-tag-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ anchor }}" title="Permanent link">¤</a>
            </h2>
            <div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{{ signature }}</code></pre></div>
                {{ source_html|safe }}
                {{ body_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        node_cls = import_symbol(entry.dotted_path)
        return {
            "anchor": entry.display_name,
            "display_name": entry.display_name,
            "signature": _format_tag_signature(node_cls),
            "source_html": source_link(node_cls),
            "body_html": render_markdown(dedent(node_cls.__doc__ or ""), current_url=kwargs.current_url),
        }


def _format_tag_signature(node_cls: Any) -> str:
    # `_signature` stringifies as "(arg: int, **kwargs: Any) -> str"; we want the
    # parameters only, recast as a `{% tag … %}` block (+ flags, + end tag).
    params = str(node_cls._signature).rsplit("->", 1)[0].strip()
    params = params[1:-1].strip()  # drop the outer parentheses
    if node_cls.allowed_flags:
        flags = " ".join(f"[{flag}]" for flag in node_cls.allowed_flags)
        params = f"{params} {flags}".strip()

    body = f"{{% {node_cls.tag}{f' {params}' if params else ''} %}}"
    if node_cls.end_tag:
        body += f"\n{{% {node_cls.end_tag} %}}"
    return body
