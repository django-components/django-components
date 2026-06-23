"""
Internal-link guard.

Every `<a href>` that points inside the site must resolve to a built page.
External links, anchor-only links, and links to non-page files (assets like
`.png`/`.pdf`, handled by the asset guard) are skipped.

Spec: docs_site/design/DESIGN_spike_10.md section 3.9 (feature 3b.12).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from .base import GuardResult

if TYPE_CHECKING:
    from .base import GuardContext


def _looks_like_file(target: str) -> bool:
    """True if the target's last segment has a non-HTML file extension."""
    last = PurePosixPath(target.rstrip("/")).name
    suffix = PurePosixPath(last).suffix
    return bool(suffix) and suffix != ".html"


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    index = ctx.site_index
    if index is None:
        return

    for page in index.pages:
        for link in page.links:
            if link.is_external or link.is_anchor_only or not link.target:
                continue
            if index.resolve_link(page.rel_path, link.target) is not None:
                continue
            # Unresolved targets that look like asset files are the asset guard's
            # job; only flag links that look like pages.
            if _looks_like_file(link.target):
                continue
            yield GuardResult.error(
                guard="internal_link",
                message=f"Broken internal link: {link.href!r}",
                source=page.label,
            )
