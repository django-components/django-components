"""
Merge raw-HTML headings into the table of contents.

python-markdown's ``toc`` extension only sees markdown headings (``#``, ``##``).
The API reference emits its symbol headings as raw HTML (via the
``{% docstring %}`` tag, passed through ``md_in_html``), so the toc extension
never sees them and the right-rail TOC would miss every symbol.

This module rebuilds the toc token tree from the rendered HTML when - and only
when - such headings are present, so a normal content page (whose headings are
all markdown) is returned untouched. It also lifts each symbol's members (the
``h4`` ``doc-member-heading``s) into the tree and records the symbol *kind*
(``class``/``method``/``attribute``/...) so the rail can show the type badge and
nest members under their class.
"""

from __future__ import annotations

import lxml.html

# Heading levels the right-rail TOC tracks: page sections (h2/h3) plus, on
# reference pages, each symbol's members (h4 `doc-member-heading`s). h1 (the page
# title) is kept in the tree but unwrapped by the flattener so it isn't listed.
_HEADING_TAGS = {"h1", "h2", "h3", "h4"}


def merge_html_headings_into_toc(content_html: str, toc_tokens: list) -> list:
    """
    Return a toc token tree that also covers raw-HTML headings in the content.

    Keeps the page-structural headings: the ones markdown already tracked, plus
    reference symbol headings (class ``doc-heading``) and their members (class
    ``doc-member-heading``). Headings that live inside a docstring body are left
    out. Returns ``toc_tokens`` unchanged when there's nothing raw to add.
    """
    existing_ids = _collect_ids(toc_tokens)
    dom_headings = _extract_headings(content_html)
    kept = [
        (lvl, hid, name, kind)
        for (lvl, hid, name, cls, kind) in dom_headings
        if hid in existing_ids or "doc-heading" in cls or "doc-member-heading" in cls
    ]

    # Nothing raw to add (every kept heading is already in the markdown toc).
    if all(hid in existing_ids for (_, hid, _, _) in kept):
        return toc_tokens

    existing_names = _collect_names(toc_tokens)
    enriched = [(lvl, hid, existing_names.get(hid, name), kind) for (lvl, hid, name, kind) in kept]
    return _build_tree(enriched)


def _extract_headings(content_html: str) -> list[tuple[int, str, str, str, str]]:
    """Document-order (level, id, label, class, kind) for every id'd h1-h4 in the HTML."""
    if not content_html.strip():
        return []

    # Wrap in a single root so multi-element fragments parse whole (fragment
    # parsing otherwise stops at the first top-level element).
    frag = lxml.html.fromstring(f"<div>{content_html}</div>")

    # Materialize first: we mutate each heading below (dropping its permalink),
    # and mutating the tree while iterating it would abort the iteration.
    heading_els = [el for el in frag.iter() if isinstance(el.tag, str) and el.tag in _HEADING_TAGS and el.get("id")]

    headings: list[tuple[int, str, str, str, str]] = []
    for el in heading_els:
        # Drop the permalink anchor so its glyph doesn't end up in the label.
        for anchor in el.findall(".//a"):
            if "headerlink" in (anchor.get("class") or ""):
                anchor.drop_tree()
        headings.append((int(el.tag[1]), el.get("id"), _heading_label(el), el.get("class") or "", _heading_kind(el)))
    return headings


def _heading_label(el: lxml.html.HtmlElement) -> str:
    """
    The clean symbol name: the ``doc-object-name`` span's text when present (so a
    member label is just its name, without the type badge or the
    classmethod/property note), otherwise the heading's full text.
    """
    for span in el.iter("span"):
        if "doc-object-name" in (span.get("class") or "").split():
            return " ".join(span.text_content().split())
    return " ".join(el.text_content().split())


def _heading_kind(el: lxml.html.HtmlElement) -> str:
    """
    The symbol kind (``class``/``method``/``attribute``/...) read from the badge
    span's ``doc-symbol-{kind}`` class, or ``""`` for a plain content heading.
    """
    for span in el.iter("span"):
        for cls in (span.get("class") or "").split():
            if cls.startswith("doc-symbol-") and cls != "doc-symbol-heading":
                return cls.removeprefix("doc-symbol-")
    return ""


def _collect_ids(tokens: list) -> set[str]:
    ids: set[str] = set()
    for token in tokens:
        if token.get("id"):
            ids.add(token["id"])
        ids |= _collect_ids(token.get("children", []))
    return ids


def _collect_names(tokens: list) -> dict[str, str]:
    names: dict[str, str] = {}
    for token in tokens:
        if token.get("id"):
            names[token["id"]] = token.get("name", token["id"])
        names.update(_collect_names(token.get("children", [])))
    return names


def _build_tree(headings: list[tuple[int, str, str, str]]) -> list:
    """Build a nested toc tree from a flat document-order heading list."""
    root: list = []
    stack: list[tuple[int, dict]] = []  # (level, node)
    for level, hid, name, kind in headings:
        node = {"id": hid, "name": name, "level": level, "kind": kind, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        (stack[-1][1]["children"] if stack else root).append(node)
        stack.append((level, node))
    return root
