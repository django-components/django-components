"""
Legacy-anchor deprecation guard (Phase 5c, feature 5c.12).

The API anchor migration (DESIGN_features.md 4.58 / spike §7.2) replaced the old
dotted-path anchors (`#django_components.Component`) with short ones
(`#Component`), and the reference pages emit the dotted form as a *legacy alias*
so old inbound links keep resolving. Those aliases are temporary: once search
indexes have refreshed, they should be removed.

This guard is the enforcement half of that deprecation. After a configurable
date (`settings.ANCHOR_ALIAS_DEPRECATION_DATE`, set to cutover + 12 months at
cutover), it flags any *content source* still linking via the long-form anchor,
so our own pages get migrated to the short cross-ref before the aliases are
deleted. Until the date is set (or reached) it's a no-op - the aliases are still
valid, so existing usage is tolerated.

Deliberately NOT done here: auto-expiring the emitted aliases on the date.
Removing inbound-link-preserving aliases is a one-way breaking change, so it
stays a deliberate manual step (taken once this guard is green at the date),
not an automatic time bomb that would silently break old links + the
`anchor_alias` guard the moment the clock ticks over.

Spec: docs_site/design/DESIGN_spike_12.md section 2.A.13.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from django.conf import settings

from .base import GuardResult
from .fence_validator import _source_files

if TYPE_CHECKING:
    from .base import GuardContext

# A link fragment (`#django_components.X`) or reference-style key
# (`][django_components.X]`) using the deprecated dotted-path anchor scheme.
_LONG_FORM = re.compile(r"(?:#|\]\[)django_components\.\w")
# Inline code spans - a `` `[X][django_components.X]` `` literal in the docstring
# guide is documentation OF the form, not a use of it, so it's stripped first.
_INLINE_CODE = re.compile(r"`[^`]*`")
# Opening/closing fence marker (``` or ~~~, 3+).
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def _today() -> date:
    return datetime.now(tz=timezone.utc).date()


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    deprecation = getattr(settings, "ANCHOR_ALIAS_DEPRECATION_DATE", None)
    # Dormant until a date is configured and reached: aliases are still live, so
    # long-form usage is fine.
    if deprecation is None or _today() < deprecation:
        return

    for label, text in _source_files(ctx):
        yield from _scan(label, text)


def _scan(label: str, text: str) -> Iterator[GuardResult]:
    in_fence = False
    marker = ""
    for lineno, line in enumerate(text.splitlines(), start=1):
        fence = _FENCE.match(line)
        if fence:
            token = fence.group(1)
            if not in_fence:
                in_fence, marker = True, token[0] * len(token)
            elif line.strip().startswith(marker):
                in_fence = False
            continue
        if in_fence:
            continue
        # Strip inline code before matching so documented-form literals don't trip it.
        if _LONG_FORM.search(_INLINE_CODE.sub("", line)):
            yield GuardResult.warning(
                guard="anchor_deprecation",
                message=(
                    "Source uses a deprecated long-form 'django_components.X' anchor; migrate to the short "
                    "cross-ref before the legacy aliases are removed"
                ),
                source=label,
                line=lineno,
            )
