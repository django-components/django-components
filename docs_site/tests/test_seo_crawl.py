"""
Tests for the Phase 5c Chunk 2 crawl + index files (features 5c.1, 5c.2, 5c.11).

Covers the sitemap.xml, robots.txt, and meta/indexing.json emitters in
apps/docs/build/seo.py, driven by a SiteIndex over a small synthetic build.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from apps.docs.build import seo
from apps.docs.build.seo import (
    _disallowed_versions,
    _priority_for,
    write_indexing_manifest,
    write_robots,
    write_sitemap,
)
from apps.docs.build.site_index import SiteIndex
from django.conf import settings

DOC_META = '<meta name="generator" content="django-components docs builder">'
GEN_AT = datetime(2026, 6, 1, tzinfo=timezone.utc)


def write_page(build: Path, rel: str, *, robots: str = "index,follow", canonical: str = "", doc: bool = True) -> None:
    head = DOC_META if doc else ""
    if robots:
        head += f'<meta name="robots" content="{robots}">'
    if canonical:
        head += f'<link rel="canonical" href="{canonical}">'
    html = f"<!DOCTYPE html><html><head>{head}</head><body><h1>x</h1></body></html>"
    path = build / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _site(build: Path) -> SiteIndex:
    write_page(build, "index.html")
    write_page(build, "docs/getting_started/index.html")
    write_page(build, "docs/community/contributing/index.html")
    write_page(build, "404.html", robots="noindex,follow")  # excluded from sitemap
    return SiteIndex(build)


# -- sitemap (5c.1) ------------------------------------------------------------


def test_sitemap_lists_indexable_root_urls(tmp_path: Path) -> None:
    count = write_sitemap(_site(tmp_path), tmp_path, site_url="https://ex.com/base")
    xml = (tmp_path / "sitemap.xml").read_text()
    # noindex 404 is excluded; the other three are present as root (latest) URLs
    assert count == 3
    assert "<loc>https://ex.com/base/</loc>" in xml
    assert "<loc>https://ex.com/base/docs/getting_started/</loc>" in xml
    assert "https://ex.com/base/404/" not in xml
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')


def test_sitemap_priorities_by_section() -> None:
    assert _priority_for("/") == 1.0
    assert _priority_for("/docs/getting_started/install/") == 0.8
    assert _priority_for("/docs/concepts/foo/") == 0.6
    assert _priority_for("/docs/community/contributing/") == 0.4
    assert _priority_for("/something/else/") == 0.5


# -- indexing.json (5c.11) -----------------------------------------------------


def test_indexing_manifest_includes_all_doc_pages_with_robots(tmp_path: Path) -> None:
    count = write_indexing_manifest(
        _site(tmp_path), tmp_path, version="9.9.9", generated_at=GEN_AT, site_url="https://ex.com/base"
    )
    data = json.loads((tmp_path / "meta" / "indexing.json").read_text())
    assert count == 4  # noindex pages ARE listed (with their robots), unlike the sitemap
    assert data["version"] == "9.9.9"
    assert data["generated_at"] == "2026-06-01"
    by_url = {p["url"]: p for p in data["pages"]}
    assert by_url["https://ex.com/base/404/"]["robots"] == "noindex,follow"
    assert by_url["https://ex.com/base/"]["robots"] == "index,follow"


def test_indexing_manifest_uses_declared_canonical(tmp_path: Path) -> None:
    write_page(tmp_path, "docs/foo/index.html", canonical="https://ex.com/base/v/9.9.9/docs/foo/")
    write_indexing_manifest(
        SiteIndex(tmp_path), tmp_path, version="9.9.9", generated_at=GEN_AT, site_url="https://ex.com/base"
    )
    data = json.loads((tmp_path / "meta" / "indexing.json").read_text())
    entry = next(p for p in data["pages"] if p["url"].endswith("/docs/foo/"))
    assert entry["canonical"] == "https://ex.com/base/v/9.9.9/docs/foo/"


# -- robots.txt (5c.2) ---------------------------------------------------------


def test_robots_has_ai_bots_and_sitemap_no_versions(tmp_path: Path) -> None:
    # No manifest -> no version disallows (the pre-cutover state)
    n = write_robots(tmp_path, site_url="https://ex.com/base", versions_root=tmp_path / "nope")
    txt = (tmp_path / "robots.txt").read_text()
    assert n == 0
    assert "User-agent: *\nAllow: /\n" in txt
    assert "Sitemap: https://ex.com/base/sitemap.xml" in txt
    for bot in seo.AI_BOTS:
        assert f"User-agent: {bot}" in txt
    assert "Disallow: /v/" not in txt


def _write_manifest(root: Path, entries: list[tuple[str, list[str]]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    data = [{"version": v, "title": v, "aliases": aliases} for v, aliases in entries]
    (root / "versions.json").write_text(json.dumps(data), encoding="utf-8")


def test_disallowed_versions_keeps_two_newest_plus_latest(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        [("0.4.0", ["latest"]), ("0.3.0", []), ("0.2.0", []), ("0.1.0", [])],
    )
    # newest two (0.4.0, 0.3.0) stay; latest already points at 0.4.0
    assert _disallowed_versions(tmp_path) == ["0.2.0", "0.1.0"]


def test_robots_emits_version_disallows(tmp_path: Path) -> None:
    versions_root = tmp_path / "versions"
    _write_manifest(versions_root, [("0.4.0", ["latest"]), ("0.3.0", []), ("0.2.0", []), ("0.1.0", [])])
    n = write_robots(tmp_path, site_url="https://ex.com/base", versions_root=versions_root)
    txt = (tmp_path / "robots.txt").read_text()
    assert n == 2
    assert "Disallow: /v/0.2.0/" in txt
    assert "Disallow: /v/0.1.0/" in txt
    assert "Disallow: /v/0.4.0/" not in txt


def test_site_url_setting_present() -> None:
    # Guards against accidental SITE_URL removal that would break absolute loc/Sitemap
    assert str(settings.SITE_URL).startswith("http")
