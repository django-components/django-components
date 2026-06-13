"""
Merge raw-HTML headings into the table of contents.

python-markdown's ``toc`` extension only sees markdown headings (``#``, ``##``).
The API reference emits its symbol headings as raw HTML (via the
``{% docstring %}`` tag, passed through ``md_in_html``), so the toc extension
never sees them and the right-rail TOC would miss every symbol.

This module rebuilds the toc token tree from the rendered HTML when - and only
when - such headings are present, so a normal content page (whose headings are
all markdown) is returned untouched.
"""

from __future__ import annotations

import lxml.html

# The right-rail TOC shows down to level 3.
_HEADING_TAGS = {"h1", "h2", "h3"}


def merge_html_headings_into_toc(content_html: str, toc_tokens: list) -> list:
    """
    Return a toc token tree that also covers raw-HTML headings in the content.

    Keeps the page-structural headings: the ones markdown already tracked, plus
    reference symbol headings (class ``doc-heading``). Headings that live inside
    a docstring body are left out of the page TOC. Returns ``toc_tokens``
    unchanged when there's nothing raw to add.
    """
    existing_ids = _collect_ids(toc_tokens)
    dom_headings = _extract_headings(content_html)
    kept = [(lvl, hid, name) for (lvl, hid, name, cls) in dom_headings if hid in existing_ids or "doc-heading" in cls]

    # Nothing raw to add (every kept heading is already in the markdown toc).
    if all(hid in existing_ids for (_, hid, _) in kept):
        return toc_tokens

    existing_names = _collect_names(toc_tokens)
    enriched = [(lvl, hid, existing_names.get(hid, name)) for (lvl, hid, name) in kept]
    return _build_tree(enriched)


def _extract_headings(content_html: str) -> list[tuple[int, str, str, str]]:
    """Document-order (level, id, label, class) for every id'd h1-h3 in the HTML."""
    if not content_html.strip():
        return []

    # Wrap in a single root so multi-element fragments parse whole (fragment
    # parsing otherwise stops at the first top-level element).
    frag = lxml.html.fromstring(f"<div>{content_html}</div>")

    # Materialize first: we mutate each heading below (dropping its permalink),
    # and mutating the tree while iterating it would abort the iteration.
    heading_els = [el for el in frag.iter() if isinstance(el.tag, str) and el.tag in _HEADING_TAGS and el.get("id")]

    headings: list[tuple[int, str, str, str]] = []
    for el in heading_els:
        # Drop the permalink anchor so its glyph doesn't end up in the label.
        for anchor in el.findall(".//a"):
            if "headerlink" in (anchor.get("class") or ""):
                anchor.drop_tree()
        label = " ".join(el.text_content().split())
        headings.append((int(el.tag[1]), el.get("id"), label, el.get("class") or ""))
    return headings


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


def _build_tree(headings: list[tuple[int, str, str]]) -> list:
    """Build a nested toc tree from a flat document-order heading list."""
    root: list = []
    stack: list[tuple[int, dict]] = []  # (level, node)
    for level, hid, name in headings:
        node = {"id": hid, "name": name, "level": level, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        (stack[-1][1]["children"] if stack else root).append(node)
        stack.append((level, node))
    return root
