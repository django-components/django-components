"""
Legacy-anchor coverage guard (feature 4.64).

Every reference entry carries two anchors: the new short ``canonical_anchor``
(``AlreadyRegistered``) and the ``legacy_anchor`` the old mkdocs site used
(``django_components.AlreadyRegistered``). The canonical anchor is linked by the
page's own table of contents, so a missing one is already caught by the `anchor`
guard. The legacy anchor is different: it exists ONLY so inbound links from the
old site keep working - nothing on our own site points at it - so no other guard
would notice if a renderer stopped emitting it.

This guard closes that gap. For every *renamed* symbol (one whose legacy anchor
differs from its canonical anchor), the built page must still expose the legacy
anchor id, or old bookmarks and search-result links silently land at the top of
the page instead of the symbol.

Severity is WARNING (a stale inbound link still loads the right page, just at the
wrong scroll position); it fails the build under ``--strict``.

Post-build: reads the rendered anchor ids from the SiteIndex.

Spec: docs_site/design/DESIGN_features.md row 4.64.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from apps.docs.reference.discovery.registry import discover_pages

from .base import GuardResult

if TYPE_CHECKING:
    from .base import GuardContext


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    index = ctx.site_index
    if index is None:
        return

    # Clean-URL -> built page, e.g. "/docs/reference/exceptions/" -> PageRecord.
    by_url = {page.url: page for page in index.pages}

    for page in discover_pages():
        record = by_url.get(f"/docs/reference/{page.slug}/")
        if record is None:
            continue  # a missing generated page is the nav / internal_link guard's concern
        present = record.anchors | record.name_aliases
        for entry in page.entries:
            # Only renamed symbols need an alias. When the legacy and canonical
            # anchors are identical there is no old anchor to preserve.
            if entry.legacy_anchor == entry.canonical_anchor:
                continue
            if entry.legacy_anchor not in present:
                yield GuardResult.warning(
                    guard="anchor_alias",
                    message=(
                        f"Renamed symbol {entry.dotted_path!r} is missing its legacy anchor "
                        f"id={entry.legacy_anchor!r}; inbound links from the old site would break."
                    ),
                    source=f"docs/reference/{page.slug}",
                )
