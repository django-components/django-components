"""
Render a context object's fields as a table (features 4.30 / 4.31).

Shared by the extension-hook renderer (the "Available data" table) and the
hook-context renderer (the object's own field listing). Walks a griffe object's
attribute members and emits a name / type / description table - types are
cross-linked via the annotation renderer, descriptions are the per-field
docstrings (now clean, since the source-code extension skips class-member
attributes).
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

import griffe

from apps.docs.reference.annotation import render_annotation
from apps.docs.reference.docstring import render_markdown

if TYPE_CHECKING:
    from collections.abc import Callable

_P_WRAP = re.compile(r"^<p>(.*)</p>$", re.DOTALL)


def render_fields_table(
    obj: griffe.Object,
    *,
    resolve: Callable[[str, str], str | None],
    current_url: str,
    title: str,
) -> str:
    """Render ``obj``'s attribute members as a ``Field | Type | Description`` table."""
    rows: list[str] = []
    for name, member in obj.members.items():
        if name.startswith("_"):
            continue
        field = member.final_target if isinstance(member, griffe.Alias) else member
        if getattr(field.kind, "value", "") != "attribute":
            continue
        annotation = getattr(field, "annotation", None)
        type_html = render_annotation(annotation, resolve) if annotation is not None else ""
        desc = _inline(render_markdown(field.docstring.value if field.docstring else "", current_url=current_url))
        rows.append(f"<tr><td><code>{html.escape(name)}</code></td><td>{type_html}</td><td>{desc}</td></tr>")

    if not rows:
        return ""
    return (
        f'<div class="doc-section doc-fields"><p class="doc-section-title">{html.escape(title)}</p>'
        '<table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _inline(rendered: str) -> str:
    """Unwrap a single enclosing ``<p>`` so the text sits in a table cell."""
    rendered = rendered.strip()
    match = _P_WRAP.match(rendered)
    return match.group(1) if match else rendered
