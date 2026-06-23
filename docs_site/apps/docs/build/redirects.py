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

Targets are validated at build time by guards/redirect_target.py (feature 5c.18).

Spec: DESIGN_spike_9.md section 2.5, DESIGN_spike_10.md section 3.12.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Old URL path -> new URL path. Ported from the old mkdocs-redirects config (5
# entries), remapped onto the `/docs/` URL taxonomy adopted during the migration.
# Keys/values are clean URL paths (leading + trailing slash). The wholesale
# preservation of *every* pre-migration URL is a separate Phase-6 concern (6.1).
REDIRECTS: dict[str, str] = {
    "/README/": "/docs/",
    "/release_notes/": "/docs/releases/",
    "/concepts/fundamentals/defining_js_css_html_files/": "/docs/concepts/fundamentals/html_js_css_files/",
    "/overview/contributing/": "/docs/community/contributing/",
    "/overview/development/": "/docs/community/development/",
}

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
<script>window.location.replace({href_json});</script>
</body>
</html>
"""


def emit_redirects(output_dir: Path, *, site_url: str) -> int:
    """Write a redirect stub for every REDIRECTS entry into `output_dir`. Returns the count."""
    site_url = site_url.rstrip("/")
    for old, new in REDIRECTS.items():
        stub = output_dir / old.strip("/") / "index.html"
        stub.parent.mkdir(parents=True, exist_ok=True)
        # Relative href from the stub's dir to the target dir (base-path-safe).
        target_dir = output_dir / new.strip("/")
        href = os.path.relpath(target_dir, stub.parent).replace(os.sep, "/") + "/"
        stub.write_text(
            _TEMPLATE.format(canonical=f"{site_url}{new}", href=href, href_json=json.dumps(href)),
            encoding="utf-8",
        )
    return len(REDIRECTS)
