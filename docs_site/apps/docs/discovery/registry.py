"""
The discovery registry: the single list of reference pages.

``discover_pages()`` calls each per-page generator and returns the full set of
``ReferencePage`` objects. ``entry_index()`` flattens them to a lookup keyed by
both the public dotted path and the short display name, which the
``{% docstring %}`` tag and the cross-ref resolver consult.

Pages are added here as their discovery generators land (Chunk A ships only the
exceptions page).
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from apps.docs.discovery.pages import exceptions

if TYPE_CHECKING:
    from apps.docs.discovery.kinds import ReferenceEntry, ReferencePage


@lru_cache(maxsize=1)
def discover_pages() -> tuple[ReferencePage, ...]:
    """Every reference page, in nav order."""
    return (exceptions.discover(),)


@lru_cache(maxsize=1)
def entry_index() -> dict[str, ReferenceEntry]:
    """
    Map a symbol reference to its ``ReferenceEntry``.

    Keyed by both the public dotted path (``django_components.AlreadyRegistered``)
    and the short display name (``AlreadyRegistered``) so both the
    ``{% docstring %}`` tag (dotted path) and docstring cross-refs (short keys,
    per the codemod convention) can find an entry.
    """
    index: dict[str, ReferenceEntry] = {}
    for page in discover_pages():
        for entry in page.entries:
            index[entry.dotted_path] = entry
            index.setdefault(entry.display_name, entry)
    return index


def page_for_entry(entry: ReferenceEntry) -> ReferencePage | None:
    """The page an entry belongs to (for building cross-page URLs)."""
    for page in discover_pages():
        if entry in page.entries:
            return page
    return None
