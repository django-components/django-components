"""
Render a griffe type annotation to HTML, with cross-reference links.

This is the heart of "signature_crossrefs" (feature 4.21): walk a griffe ``Expr``
tree and emit HTML where each referenced type (``Component``, ``Context``,
``Any``, ...) becomes a link if a resolver can place it - against project symbols
or an external inventory. Dotted attribute paths collapse to their leaf name
(``django.template.context.Context`` renders as a linked ``Context``), matching
how the old mkdocstrings output read.

The resolver is injected so this module stays decoupled from where URLs come
from: ``resolve(leaf_name, canonical_path) -> url | None``.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def render_annotation(expr: object, resolve: Callable[[str, str], str | None]) -> str:
    """Render an annotation (a griffe ``Expr``, a ``str``, or ``None``) to HTML."""
    if expr is None:
        return ""
    return _render(expr, resolve)


def _render(node: object, resolve: Callable[[str, str], str | None]) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return html.escape(node)

    kind = type(node).__name__
    handler = _HANDLERS.get(kind)
    if handler is not None:
        return handler(node, resolve)

    # Unknown Expr type: fall back to a flat token walk so we still link the
    # names we can, rather than dropping to an unlinked str().
    return _render_flat(node, resolve)


def _link(name: str, canonical_path: str, resolve: Callable[[str, str], str | None]) -> str:
    url = resolve(name, canonical_path)
    text = html.escape(name)
    if url:
        return f'<a class="doc-type-link" href="{html.escape(url)}">{text}</a>'
    return text


def _render_name(node: object, resolve: Callable[[str, str], str | None]) -> str:
    name = getattr(node, "name", None) or str(node)
    canonical = getattr(node, "canonical_path", name)
    return _link(name, canonical, resolve)


def _render_attribute(node: object, resolve: Callable[[str, str], str | None]) -> str:
    # Dotted path (a.b.C): show + link only the leaf, keyed on its full path.
    values = list(getattr(node, "values", []))
    if not values:
        return html.escape(str(node))
    leaf = values[-1]
    name = getattr(leaf, "name", None) or str(leaf)
    canonical = getattr(leaf, "canonical_path", name)
    return _link(name, canonical, resolve)


def _render_subscript(node: Any, resolve: Callable[[str, str], str | None]) -> str:
    return f"{_render(node.left, resolve)}[{_render(node.slice, resolve)}]"


def _render_binop(node: Any, resolve: Callable[[str, str], str | None]) -> str:
    op = html.escape(str(node.operator))
    return f"{_render(node.left, resolve)} {op} {_render(node.right, resolve)}"


def _render_sequence(node: Any, resolve: Callable[[str, str], str | None]) -> str:
    inner = ", ".join(_render(el, resolve) for el in node.elements)
    return f"[{inner}]" if type(node).__name__ == "ExprList" else inner


def _render_flat(node: object, resolve: Callable[[str, str], str | None]) -> str:
    iterate = getattr(node, "iterate", None)
    if iterate is None:
        return html.escape(str(node))
    parts: list[str] = []
    for token in iterate(flat=True):
        if isinstance(token, str):
            parts.append(html.escape(token))
        elif type(token).__name__ == "ExprName":
            parts.append(_render_name(token, resolve))
        else:
            parts.append(html.escape(str(token)))
    return "".join(parts)


_HANDLERS: dict[str, Callable[[object, Callable[[str, str], str | None]], str]] = {
    "ExprName": _render_name,
    "ExprAttribute": _render_attribute,
    "ExprSubscript": _render_subscript,
    "ExprBinOp": _render_binop,
    "ExprTuple": _render_sequence,
    "ExprList": _render_sequence,
}
