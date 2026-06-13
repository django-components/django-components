"""
Structured-headings guard.

Heading levels should not jump by more than one when descending (e.g. an `##`
followed directly by `####` skips `###`). Skips break the document outline that
screen readers and the `.md` companion rely on. Only DocPage content is checked.

Spec: docs_site/design/DESIGN_spike_12.md feature 3.B.3 (feature 3b.22).
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
        # Release pages are generated verbatim from CHANGELOG.md, whose
        # historical sections legitimately jump levels (## version -> #### Feat).
        # That formatting is frozen history, so flagging it is pure noise.
        if page.label.startswith("docs/releases/"):
            continue
        prev_level = 0
        for heading in page.headings:
            if prev_level and heading.level > prev_level + 1:
                label = heading.text or heading.id or "(untitled)"
                yield GuardResult.warning(
                    guard="headings",
                    message=f"Heading level jumps from h{prev_level} to h{heading.level}: {label!r}",
                    source=page.label,
                )
            prev_level = heading.level
