"""
Image alt-text guard.

Every content `<img>` should carry non-empty alt text (screen readers, broken-
image fallback, AI consumers). Only DocPage content is checked.

Spec: docs_site/design/DESIGN_spike_12.md feature 2.A.9 (feature 3b.21).
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
        if not page.is_doc_page or page.is_redirect_stub:
            continue
        for img in page.images:
            if not img.alt:  # None (missing) or "" (empty)
                yield GuardResult.warning(
                    guard="alt_text",
                    message=f"Image missing alt text: {img.src!r}",
                    source=page.label,
                )
