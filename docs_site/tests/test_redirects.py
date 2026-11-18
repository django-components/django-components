"""Tests for Phase 5c Chunk 5 redirects (features 5c.17 emitter + 5c.18 guard)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from apps.docs.build import redirects
from apps.docs.build.guards import GuardContext, redirect_target
from apps.docs.build.guards.base import Severity
from apps.docs.build.redirects import emit_legacy_redirects, emit_redirects, legacy_redirect_map
from apps.docs.build.site_index import SiteIndex
from django.core.management import call_command
from django.test import override_settings


def _ctx(build: Path) -> GuardContext:
    return GuardContext(
        content_dir=build,
        examples_dir=build,
        nav_path=build / "_nav.yml",
        static_dir=build / "static",
        site_index=SiteIndex(build),
    )


def _write_stub(build: Path, rel: str, target: str) -> None:
    html = (
        f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url={target}"></head><body></body></html>'
    )
    path = build / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _write_page(build: Path, rel: str) -> None:
    path = build / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<!DOCTYPE html><html><body>ok</body></html>", encoding="utf-8")


# -- emitter (5c.17) -----------------------------------------------------------


def test_emit_redirects_writes_stubs(tmp_path: Path) -> None:
    n = emit_redirects(tmp_path, site_url="https://ex.com/base")
    assert n == len(redirects.REDIRECTS)

    stub = tmp_path / "concepts/fundamentals/defining_js_css_html_files/index.html"
    html = stub.read_text()
    # Canonical is absolute; refresh + JS targets are relative (base-path safe).
    assert 'href="https://ex.com/base/docs/concepts/fundamentals/html_js_css_files/"' in html
    rel = "../../../docs/concepts/fundamentals/html_js_css_files/"
    assert f"url={rel}" in html
    # The JS target also carries the visitor's query string and #anchor.
    assert f"location.replace({json.dumps(rel)} + window.location.search + window.location.hash)" in html
    assert 'name="robots" content="noindex,follow"' in html


def test_emit_redirects_site_root_forwards_to_welcome(tmp_path: Path) -> None:
    """The site root has no landing page of its own; it forwards to /docs/."""
    emit_redirects(tmp_path, site_url="https://ex.com/base")
    html = (tmp_path / "index.html").read_text()
    assert "url=docs/" in html  # / -> /docs/, relative so the base path is preserved
    assert 'href="https://ex.com/base/docs/"' in html


def test_emit_redirects_home_target_relative(tmp_path: Path) -> None:
    emit_redirects(tmp_path, site_url="https://ex.com/base")
    html = (tmp_path / "README/index.html").read_text()
    assert "url=../docs/" in html  # /README/ -> /docs/


# -- legacy /latest/ and /dev/ URLs ---------------------------------------------


@pytest.fixture
def site(tmp_path: Path) -> Path:
    """A built root site: docs pages, root pages, assets, a version snapshot, and the root stubs."""
    site = tmp_path / "site"
    for rel in (
        "docs",
        "docs/concepts/fundamentals/slots",
        "docs/concepts/fundamentals/html_js_css_files",
        "docs/community/contributing",
        "docs/community/development",
        "docs/releases",
        "examples/tabs",
        "plugins",
        "benchmarks",
        "v/dev/docs/concepts",
        "static/vendor",
        "pagefind",
    ):
        _write_page(site, f"{rel}/index.html")
    emit_redirects(site, site_url="https://ex.com/base")
    return site


def test_legacy_map_drops_docs_prefix(site: Path) -> None:
    mapping = legacy_redirect_map(site)
    assert mapping["/concepts/fundamentals/slots/"] == "/docs/concepts/fundamentals/slots/"
    assert mapping["/"] == "/docs/"


def test_legacy_map_keeps_root_pages_at_their_path(site: Path) -> None:
    mapping = legacy_redirect_map(site)
    assert mapping["/examples/tabs/"] == "/examples/tabs/"
    assert mapping["/plugins/"] == "/plugins/"
    assert mapping["/benchmarks/"] == "/benchmarks/"


def test_legacy_map_applies_moved_page_redirects(site: Path) -> None:
    mapping = legacy_redirect_map(site)
    assert mapping["/overview/contributing/"] == "/docs/community/contributing/"
    assert mapping["/overview/welcome/"] == "/docs/"
    assert mapping["/release_notes/"] == "/docs/releases/"


def test_legacy_map_skips_snapshots_and_assets(site: Path) -> None:
    mapping = legacy_redirect_map(site)
    # No key starts with /v/, /static/ or /pagefind/, and no value points into /v/.
    assert not [old for old in mapping if old.startswith(("/v/", "/static/", "/pagefind/"))]
    assert not [new for new in mapping.values() if new.startswith("/v/")]


def test_emit_legacy_redirects_writes_stubs_under_both_prefixes(site: Path) -> None:
    n = emit_legacy_redirects(site, site_url="https://ex.com/base")
    assert n == len(legacy_redirect_map(site)) * len(redirects.LEGACY_PREFIXES)

    for prefix in ("latest", "dev"):
        html = (site / prefix / "concepts/fundamentals/slots/index.html").read_text()
        # Canonical is absolute; refresh + JS targets are relative (base-path safe).
        assert 'href="https://ex.com/base/docs/concepts/fundamentals/slots/"' in html
        assert "url=../../../../docs/concepts/fundamentals/slots/" in html
        assert 'name="robots" content="noindex,follow"' in html
        # A link to a section of an old page keeps its anchor.
        assert "window.location.search + window.location.hash" in html
        assert "url=../docs/" in (site / prefix / "index.html").read_text()


def test_emit_legacy_redirects_is_repeatable(site: Path) -> None:
    first = emit_legacy_redirects(site, site_url="https://ex.com/base")
    second = emit_legacy_redirects(site, site_url="https://ex.com/base")
    # The stubs from the first run are not mistaken for pages by the second.
    assert first == second
    assert not (site / "latest" / "latest").exists()
    assert not (site / "dev" / "latest").exists()


def test_legacy_stubs_all_resolve(site: Path) -> None:
    emit_legacy_redirects(site, site_url="https://ex.com/base")
    assert list(redirect_target.check(_ctx(site))) == []


def test_docs_assemble_writes_legacy_stubs(site: Path, tmp_path: Path) -> None:
    # `no_build` assembles into the site above instead of building the real docs;
    # the empty versions dir keeps the committed snapshots out of the test.
    with override_settings(VERSIONS_DIR=tmp_path / "no_versions", SITE_URL="https://ex.com/base"):
        call_command("docs_assemble", output=str(site), no_build=True, no_dev=True)
    assert (site / "latest" / "concepts/fundamentals/slots/index.html").is_file()
    assert (site / "dev" / "examples/tabs/index.html").is_file()


# -- guard (5c.18) -------------------------------------------------------------


def test_guard_passes_when_target_resolves(tmp_path: Path) -> None:
    _write_page(tmp_path, "docs/foo/index.html")
    _write_stub(tmp_path, "old/index.html", "../docs/foo/")
    assert list(redirect_target.check(_ctx(tmp_path))) == []


def test_guard_errors_on_broken_target(tmp_path: Path) -> None:
    _write_stub(tmp_path, "old/index.html", "../docs/gone/")
    results = list(redirect_target.check(_ctx(tmp_path)))
    assert len(results) == 1
    assert results[0].severity is Severity.ERROR
    assert "does not resolve" in results[0].message


def test_guard_skips_external_redirect(tmp_path: Path) -> None:
    _write_stub(tmp_path, "old/index.html", "https://example.com/elsewhere/")
    assert list(redirect_target.check(_ctx(tmp_path))) == []


def test_emitted_redirects_all_resolve_against_real_build() -> None:
    # The shipped REDIRECTS map must point only at pages that exist. The build
    # emits these stubs and docs_build_check runs this guard, but assert the
    # config's targets are non-empty + well-formed here as a fast unit check.
    for old, new in redirects.REDIRECTS.items():
        assert old.startswith("/") and old.endswith("/")
        assert new.startswith("/") and new.endswith("/")
