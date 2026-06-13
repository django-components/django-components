"""
Image / asset guard.

Local `<img src>`, `<script src>`, and `<link href>` references must resolve to
a real file. `/static/...` paths resolve against the source static dir (which
is copied verbatim into the deployed site); other local paths resolve against
the build output.

Spec: docs_site/design/DESIGN_spike_10.md section 3.12 (feature 3b.14).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from django.contrib.staticfiles import finders

from .base import GuardResult

if TYPE_CHECKING:
    from pathlib import Path

    from .base import GuardContext

_STATIC_PREFIX = "/static/"


def _static_asset_exists(rel: str, static_dir: Path) -> bool:
    """Resolve a /static/ path the way collectstatic will at deploy time."""
    # Django's finders see every app's static dir (e.g. the django_components
    # package's own JS), which a bare docs_site/static check would miss.
    if finders.find(rel) is not None:
        return True
    return (static_dir / rel).is_file()


def _asset_exists(src: str, build_dir: Path, static_dir: Path, page_dir: Path) -> bool:
    path, _, _ = src.partition("#")
    path, _, _ = path.partition("?")
    if not path:
        return True
    if path.startswith(_STATIC_PREFIX):
        return _static_asset_exists(path[len(_STATIC_PREFIX) :], static_dir)
    if path.startswith("/"):
        rel = path.lstrip("/")
        return (build_dir / rel).is_file() or (build_dir / rel / "index.html").is_file()
    # Relative asset path: resolve the way a browser does - against the page's
    # output directory (pages are directory URLs, so that's the page's own dir)
    return (page_dir / path).resolve().is_file()


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    index = ctx.site_index
    if index is None:
        return

    seen: set[str] = set()  # dedupe identical broken assets across pages
    for page in index.pages:
        # Only check docs-owned assets. Example demo pages / fragments reference
        # runtime-injected package static (e.g. django_components.min.js) that
        # isn't part of the docs static tree.
        if not page.is_doc_page:
            continue
        page_dir = (index.build_dir / page.label).parent
        for asset in page.assets:
            if asset.is_external or not asset.src:
                continue
            if _asset_exists(asset.src, index.build_dir, ctx.static_dir, page_dir):
                continue
            key = asset.src
            if key in seen:
                continue
            seen.add(key)
            yield GuardResult.error(
                guard="asset",
                message=f"Broken {asset.tag} asset: {asset.src!r}",
                source=page.label,
            )
