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
That guard sees the `REDIRECTS` stubs, which every build writes. The other two sets
exist only in the assembled deploy, which no guard reads. They are built from files
that exist, and the tests check that every target resolves.

A "stub" and a "redirect page" are the same thing in this module.

There are three sets of stubs:

- `REDIRECTS`: pages that moved inside the new site. `emit_redirects` writes them
  into every build.
- The old `/latest/...` and `/dev/...` URLs, emitted by `emit_legacy_redirects`
  into the assembled deploy only (see `docs_assemble`). The earlier mike-based
  site served the current docs under those prefixes, and published READMEs and
  other sites still link to them.
- The old version-pinned URLs `/<version>/...`, emitted by `emit_version_redirects`
  into the assembled deploy only. The earlier site served each release at
  `/<version>/`, and changelogs and other sites still link to those pages.

Spec: DESIGN_spike_9.md section 2.5, DESIGN_spike_10.md section 3.12.
"""

from __future__ import annotations

import html
import json
import os
import re
from typing import TYPE_CHECKING
from urllib.parse import quote

from apps.docs.build.versioning import load_manifest

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

# Folder names of the releases in the earlier mike-based site: `0.148.0`, `0.124`.
# Only a manifest entry with a name like this gets redirect pages, so an entry such
# as `dev` or `docs` can never write into the site's own folders. `[0-9]` keeps
# non-ASCII digits out of a folder name.
VERSION_FOLDER = re.compile(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?")

# Where an old page goes when the version it names is not on the site, and the
# current docs have no page at the same path.
_FALLBACK = "/docs/"

# Top-level folders that the old site never had pages for: the version snapshots,
# the build assets, and the redirect folders this code writes (the `/<version>/`
# folders are skipped by name in `legacy_redirect_map`).
_NOT_LEGACY_PAGES = frozenset({"v", "static", "pagefind", *LEGACY_PREFIXES})

_MOVED = "This page has moved."

# A page with this title was written by `_write_stub` (see `_is_stub`). Keep it equal
# to the `<title>` in `_TEMPLATE`, or a second run would skip every stub it wrote.
_STUB_MARKER = "<title>Redirecting&hellip;</title>"

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
<p>{message} <a href="{href}">Continue to the new page</a>.</p>
<script>window.location.replace({href_json} + window.location.search + window.location.hash);</script>
</body>
</html>
"""


def _write_stub(output_dir: Path, old: str, new: str, *, site_url: str, message: str = _MOVED) -> None:
    """
    Write the stub that sends `old` to `new` (both clean URL paths, leading + trailing slash).

    `message` is the sentence shown above the link, which a visitor sees only if the
    redirect is slow or blocked.
    """
    stub = output_dir / old.strip("/") / "index.html"
    stub.parent.mkdir(parents=True, exist_ok=True)
    # Relative href from the stub's dir to the target dir (base-path safe).
    target_dir = output_dir / new.strip("/")
    href = os.path.relpath(target_dir, stub.parent).replace(os.sep, "/") + "/"
    # Percent-encode the path so a folder name with a quote or a `<` cannot end the
    # attribute or the script string, and a `#` stays part of the path. The result has
    # only letters, digits and `/.-_~%`, so it needs no more escaping.
    href = quote(href, safe="/")
    stub.write_text(
        _TEMPLATE.format(
            canonical=f"{site_url}{quote(new, safe='/')}",
            href=href,
            href_json=json.dumps(href),
            message=html.escape(message),
        ),
        encoding="utf-8",
    )


def _is_stub(page: Path) -> bool:
    """True if `page` is a redirect page written by `_write_stub`, so it is safe to replace."""
    return _STUB_MARKER in page.read_text(encoding="utf-8", errors="replace")


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
    # directories and the `/<version>/` folders hold stubs from an earlier run.
    for top_dir in sorted(
        d
        for d in site_dir.iterdir()
        if d.is_dir() and d.name not in _NOT_LEGACY_PAGES and not VERSION_FOLDER.fullmatch(d.name)
    ):
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


def emit_version_redirects(site_dir: Path, versions_root: Path, *, site_url: str) -> int:
    """
    Write stubs for the old `/<version>/...` URLs into the built `site_dir`.

    The earlier site served each release at `/<version>/`, and changelogs and other
    sites still link to those pages. Each page of each release in the committed
    `versions_root` gets a stub at its old path:

    - A release that `docs_assemble` mounted under `/v/<version>/` sends the visitor
      to the same page there. The pages are read from the mounted copy, so every
      target exists.
    - A release that is committed but not mounted (the deploy publishes only the
      newest `window` releases, set in `docs_versions.toml`) sends the visitor to the
      page that `/latest/<path>/` goes to, or to `/docs/` when there is none. The
      stub says so.

    "Mounted" means copied under `site_dir/v/<version>/` by `docs_assemble`. A manifest
    entry whose name is not a version number is skipped. When `site_dir` has no
    `/docs/` page, a release that is not mounted gets no stubs.

    A page that already exists at a stub's address and is not a redirect page is left
    alone. Run it after `docs_assemble` has built the current docs into `site_dir` and
    copied the version snapshots under `site_dir/v/`. Returns the number of stubs
    written.
    """
    site_url = site_url.rstrip("/")
    # The page that serves each old path in the current docs. A release that is not
    # mounted sends its pages there.
    current = legacy_redirect_map(site_dir)
    # Without the docs home page there is no fallback, and those pages get no stub
    # rather than one that leads to a 404.
    has_fallback = (site_dir / _FALLBACK.strip("/") / "index.html").is_file()
    written = 0
    for info in load_manifest(versions_root):
        version = str(info.version)
        if not VERSION_FOLDER.fullmatch(version):
            continue
        mounted = (site_dir / "v" / version).is_dir()
        if not mounted and not has_fallback:
            continue
        source = site_dir / "v" / version if mounted else versions_root / version
        not_hosted = f"Version {version} of the docs is no longer hosted"
        for page in sorted(source.rglob("index.html")):
            rel = page.parent.relative_to(source).as_posix()
            tail = "" if rel == "." else f"{rel}/"
            old = f"/{version}/{tail}"
            if mounted:
                new = f"/v/{version}/{tail}"
                message = _MOVED
            elif f"/{tail}" in current:
                new = current[f"/{tail}"]
                message = f"{not_hosted}, so this link goes to the same page in the current docs."
            else:
                new = _FALLBACK
                message = f"{not_hosted}, and the current docs have no matching page, so this link goes to the docs home page."
            stub = site_dir / old.strip("/") / "index.html"
            # A page that is not one of our stubs is a real page. It keeps its path.
            if stub.is_file() and not _is_stub(stub):
                continue
            _write_stub(site_dir, old, new, site_url=site_url, message=message)
            written += 1
    return written
