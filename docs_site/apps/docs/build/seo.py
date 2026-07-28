"""
Post-build SEO crawl + index files: sitemap.xml, robots.txt, meta/indexing.json.

All three are root-level artifacts emitted after the page build. They share one
enumeration of the built site (a single SiteIndex pass) and one notion of which
versions are current (the versions.json manifest), so the "which pages /
versions count" logic lives here once.

Scope: these target the *assembled, deployed* site, whose root is the current
("latest") version with older versions mounted under /v/<version>/. The current
docs-build to ./site/ already IS that current-version build (preview mode), so
they're generated there. Wiring them into the full multi-version assembly
(copying versions/* alongside) is Phase 6 (feature 6.4).

Canonical note: the current-version build canonicals to the root (latest) URL
(feature 6.12 part a), so for it sitemap `loc`, indexing.json `url`, and each
page's declared `canonical` agree. Old `/v/<version>/` snapshots still self-canonical; mapping
those to their /latest/ counterpart (+ noindex if absent from latest) is 6.12
part b (Phase 6, needs the multi-version manifest).

Specs:
- sitemap:  docs_site/design/DESIGN_spike_12.md section 2.A.2 (feature 5c.1)
- robots:   docs_site/design/DESIGN_spike_12.md section 2.A.3 (feature 5c.2)
- indexing: docs_site/design/DESIGN_spike_12.md section 4.C.5 (feature 5c.11)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from django.conf import settings

from apps.docs.build.git_metadata import get_page_git_meta
from apps.docs.build.paths import url_to_md
from apps.docs.build.site_index import SiteIndex
from apps.docs.build.versioning import load_manifest

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from apps.docs.build.site_index import PageRecord

# AI crawlers we explicitly allow (default-allow stance, see the AI bot policy
# page). Listed individually so the policy is visible and auditable in robots.txt.
AI_BOTS = (
    "GPTBot",
    "ClaudeBot",
    "anthropic-ai",
    "Google-Extended",
    "PerplexityBot",
    "CCBot",
)

# How many of the newest release versions stay crawlable. Older /v/<version>/
# dirs are disallowed (they're noindex'd too). Matches the per-version-noindex
# rule of keeping the current version plus one prior.
KEEP_RECENT_VERSIONS = 2

# Per-section sitemap <priority>. Google ignores it, but Bing/Yandex still read
# it. Keyed by the URL path prefix (after the leading slash).
_PRIORITY_RULES = (
    ("docs/getting_started", 0.8),
    ("docs/concepts", 0.6),
    ("docs/reference", 0.6),
    ("docs/guides", 0.6),
    ("docs/overview", 0.6),
    ("docs/community", 0.4),
    ("releases", 0.4),
)


@dataclass
class SeoOutcome:
    sitemap_urls: int
    indexed_pages: int
    disallowed_versions: int


def generate_seo_files(
    output_dir: Path,
    *,
    version: str,
    generated_at: datetime,
    versions_root: Path | None = None,
) -> SeoOutcome:
    """
    Write sitemap.xml, robots.txt, and meta/indexing.json into a built site.

    `versions_root` defaults to the committed versions tree; its versions.json
    drives the robots.txt old-version disallow list (no manifest -> no
    disallows, which is the pre-cutover state).
    """
    site_url = str(settings.SITE_URL).rstrip("/")
    index = SiteIndex(output_dir)

    sitemap_urls = write_sitemap(index, output_dir, site_url=site_url)
    indexed = write_indexing_manifest(index, output_dir, version=version, generated_at=generated_at, site_url=site_url)
    disallowed = write_robots(
        output_dir,
        site_url=site_url,
        versions_root=versions_root if versions_root is not None else settings.VERSIONS_DIR,
    )
    return SeoOutcome(sitemap_urls=sitemap_urls, indexed_pages=indexed, disallowed_versions=disallowed)


def _indexable_pages(index: SiteIndex) -> list[PageRecord]:
    """Doc pages that should appear in the sitemap: built, not a redirect, not noindex."""
    return [p for p in index.pages if p.is_doc_page and not p.is_redirect_stub and "noindex" not in p.robots.lower()]


def _loc_for(page: PageRecord, site_url: str) -> str:
    """Absolute deployed URL (root = latest version) for a built page."""
    return f"{site_url}{page.url}"


def _priority_for(url: str) -> float:
    """Sitemap <priority> for a page URL. Home is 1.0; sections per _PRIORITY_RULES."""
    path = url.strip("/")
    if not path:
        return 1.0
    for prefix, priority in _PRIORITY_RULES:
        if path == prefix or path.startswith(prefix + "/"):
            return priority
    return 0.5


def write_sitemap(index: SiteIndex, output_dir: Path, *, site_url: str) -> int:
    """Write sitemap.xml listing indexable latest-version URLs. Returns the URL count."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    pages = sorted(_indexable_pages(index), key=lambda p: p.url)
    for page in pages:
        loc = _loc_for(page, site_url)
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(loc)}</loc>")
        lastmod = _git_lastmod(page)
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <priority>{_priority_for(page.url):.1f}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (output_dir / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(pages)


def _git_lastmod(page: PageRecord) -> str:
    """ISO-8601 date of the page source's last commit, or "" if it has no source/history."""
    md_path = url_to_md(settings.CONTENT_DIR, page.url)
    if md_path is None:
        return ""  # generated page (reference/releases) has no single source file
    meta = get_page_git_meta(settings.REPO_ROOT, md_path)
    return meta.last_updated.date().isoformat() if meta.last_updated else ""


def write_indexing_manifest(
    index: SiteIndex,
    output_dir: Path,
    *,
    version: str,
    generated_at: datetime,
    site_url: str,
) -> int:
    """Write meta/indexing.json (url + canonical + robots per page). Returns the page count."""
    pages = []
    for page in sorted(index.pages, key=lambda p: p.url):
        if not page.is_doc_page or page.is_redirect_stub:
            continue
        loc = _loc_for(page, site_url)
        pages.append(
            {
                "url": loc,
                "canonical": page.canonical or loc,
                "robots": page.robots or "index,follow",
            }
        )
    data = {
        "generated_at": generated_at.date().isoformat(),
        "version": version,
        "pages": pages,
    }
    meta_dir = output_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "indexing.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return len(pages)


def _disallowed_versions(versions_root: Path) -> list[str]:
    """
    Versions whose /v/<version>/ dir should be disallowed: every version except
    the KEEP_RECENT_VERSIONS newest releases and whatever "latest" points at.
    """
    manifest = load_manifest(versions_root)
    ordered = [str(info.version) for info in manifest]  # newest-first (vendored Versions.__iter__)
    if not ordered:
        return []

    keep = set(ordered[:KEEP_RECENT_VERSIONS])
    latest = manifest.find("latest")
    if latest:
        keep.add(str(latest[0]))
    return [v for v in ordered if v not in keep]


def write_robots(output_dir: Path, *, site_url: str, versions_root: Path) -> int:
    """Write robots.txt (allow-all + old-version disallows + AI bots + sitemap). Returns disallow count."""
    disallowed = _disallowed_versions(versions_root)

    lines = ["User-agent: *", "Allow: /"]
    lines += [f"Disallow: /v/{v}/" for v in disallowed]
    lines.append("")
    lines.append(f"Sitemap: {site_url}/sitemap.xml")
    lines.append("")
    lines.append("# AI crawlers - explicit allow (see /docs/community/ai_bot_policy/)")
    for bot in AI_BOTS:
        lines.append(f"User-agent: {bot}")
        lines.append("Allow: /")
    (output_dir / "robots.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(disallowed)
