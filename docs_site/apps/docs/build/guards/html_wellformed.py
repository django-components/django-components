"""
HTML well-formedness guard.

Reports pages that lxml couldn't parse strictly (recover=False) and pages with
duplicate `id=` values. A duplicate id silently breaks anchor navigation (the
browser jumps to the first match), so the anchor guard can pass while the link
still lands in the wrong place.

The SiteIndex already did the strict parse and the id counting; this guard just
reports what it collected.

Spec: docs_site/design/DESIGN_spike_10.md section 3.15 (feature 3b.16).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from .base import GuardResult

if TYPE_CHECKING:
    from .base import GuardContext


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    index = ctx.site_index
    if index is None:
        return

    for page in index.pages:
        if page.parse_error:
            yield GuardResult.error(
                guard="html_wellformed",
                message=f"HTML parse error: {page.parse_error}",
                source=page.label,
            )
        for dup in page.duplicate_ids:
            yield GuardResult.warning(
                guard="html_wellformed",
                message=f"Duplicate id={dup!r} on page",
                source=page.label,
            )
