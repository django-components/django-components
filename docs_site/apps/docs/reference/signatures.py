"""
Render a symbol's signature to a cross-linked HTML code block (feature 4.35).

This is the "separate_signature + show_signature_annotations" replacement: a
monospace block under the heading showing the call signature with each parameter
type linked via the annotation renderer. Because the annotations carry ``<a>``
links, the block is built as HTML directly (not run through Pygments, which would
escape them).

Works for classes (``obj.parameters`` is the merged ``__init__`` signature -
"merge_init_into_class" comes free with griffe) and functions (adds ``-> Return``).
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from apps.docs.reference.annotation import render_annotation

if TYPE_CHECKING:
    from collections.abc import Callable

    import griffe

# Implicit first parameters that read as noise in rendered signatures.
_IMPLICIT_FIRST = {"self", "cls"}
# Wrap onto multiple lines past this many parameters.
_WRAP_THRESHOLD = 2


def render_signature(obj: griffe.Object, *, display_name: str, resolve: Callable[[str, str], str | None]) -> str:
    """Render ``obj``'s signature as a cross-linked HTML code block."""
    parameters = list(getattr(obj, "parameters", []) or [])
    params = [p for p in parameters if p.name not in _IMPLICIT_FIRST]

    rendered = [_render_param(p, resolve) for p in params]
    name = html.escape(display_name)

    if not rendered:
        sig = f"{name}()"
    elif len(rendered) <= _WRAP_THRESHOLD:
        sig = f"{name}({', '.join(rendered)})"
    else:
        body = ",\n".join(f"    {item}" for item in rendered)
        sig = f"{name}(\n{body}\n)"

    returns = getattr(obj, "returns", None)
    if returns is not None:
        sig += f" -> {render_annotation(returns, resolve)}"

    return f'<div class="doc-signature highlight"><pre><code>{sig}</code></pre></div>'


def _render_param(param: griffe.Parameter, resolve: Callable[[str, str], str | None]) -> str:
    # *args / **kwargs prefixes from the parameter kind.
    prefix = ""
    kind = getattr(param.kind, "name", "")
    if kind == "var_positional":
        prefix = "*"
    elif kind == "var_keyword":
        prefix = "**"

    out = prefix + html.escape(param.name)
    if param.annotation is not None:
        out += f": {render_annotation(param.annotation, resolve)}"
    if param.default is not None:
        # griffe gives defaults as source text (e.g. "None", "'document'").
        out += f" = {html.escape(str(param.default))}"
    return out
