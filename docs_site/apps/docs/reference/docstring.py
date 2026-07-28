"""
Docstring -> HTML rendering (feature 4.38, ``DocstringBody``).

Parses a griffe docstring into Google-style sections and renders each by kind:

- text -> markdown (this is also where the bases / source-link HTML that the
  griffe extensions prepend rides along, passed through by ``md_in_html``)
- parameters -> a parameter table (feature 4.37), with types taken from the
  signature (so they cross-link) merged with the docstring descriptions
- returns / raises -> small labelled blocks
- examples -> rendered code blocks (feature 4.40)
- admonition -> a blockquote-style callout

Bracket cross-refs in prose are resolved while the content is still markdown.
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from apps.docs.reference.annotation import render_annotation
from apps.docs.reference.crossrefs import resolve_crossrefs

if TYPE_CHECKING:
    from collections.abc import Callable

    import griffe

_P_WRAP = re.compile(r"^<p>(.*)</p>$", re.DOTALL)


def render_docstring_html(
    obj: griffe.Object,
    *,
    current_url: str,
    resolve: Callable[[str, str], str | None],
    base_level: int = 2,
) -> tuple[str, list[str]]:
    """
    Render ``obj``'s docstring to HTML.

    ``base_level`` is the heading level of the container the docstring sits
    under (2 for a top-level symbol, 4 for a member); the docstring's own
    headings are demoted to nest beneath it. Returns the HTML and the list of
    unresolved cross-ref keys. An object with no docstring renders to "".
    """
    docstring = obj.docstring
    if docstring is None or not docstring.value.strip():
        return "", []

    sig_params = {p.name: p for p in getattr(obj, "parameters", []) or []}
    unresolved: list[str] = []
    parts: list[str] = []

    for section in _parse_sections(docstring):
        kind = getattr(section.kind, "value", str(section.kind))
        if kind == "parameters":
            parts.append(_render_parameters(section.value, sig_params, resolve, current_url, unresolved))
        elif kind == "returns":
            parts.append(_render_returns(section.value, obj, resolve, current_url, unresolved))
        elif kind == "raises":
            parts.append(_render_raises(section.value, resolve, current_url, unresolved))
        elif kind == "examples":
            parts.append(_render_examples(section.value))
        elif kind == "admonition":
            parts.append(_render_admonition(section, current_url, unresolved))
        else:  # text and anything we don't special-case
            parts.append(_markdown(str(section.value), current_url, unresolved))

    # Demote the docstring's own headings once over the assembled HTML so the
    # shallowest sits exactly one level under its container.
    html = _demote_headings("\n".join(p for p in parts if p), base_level)
    return html, unresolved


def _parse_sections(docstring: griffe.Docstring) -> list:
    try:
        return docstring.parse("google")
    except Exception:
        return []


_HEADING_TAG_RE = re.compile(r"<(/?)h([1-6])\b")


def _docstring_md_config() -> tuple[list[str], dict]:
    """
    Markdown settings for docstring fragments.

    Differs from the page pipeline in two ways that matter when many fragments
    render onto one page: ``toc`` is dropped (docstring headings shouldn't get
    page-level slugs that collide), and Pygments line anchors are off (each
    fragment restarts their numbering, which would dup ``__codelineno`` ids).
    """
    from apps.docs.build.pipeline import MD_EXTENSION_CONFIGS, MD_EXTENSIONS  # noqa: PLC0415

    extensions = [ext for ext in MD_EXTENSIONS if ext != "toc"]
    configs = dict(MD_EXTENSION_CONFIGS)
    configs["pymdownx.highlight"] = {**configs.get("pymdownx.highlight", {}), "anchor_linenums": False}
    return extensions, configs


def _demote_headings(html_fragment: str, base_level: int) -> str:
    """
    Shift docstring headings so the shallowest sits one level under its container.

    The page nests h1 (page) > h2 (symbol) > h3 (group) > h4 (member); a
    docstring's own ``#``/``##`` must continue below that without skipping a
    level or adding stray <h1>s. ``base_level`` is the container level (2 for a
    top-level symbol, 4 for a member), so the shallowest heading becomes
    ``base_level + 1`` and the rest shift with it (capped at h6).
    """
    levels = [int(level) for level in re.findall(r"<h([1-6])", html_fragment)]
    if not levels:
        return html_fragment
    shift = max(0, (base_level + 1) - min(levels))
    if shift == 0:
        return html_fragment
    return _HEADING_TAG_RE.sub(lambda m: f"<{m.group(1)}h{min(int(m.group(2)) + shift, 6)}", html_fragment)


def _md_to_html(text: str) -> str:
    import markdown  # type: ignore[import-untyped]  # noqa: PLC0415  # python-markdown ships no stubs

    extensions, configs = _docstring_md_config()
    md = markdown.Markdown(extensions=extensions, extension_configs=configs)
    return md.convert(text)


def render_markdown(text: str, *, current_url: str, base_level: int = 2) -> str:
    """
    Render a standalone markdown string (e.g. a command's help / description) to HTML.

    Same treatment as docstring prose - bracket cross-refs resolved, the docstring
    markdown extension set, heading demotion - but for text that doesn't arrive as
    a griffe docstring.
    """
    if not text or not text.strip():
        return ""
    resolved, _ = resolve_crossrefs(text, current_url=current_url)
    return _demote_headings(_md_to_html(resolved), base_level)


def _markdown(text: str, current_url: str, unresolved: list[str]) -> str:
    """Render a markdown fragment to HTML, resolving bracket cross-refs first."""
    if not text or not text.strip():
        return ""
    resolved, missing = resolve_crossrefs(text, current_url=current_url)
    unresolved.extend(missing)
    return _md_to_html(resolved)


def _markdown_inline(text: str, current_url: str, unresolved: list[str]) -> str:
    """Like ``_markdown`` but unwrap a single enclosing ``<p>`` (for table cells)."""
    rendered = _markdown(text, current_url, unresolved).strip()
    match = _P_WRAP.match(rendered)
    return match.group(1) if match else rendered


def _render_parameters(
    rows: list,
    sig_params: dict,
    resolve: Callable[[str, str], str | None],
    current_url: str,
    unresolved: list[str],
) -> str:
    body = []
    for row in rows:
        name = html.escape(row.name)
        # Prefer the signature's structured annotation (cross-linkable) over the
        # docstring's plain-text one.
        sig = sig_params.get(row.name)
        if sig is not None and sig.annotation is not None:
            type_html = render_annotation(sig.annotation, resolve)
        else:
            type_html = html.escape(str(row.annotation)) if row.annotation else ""

        desc = _markdown_inline(row.description or "", current_url, unresolved)
        default = getattr(row, "value", None)
        if default:
            desc += f' <span class="doc-param-default">(default: <code>{html.escape(str(default))}</code>)</span>'

        body.append(f"<tr><td><code>{name}</code></td><td>{type_html}</td><td>{desc}</td></tr>")

    return (
        '<table class="doc-params">'
        "<thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _render_returns(
    rows: list,
    obj: griffe.Object,
    resolve: Callable[[str, str], str | None],
    current_url: str,
    unresolved: list[str],
) -> str:
    items = []
    for row in rows:
        # Prefer the signature return annotation (cross-linkable).
        returns_ann = getattr(obj, "returns", None)
        if returns_ann is not None:
            type_html = render_annotation(returns_ann, resolve)
        else:
            type_html = html.escape(str(row.annotation)) if row.annotation else ""
        desc = _markdown_inline(row.description or "", current_url, unresolved)
        items.append(f"<li>{type_html}{' &ndash; ' + desc if desc else ''}</li>")
    return (
        f'<div class="doc-section doc-returns"><p class="doc-section-title">Returns</p><ul>{"".join(items)}</ul></div>'
    )


def _render_raises(
    rows: list,
    resolve: Callable[[str, str], str | None],
    current_url: str,
    unresolved: list[str],
) -> str:
    items = []
    for row in rows:
        type_html = render_annotation(row.annotation, resolve) if row.annotation is not None else ""
        desc = _markdown_inline(row.description or "", current_url, unresolved)
        items.append(f"<li>{type_html}{' &ndash; ' + desc if desc else ''}</li>")
    return (
        f'<div class="doc-section doc-raises"><p class="doc-section-title">Raises</p><ul>{"".join(items)}</ul></div>'
    )


def _render_examples(rows: list) -> str:
    # Each item is (kind, content); content is already markdown (often a fence).
    blocks = [_md_to_html(item[1] if isinstance(item, tuple) else str(item)) for item in rows]
    return f'<div class="doc-section doc-examples"><p class="doc-section-title">Example</p>{"".join(blocks)}</div>'


def _render_admonition(section: object, current_url: str, unresolved: list[str]) -> str:
    title = html.escape(str(getattr(section, "title", "") or "Note"))
    value = getattr(section, "value", "")
    text = value.contents if hasattr(value, "contents") else str(value)
    body = _markdown(text, current_url, unresolved)
    return f'<blockquote class="doc-admonition"><p class="doc-admonition-title">{title}</p>{body}</blockquote>'
