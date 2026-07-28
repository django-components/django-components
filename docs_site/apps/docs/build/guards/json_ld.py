"""
JSON-LD validity guard.

Every `<script type="application/ld+json">` block we emit (BreadcrumbList on
every page, TechArticle on content pages) must be well-formed JSON and carry the
fields search engines need for rich results. Malformed JSON-LD silently drops a
page out of rich-result eligibility, so a broken block is an ERROR; a missing
recommended field is a WARNING.

This validates structure (parses, `@context`/`@type` present, per-type required
keys) without pulling in a full schema.org validator dependency.

Spec: docs_site/design/DESIGN_spike_12.md feature 2.A.7 (feature 5c.9).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from .base import GuardResult

if TYPE_CHECKING:
    from .base import GuardContext

# Required keys per @type. Absence is a WARNING (the block still parses, but the
# rich result is weaker or ineligible).
REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "BreadcrumbList": ("itemListElement",),
    "TechArticle": ("headline",),
}


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    index = ctx.site_index
    if index is None:
        return

    for page in index.pages:
        if not page.is_doc_page or page.is_redirect_stub:
            continue
        for block in page.jsonld_blocks:
            yield from _check_block(block, source=page.label)


def _check_block(block: str, *, source: str) -> Iterator[GuardResult]:
    try:
        data = json.loads(block)
    except (json.JSONDecodeError, ValueError) as e:
        yield GuardResult.error(
            guard="json_ld",
            message=f"Malformed JSON-LD block: {e}",
            source=source,
        )
        return

    if not isinstance(data, dict):
        yield GuardResult.error(
            guard="json_ld",
            message=f"JSON-LD block is not an object (got {type(data).__name__})",
            source=source,
        )
        return

    if data.get("@context") != "https://schema.org":
        yield GuardResult.warning(
            guard="json_ld",
            message=f"JSON-LD @context is not https://schema.org (got {data.get('@context')!r})",
            source=source,
        )

    type_name = data.get("@type")
    if not type_name:
        yield GuardResult.error(
            guard="json_ld",
            message="JSON-LD block is missing @type",
            source=source,
        )
        return

    yield from _check_required_keys(data, type_name, source=source)


def _check_required_keys(data: dict[str, Any], type_name: str, *, source: str) -> Iterator[GuardResult]:
    for key in REQUIRED_KEYS.get(type_name, ()):
        if not data.get(key):
            yield GuardResult.warning(
                guard="json_ld",
                message=f"{type_name} JSON-LD is missing recommended field {key!r}",
                source=source,
            )
