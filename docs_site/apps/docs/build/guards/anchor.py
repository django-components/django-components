"""
Anchor guard.

For every `<a href="...#fragment">`, the fragment must exist as an `id=` (or a
legacy `<a name=>`) on the target page. Same-page (`#foo`) links are checked
against the current page.

Severity is WARNING to match the current CI baseline (mkdocs
`validation.anchors: warn`): a broken anchor still loads the page, just at the
wrong scroll position. It fails the build under `--strict`.

Spec: docs_site/design/DESIGN_spike_10.md section 3.10 (feature 3b.13).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from .base import GuardResult

if TYPE_CHECKING:
    from apps.docs.build.site_index import PageRecord

    from .base import GuardContext


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    index = ctx.site_index
    if index is None:
        return

    for page in index.pages:
        for link in page.links:
            if not link.anchor:
                continue

            target_page: PageRecord | None
            if link.is_anchor_only:
                target_page = page
            elif link.is_external:
                continue
            else:
                resolved = index.resolve_link(page.rel_path, link.target)
                target_page = index.get_page(resolved)
                if target_page is None:
                    continue  # the internal_link guard owns the missing target

            if link.anchor not in target_page.anchors and link.anchor not in target_page.name_aliases:
                yield GuardResult.warning(
                    guard="anchor",
                    message=f"Broken anchor: {link.href!r} (no id={link.anchor!r} on target)",
                    source=page.label,
                )
