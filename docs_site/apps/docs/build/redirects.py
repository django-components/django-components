"""
Static redirect stubs for moved pages (Phase 5c, feature 5c.17).

Replaces the old `mkdocs-redirects` plugin: for every old URL that has moved, we
emit a tiny HTML page at the old path that sends visitors to the new one. The
stub uses three mechanisms together (defense in depth):

- `<meta http-equiv="refresh">` - works without JS (crawlers, a11y tools).
- `<script>location.replace()` - faster in browsers, and replaces (not pushes)
  history so the back button skips the dead URL.
- `<link rel="canonical">` + `<meta robots noindex>` - tells search engines the
  new URL is authoritative and keeps the stub itself out of the index.

The refresh/JS targets are *relative* hrefs (computed per stub) so they resolve
correctly under the GitHub Pages project base path; the canonical is absolute.
The JS target also carries the visitor's query string and `#anchor`, so a link to
a section of an old page lands on the same section of the new page.

Targets are validated at build time by guards/redirect_target.py (feature 5c.18).

There are two sets of stubs:

- `REDIRECTS`: pages that moved inside the new site. `emit_redirects` writes them
  into every build.
- The old `/latest/...` and `/dev/...` URLs, emitted by `emit_legacy_redirects`
  into the assembled deploy only (see `docs_assemble`). The earlier mike-based
  site served the current docs under those prefixes, and published READMEs and
  other sites still link to them.

Spec: DESIGN_spike_9.md section 2.5, DESIGN_spike_10.md section 3.12.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Old URL path -> new URL path. Ported from the old mkdocs-redirects config,
# remapped onto the `/docs/` URL taxonomy adopted during the migration, plus the
# old welcome page. Keys/values are clean URL paths (leading + trailing slash).
# `emit_legacy_redirects` applies these entries under `/latest/` and `/dev/` too.
REDIRECTS: dict[str, str] = {
    # The site root has no landing page of its own yet, so it forwards to the
    # docs welcome page, which acts as the landing page in the meantime.
    "/": "/docs/",
    "/README/": "/docs/",
    "/release_notes/": "/docs/releases/",
    "/concepts/fundamentals/defining_js_css_html_files/": "/docs/concepts/fundamentals/html_js_css_files/",
    "/overview/contributing/": "/docs/community/contributing/",
    "/overview/development/": "/docs/community/development/",
    # The old welcome page is the docs home page today.
    "/overview/welcome/": "/docs/",
}

# URL prefixes the earlier mike-based site served the current docs under. Published
# READMEs, PyPI pages and other sites still link to them.
LEGACY_PREFIXES = ("latest", "dev")

# Top-level folders that the old site never had pages for: the version snapshots,
# the build assets, and the redirect folders this code writes.
_NOT_LEGACY_PAGES = frozenset({"v", "static", "pagefind", *LEGACY_PREFIXES})

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting&hellip;</title>
<link rel="canonical" href="{canonical}">
<meta http-equiv="refresh" content="0; url={href}">
<meta name="robots" content="noindex,follow">
</head>
<body>
<p>This page has moved. <a href="{href}">Continue to the new page</a>.</p>
<script>window.location.replace({href_json} + window.location.search + window.location.hash);</script>
</body>
</html>
"""


def _write_stub(output_dir: Path, old: str, new: str, *, site_url: str) -> None:
    """Write the stub that sends `old` to `new` (both clean URL paths, leading + trailing slash)."""
    stub = output_dir / old.strip("/") / "index.html"
    stub.parent.mkdir(parents=True, exist_ok=True)
    # Relative href from the stub's dir to the target dir (base-path safe).
    target_dir = output_dir / new.strip("/")
    href = os.path.relpath(target_dir, stub.parent).replace(os.sep, "/") + "/"
    stub.write_text(
        _TEMPLATE.format(canonical=f"{site_url}{new}", href=href, href_json=json.dumps(href)),
        encoding="utf-8",
    )


def emit_redirects(output_dir: Path, *, site_url: str) -> int:
    """Write a redirect stub for every REDIRECTS entry into `output_dir`. Returns the count."""
    site_url = site_url.rstrip("/")
    for old, new in REDIRECTS.items():
        _write_stub(output_dir, old, new, site_url=site_url)
    return len(REDIRECTS)


def legacy_redirect_map(site_dir: Path) -> dict[str, str]:
    """
    Map each old page path (the part after `/latest/`) to the URL that serves it today.

    Both sides are clean URL paths with a leading and trailing slash, like `REDIRECTS`.
    The pages come from the built site itself, so every target exists. A page under
    `docs/` has the same path without that prefix (`/docs/concepts/x/` serves what
    `/latest/concepts/x/` served). A page that sits at the site root outside `docs/`
    (`examples/`, `plugins/`, `benchmarks/`) keeps its path. The `REDIRECTS` entries apply under
    the old prefix too, so a page that moved before the migration still resolves.
    """
    mapping: dict[str, str] = {}
    # Walk only the directories that can hold a page. The version snapshots under
    # `v/` are large and never map to an old `/latest/...` path, and the prefix
    # directories hold stubs from an earlier run.
    for top_dir in sorted(d for d in site_dir.iterdir() if d.is_dir() and d.name not in _NOT_LEGACY_PAGES):
        for page in sorted(top_dir.rglob("index.html")):
            new = f"/{page.parent.relative_to(site_dir).as_posix()}/"
            mapping[new.removeprefix("/docs") if top_dir.name == "docs" else new] = new
    # `emit_redirects` already wrote stubs at the root, and the loop above counts them
    # as pages. This update replaces their entries with the real targets.
    mapping.update(REDIRECTS)
    return mapping


def emit_legacy_redirects(site_dir: Path, *, site_url: str) -> int:
    """
    Write stubs for the old `/latest/...` and `/dev/...` URLs into the built `site_dir`.

    Each stub sends the visitor to the page that serves the same path today, so a
    link from a published README or another site keeps working. Returns the number
    of stubs written. Run it on the root site, after the pages are built.
    """
    site_url = site_url.rstrip("/")
    mapping = legacy_redirect_map(site_dir)
    for prefix in LEGACY_PREFIXES:
        for old, new in mapping.items():
            _write_stub(site_dir, f"/{prefix}{old}", new, site_url=site_url)
    return len(mapping) * len(LEGACY_PREFIXES)
