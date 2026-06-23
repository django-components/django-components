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
from typing import TYPE_CHECKING

from apps.docs.reference.discovery.registry import discover_pages
from apps.docs.reference.inventory import external_inventory

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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

    Keyed by the public dotted path, the short display name, and - so member
    cross-refs like ``[X][Component.get_js_data]`` and field refs like
    ``[X][ComponentsSettings.cache]`` resolve - by member and qualified-field
    keys that mirror the anchors the pages actually render.
    """
    # Lazy: these pull griffe + the members helper, which imports the docstring
    # renderer, which imports this module (cycle). Deferring to call time breaks it.
    from apps.docs.reference.discovery.walk import resolve  # noqa: PLC0415
    from apps.docs.reference.members import public_member_names  # noqa: PLC0415

    index: dict[str, str] = {}

    # Pass 1: entry-level keys. A symbol with its own dedicated entry (e.g. the
    # `cache` setting) must win over the same name seen as a member of another
    # entry (e.g. `ComponentsSettings.cache` on the API page), so these go first.
    for page in discover_pages():
        base = reference_page_url(page.slug)
        for entry in page.entries:
            url = f"{base}#{entry.canonical_anchor}"
            index[entry.dotted_path] = url
            index.setdefault(entry.display_name, url)
            # `ComponentsSettings.cache` etc. - the last two dotted-path segments
            # of a field entry, the form docstrings/content use to reference it.
            index.setdefault(".".join(entry.dotted_path.split(".")[-2:]), url)

    # Pass 2: member keys. Class/component members render `{DisplayName}.{member}`
    # anchors; index them so `[X][Component.get_js_data]` lands on the right one,
    # without overriding a dedicated entry claimed in pass 1.
    for page in discover_pages():
        base = reference_page_url(page.slug)
        for entry in page.entries:
            if entry.kind not in ("class", "component_class"):
                continue
            try:
                obj = resolve(entry.dotted_path)
            except Exception:  # noqa: S112 - non-griffe entries (commands, tags) simply have no members
                continue
            for member in public_member_names(obj):
                member_url = f"{base}#{entry.canonical_anchor}.{member}"
                index.setdefault(f"{entry.display_name}.{member}", member_url)
                index.setdefault(f"{entry.dotted_path}.{member}", member_url)
    return index


def resolve_crossrefs(
    md: str,
    *,
    current_url: str,
    index: dict[str, str] | None = None,
    degrade_unresolved: bool = True,
) -> tuple[str, list[str]]:
    """
    Rewrite bracket cross-refs in a markdown string.

    Returns the rewritten markdown and the list of cross-ref keys that could not
    be resolved. ``current_url`` is the clean URL of the page being rendered, used
    to make the links relative.

    ``degrade_unresolved`` controls what happens to a ref whose key isn't a known
    symbol: ``True`` (docstrings/prefaces, which we author) renders just the
    display text; ``False`` (whole content pages) leaves the original
    ``[text][key]`` untouched, so a bracket pair that is actually code - e.g.
    ``arr[i][j]`` - survives instead of being mangled into ``arri``.
    """
    idx = symbol_url_index() if index is None else index
    unresolved: list[str] = []

    def replace(match: re.Match[str]) -> str:
        text, key = match.group(1), match.group(2)
        lookup = key or _SYMBOL_CLEAN_RE.sub("", text).removesuffix("()")
        target = idx.get(lookup)
        if target is not None:
            return f"[{text}]({_relative_href(target, current_url)})"
        external = resolve_external_url(lookup)
        if external is not None:
            return f"[{text}]({external})"
        unresolved.append(lookup)
        return text if degrade_unresolved else match.group(0)

    return _CROSSREF_RE.sub(replace, md), unresolved


# Fenced code blocks (``` / ~~~). Cross-refs are never resolved inside these. We
# deliberately do NOT skip *inline* code, because a ref's display text legitimately
# contains it - ``[`Component.js`][Component.js]`` - and unresolved inline code like
# `` `arr[i][j]` `` is already safe (the keys aren't symbols, so it's left as-is).
_FENCED_CODE_RE = re.compile(r"(```.*?```|~~~.*?~~~)", re.DOTALL)


def resolve_crossrefs_in_prose(md: str, *, current_url: str) -> tuple[str, list[str]]:
    """
    Resolve cross-refs across a whole content page (the analog of the old
    mkdocstrings autorefs), skipping fenced code and leaving unresolved refs
    literal. Used by the render pipeline; docstrings/prefaces call
    ``resolve_crossrefs`` directly with their own degrade behavior.
    """
    parts = _FENCED_CODE_RE.split(md)
    unresolved: list[str] = []
    # re.split with one capture group -> [prose, fence, prose, fence, ...];
    # even indices are prose, odd indices are fenced code (left untouched).
    for i in range(0, len(parts), 2):
        resolved, missing = resolve_crossrefs(parts[i], current_url=current_url, degrade_unresolved=False)
        parts[i] = resolved
        unresolved.extend(missing)
    return "".join(parts), unresolved


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


def _inventory_candidates(canonical_path: str) -> Iterator[str]:
    """
    Public-path candidates for an inventory lookup, longest first.

    griffe yields module paths (``django.http.request.HttpRequest``) while Sphinx
    inventories key the public re-export (``django.http.HttpRequest``), so after
    the exact path we also try progressively dropping trailing module segments.
    """
    parts = canonical_path.split(".")
    if len(parts) < 2:
        yield canonical_path
        return
    leaf, mods = parts[-1], parts[:-1]
    for i in range(len(mods), 0, -1):
        yield ".".join([*mods[:i], leaf])


def resolve_external_url(canonical_path: str) -> str | None:
    """Resolve a dotted path against the external (stdlib + Django) inventory."""
    inventory = external_inventory()
    for candidate in _inventory_candidates(canonical_path):
        if candidate in inventory:
            return inventory[candidate]
    return None


def make_type_resolver(current_url: str) -> Callable[[str, str], str | None]:
    """
    Build a resolver for signature annotations (feature 4.21).

    Resolves a referenced type to a URL: project symbols first (by short name or
    dotted path, as a page-relative link), then the external inventory (absolute).
    Returns ``None`` when the type isn't documented anywhere, so it renders plain.
    """
    index = symbol_url_index()

    def resolve(name: str, canonical_path: str) -> str | None:
        target = index.get(name) or index.get(canonical_path)
        if target is not None:
            return _relative_href(target, current_url)
        return resolve_external_url(canonical_path)

    return resolve
