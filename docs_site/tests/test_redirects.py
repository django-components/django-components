"""Tests for Phase 5c Chunk 5 redirects (features 5c.17 emitter + 5c.18 guard)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from apps.docs.build import redirects
from apps.docs.build.guards import GuardContext, redirect_target
from apps.docs.build.guards.base import Severity
from apps.docs.build.redirects import (
    emit_legacy_redirects,
    emit_redirects,
    emit_version_redirects,
    legacy_redirect_map,
)
from apps.docs.build.site_index import SiteIndex
from apps.docs.build.versioning import update_manifest
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


# -- old /<version>/ URLs ---------------------------------------------------------


@pytest.fixture
def versions(tmp_path: Path, site: Path) -> Path:
    """
    A committed versions tree with two releases, as `docs_assemble` sees it.

    0.148.0 is mounted under `site/v/` (published). 0.130 is committed but not
    mounted (outside the publish window). Each holds pages and files that are not pages.
    """
    root = tmp_path / "versions"
    pages = {
        "0.148.0": (
            "index.html",
            "concepts/fundamentals/slots/index.html",
            "reference/api/index.html",
            "404.html",
            "overrides/main.html",
            "assets/app.js",
            "objects.inv",
        ),
        "0.130": (
            "index.html",
            "concepts/fundamentals/slots/index.html",
            "concepts/fundamentals/defining_js_css_html_files/index.html",
            "examples/tabs/index.html",
            "reference/testing_api/index.html",
            "404.html",
        ),
    }
    for version, files in pages.items():
        for rel in files:
            _write_page(root / version, rel)
        update_manifest(root, version)
    shutil.copytree(root / "0.148.0", site / "v" / "0.148.0")
    return root


def _stub_path(site: Path, version: str, rel: str) -> Path:
    return site / version / rel / "index.html"


def test_version_redirects_mounted_version_goes_to_the_same_page_under_v(site: Path, versions: Path) -> None:
    emit_version_redirects(site, versions, site_url="https://ex.com/base")

    html = _stub_path(site, "0.148.0", "concepts/fundamentals/slots").read_text()
    # The old path and the new one are the same page, one folder deeper under /v/.
    assert 'href="https://ex.com/base/v/0.148.0/concepts/fundamentals/slots/"' in html
    assert "url=../../../../v/0.148.0/concepts/fundamentals/slots/" in html
    assert "This page has moved." in html
    assert 'name="robots" content="noindex,follow"' in html
    # A link to a section of an old page keeps its anchor.
    assert "window.location.search + window.location.hash" in html
    # The version's home page redirects too.
    assert "url=../v/0.148.0/" in (site / "0.148.0" / "index.html").read_text()


def test_version_redirects_unmounted_version_goes_to_the_current_page(site: Path, versions: Path) -> None:
    emit_version_redirects(site, versions, site_url="https://ex.com/base")

    # The same path exists in the current docs without the `docs/` prefix.
    html = _stub_path(site, "0.130", "concepts/fundamentals/slots").read_text()
    assert 'href="https://ex.com/base/docs/concepts/fundamentals/slots/"' in html
    assert "url=../../../../docs/concepts/fundamentals/slots/" in html
    # The page says why the visitor ends up on a different version.
    assert "Version 0.130 of the docs is no longer hosted, so this link goes to the same page" in html
    # Pages outside docs/ keep their path, and moved pages follow `REDIRECTS`.
    assert "url=../../../examples/tabs/" in _stub_path(site, "0.130", "examples/tabs").read_text()
    moved = _stub_path(site, "0.130", "concepts/fundamentals/defining_js_css_html_files").read_text()
    assert "url=../../../../docs/concepts/fundamentals/html_js_css_files/" in moved
    # The home page of a version that is not mounted goes to the docs home page,
    # with the right canonical (no stray `./`) and the fallback-free message.
    home = (site / "0.130" / "index.html").read_text()
    assert "url=../docs/" in home
    assert 'href="https://ex.com/base/docs/"' in home
    assert "so this link goes to the same page in the current docs" in home


def test_version_redirects_page_without_a_current_counterpart_goes_to_docs_home(site: Path, versions: Path) -> None:
    emit_version_redirects(site, versions, site_url="https://ex.com/base")

    html = _stub_path(site, "0.130", "reference/testing_api").read_text()
    assert 'href="https://ex.com/base/docs/"' in html
    assert "url=../../../docs/" in html
    assert (
        "Version 0.130 of the docs is no longer hosted, and the current docs have no matching page, "
        "so this link goes to the docs home page."
    ) in html


def test_version_redirects_skip_files_that_are_not_pages(site: Path, versions: Path) -> None:
    emit_version_redirects(site, versions, site_url="https://ex.com/base")

    # Only `index.html` pages get a stub, so assets, templates, `404.html` and
    # `objects.inv` are not redirected.
    stubs = sorted(p.relative_to(site).as_posix() for v in ("0.148.0", "0.130") for p in (site / v).rglob("*.*"))
    assert stubs == [
        "0.130/concepts/fundamentals/defining_js_css_html_files/index.html",
        "0.130/concepts/fundamentals/slots/index.html",
        "0.130/examples/tabs/index.html",
        "0.130/index.html",
        "0.130/reference/testing_api/index.html",
        "0.148.0/concepts/fundamentals/slots/index.html",
        "0.148.0/index.html",
        "0.148.0/reference/api/index.html",
    ]


def test_version_redirects_read_a_mounted_version_from_its_mounted_copy(site: Path, versions: Path) -> None:
    # A page that is committed but missing from the mounted copy has no target under
    # /v/, so it gets no stub. A page only the mounted copy has does get one.
    _write_page(versions / "0.148.0", "only/committed/index.html")
    _write_page(site / "v" / "0.148.0", "only/mounted/index.html")

    emit_version_redirects(site, versions, site_url="https://ex.com/base")

    assert not _stub_path(site, "0.148.0", "only/committed").exists()
    assert "url=../../../v/0.148.0/only/mounted/" in _stub_path(site, "0.148.0", "only/mounted").read_text()
    assert list(redirect_target.check(_ctx(site))) == []


def test_version_redirects_ignore_a_trailing_slash_on_the_site_url(site: Path, versions: Path) -> None:
    emit_version_redirects(site, versions, site_url="https://ex.com/base/")

    html = _stub_path(site, "0.148.0", "reference/api").read_text()
    assert 'href="https://ex.com/base/v/0.148.0/reference/api/"' in html


def test_version_redirects_count(site: Path, versions: Path) -> None:
    assert emit_version_redirects(site, versions, site_url="https://ex.com/base") == 8


def test_version_redirects_all_resolve(site: Path, versions: Path) -> None:
    emit_version_redirects(site, versions, site_url="https://ex.com/base")
    assert list(redirect_target.check(_ctx(site))) == []


def test_version_redirects_never_replace_a_real_page(site: Path, versions: Path) -> None:
    real = _stub_path(site, "0.148.0", "concepts/fundamentals/slots")
    real.parent.mkdir(parents=True)
    real.write_text("<html><body>a real page</body></html>", encoding="utf-8")

    # One stub fewer than the 8 pages: the real page keeps its path.
    assert emit_version_redirects(site, versions, site_url="https://ex.com/base") == 7
    assert real.read_text() == "<html><body>a real page</body></html>"
    assert (site / "0.148.0" / "index.html").is_file()


def test_version_redirects_are_repeatable(site: Path, versions: Path) -> None:
    before = legacy_redirect_map(site)
    first = emit_version_redirects(site, versions, site_url="https://ex.com/base")
    second = emit_version_redirects(site, versions, site_url="https://ex.com/base")
    # A second run writes the same stubs, and it does not take them for current
    # pages (which would add `/latest/0.148.0/...` stubs).
    assert first == second
    assert legacy_redirect_map(site) == before
    emit_legacy_redirects(site, site_url="https://ex.com/base")
    assert not (site / "latest" / "0.148.0").exists()
    assert not (site / "dev" / "0.130").exists()


def test_version_redirects_only_for_version_folders(site: Path, versions: Path) -> None:
    # A manifest entry that is not a release folder name never becomes a path.
    # The last name is made of Arabic-Indic digits, which `\d` would take for a version number.
    arabic = "\u0660.\u0661"
    for name in ("dev", "latest", "docs", arabic):
        _write_page(versions, f"{name}/index.html")
        update_manifest(versions, name)

    emit_version_redirects(site, versions, site_url="https://ex.com/base")

    assert not (site / "dev").exists()
    assert not (site / "latest").exists()
    assert not (site / arabic).exists()
    # The real `docs/` page is untouched.
    assert "ok" in (site / "docs" / "index.html").read_text()


def test_version_redirects_unmounted_versions_need_the_docs_home_page(site: Path, versions: Path) -> None:
    (site / "docs" / "index.html").unlink()

    n = emit_version_redirects(site, versions, site_url="https://ex.com/base")

    # With nowhere to send them, the unmounted version gets no stubs. The mounted one does.
    assert n == 3
    assert not (site / "0.130").exists()


def test_version_redirects_encode_odd_folder_names(site: Path, versions: Path) -> None:
    odd = "we ird#x&y'z"
    _write_page(versions / "0.148.0", f"{odd}/index.html")
    _write_page(site / "v" / "0.148.0", f"{odd}/index.html")

    emit_version_redirects(site, versions, site_url="https://ex.com/base")

    html = _stub_path(site, "0.148.0", odd).read_text()
    # The name stays one path segment, and none of its characters can end the attribute.
    encoded = "we%20ird%23x%26y%27z"
    assert f"url=../../v/0.148.0/{encoded}/" in html
    assert f'href="https://ex.com/base/v/0.148.0/{encoded}/"' in html
    assert f"location.replace({json.dumps(f'../../v/0.148.0/{encoded}/')}" in html
    assert odd not in html


def test_docs_assemble_writes_version_stubs(site: Path, versions: Path, tmp_path: Path) -> None:
    # A window of 1 mounts only the newest release (0.148.0); 0.130 stays committed.
    config = tmp_path / "docs_versions.toml"
    config.write_text("[publish]\nwindow = 1\n", encoding="utf-8")
    shutil.rmtree(site / "v")
    with override_settings(VERSIONS_DIR=versions, VERSIONS_CONFIG=config, SITE_URL="https://ex.com/base"):
        call_command("docs_assemble", output=str(site), no_build=True, no_dev=True)

    assert "url=../../../v/0.148.0/reference/api/" in _stub_path(site, "0.148.0", "reference/api").read_text()
    assert (
        "url=../../../../docs/concepts/fundamentals/slots/"
        in _stub_path(site, "0.130", "concepts/fundamentals/slots").read_text()
    )
    assert list(redirect_target.check(_ctx(site))) == []


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
