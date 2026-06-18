"""
Redirect target guard.

Every redirect stub (a `<meta http-equiv="refresh">` page, e.g. the moved-page
stubs from build/redirects.py) must point at a URL that actually resolves in the
built site - otherwise the redirect lands on a 404. Replaces mkdocs `--strict`'s
"redirect destination doesn't exist" check.

Spec: docs_site/design/DESIGN_spike_10.md section 3.12 (feature 5c.18).
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
        if not page.is_redirect_stub:
            continue
        target = (page.redirect_target or "").strip()
        if not target:
            yield GuardResult.error(
                guard="redirect_target",
                message="Redirect stub has no target URL",
                source=page.label,
            )
            continue
        # External / absolute redirects are out of scope (we don't emit them).
        if target.startswith(("http://", "https://", "//")):
            continue
        path, _, _ = target.partition("#")
        path, _, _ = path.partition("?")
        if index.resolve_link(page.rel_path, path) is None:
            yield GuardResult.error(
                guard="redirect_target",
                message=f"Redirect target does not resolve to a built page: {target!r}",
                source=page.label,
            )
