"""
Cross-version link guard (feature 5b.15).

Asserts that every relative ``<a href>`` in docs_site/versions/ resolves to a
real built page - both intra-version links and links that cross from one version
subtree into another. The §4.6 strategy persists every version to the repo, so a
``/v/0.151/.. -> /v/0.150/..`` link is just a filesystem path that must exist
(see main doc section 8).

Reuses the same SiteIndex parser + clean-URL resolver the internal_link guard
uses, pointed at the whole versions tree so cross-version links resolve against
one unified index. What's skipped is version-tree-specific:

- absolute (``/...``) links - they resolve against the deploy *site* root, not a
  single version subtree, so they can't be checked here;
- non-page assets (``.md`` companions, images) - mirrors internal_link, via an
  explicit suffix allowlist so clean-URL version dirs like ``0.150.0/`` (whose
  ".0" reads as an extension) are still checked.

External / anchor / mailto links are skipped via the shared ``LinkRef`` flags.
Runs only when ``ctx.versions_root`` is set. Spec: DESIGN_spike_10.md section
3.8; DESIGN_spike_7.md section 11.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from apps.docs.build.site_index import SiteIndex
from apps.docs.build.versioning import is_frozen_import

from .base import GuardResult

if TYPE_CHECKING:
    from .base import GuardContext

# Non-page targets to skip (raw markdown companions, images, other assets). An
# explicit allowlist - not "any non-.html suffix" - so links to clean-URL version
# dirs like `0.150.0/`, whose ".0" looks like an extension, are still checked.
_NON_PAGE_SUFFIXES = frozenset(
    {
        ".md",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".css",
        ".js",
        ".json",
        ".txt",
        ".xml",
        ".pdf",
        ".zip",
        ".woff",
        ".woff2",
        ".ttf",
    }
)


def _is_non_page_asset(target: str) -> bool:
    return PurePosixPath(target.rstrip("/")).suffix.lower() in _NON_PAGE_SUFFIXES


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    root = ctx.versions_root
    if root is None or not root.is_dir():
        return

    # One index over the whole tree: cross-version links resolve against it the
    # same way the browser resolves a relative href from a clean-URL page.
    index = SiteIndex(root)
    # Frozen gh-pages imports are historical HTML we never rebuild (old mkdocs
    # theme templates, era-specific structures, long-dead relative links). Their
    # internal links are whatever the old deploy shipped, so we don't link-check
    # them - only the versions we build ourselves. Cache the per-version verdict.
    frozen_verdict: dict[str, bool] = {}

    def _is_frozen(version: str) -> bool:
        if version not in frozen_verdict:
            frozen_verdict[version] = is_frozen_import(root / version)
        return frozen_verdict[version]

    for page in index.pages:
        parts = PurePosixPath(page.rel_path).parts
        if parts and _is_frozen(parts[0]):
            continue
        for link in page.links:
            if link.is_external or link.is_anchor_only or not link.target:
                continue
            if link.target.startswith("/") or _is_non_page_asset(link.target):
                continue
            if index.resolve_link(page.rel_path, link.target) is None:
                yield GuardResult.error(
                    guard="cross_version_link",
                    message=f"Broken link {link.href!r}: target not found on disk",
                    source=page.label,
                )
