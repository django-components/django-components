"""
Cross-reference resolution for docstrings (the Chunk-A subset of feature 4.41).

Docstrings use bracket cross-refs - ``[Component][Component]`` or
``[text][ComponentRegistry.register]`` - per the project's docstring convention.
This module rewrites those, in the markdown *before* it is converted to HTML, to
real relative links when the target is a known reference symbol.

Scope note: this Chunk-A version resolves only *project* symbols (whatever
discovery has found). External inventory linking (Python stdlib + Django via
``objects.inv``) and the in-signature cross-refs are Chunk B (features 4.20-4.22).
Until then, a ref to a not-yet-discovered or external symbol is rendered as its
plain display text (not a broken ``[x][y]`` literal) and reported as unresolved
so a future guard can flag it.
"""

from __future__ import annotations

import posixpath
import re
from functools import lru_cache

from apps.docs.discovery.registry import discover_pages

# [text][key] and the shortcut [text][] (key defaults to a symbol parsed from text)
_CROSSREF_RE = re.compile(r"\[([^\]\[]+)\]\[([^\]\[]*)\]")
# Strip backticks / a trailing "()" so [`unregister()`][] keys off "unregister"
_SYMBOL_CLEAN_RE = re.compile(r"[`\s]")


def reference_page_url(slug: str) -> str:
    """
    Clean URL path (no leading slash) for a reference page, e.g.
    ``"docs/reference/exceptions/"``.
    """
    return f"docs/reference/{slug}/"


@lru_cache(maxsize=1)
def symbol_url_index() -> dict[str, str]:
    """
    Map a symbol key to its clean URL path + anchor, e.g.
    ``"AlreadyRegistered" -> "docs/reference/exceptions/#AlreadyRegistered"``.

    Keyed by both the public dotted path and the short display name (docstring
    cross-refs use the short form).
    """
    index: dict[str, str] = {}
    for page in discover_pages():
        base = reference_page_url(page.slug)
        for entry in page.entries:
            url = f"{base}#{entry.canonical_anchor}"
            index[entry.dotted_path] = url
            index.setdefault(entry.display_name, url)
    return index


def resolve_crossrefs(md: str, *, current_url: str, index: dict[str, str] | None = None) -> tuple[str, list[str]]:
    """
    Rewrite bracket cross-refs in a markdown string.

    Returns the rewritten markdown and the list of cross-ref keys that could not
    be resolved (left as plain text). ``current_url`` is the clean URL of the page
    being rendered, used to make the links relative.
    """
    idx = symbol_url_index() if index is None else index
    unresolved: list[str] = []

    def replace(match: re.Match[str]) -> str:
        text, key = match.group(1), match.group(2)
        lookup = key or _SYMBOL_CLEAN_RE.sub("", text).removesuffix("()")
        target = idx.get(lookup)
        if target is None:
            unresolved.append(lookup)
            # Degrade to the display text (keeps inline code), never a [x][y] literal.
            return text
        return f"[{text}]({_relative_href(target, current_url)})"

    return _CROSSREF_RE.sub(replace, md), unresolved


def _relative_href(target_url: str, current_url: str) -> str:
    """Relative href from ``current_url`` (a clean page URL) to ``target_url``."""
    target_path, _, anchor = target_url.partition("#")
    cur = current_url.strip("/")
    tgt = target_path.strip("/")
    anchor_suffix = f"#{anchor}" if anchor else ""
    if cur == tgt:
        return anchor_suffix or "#"
    rel = posixpath.relpath(tgt, cur) if cur else tgt
    if not rel.endswith("/"):
        rel += "/"
    return rel + anchor_suffix
