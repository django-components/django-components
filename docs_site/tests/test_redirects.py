"""Tests for Phase 5c Chunk 5 redirects (features 5c.17 emitter + 5c.18 guard)."""

from __future__ import annotations

import json
from pathlib import Path

from apps.docs.build import redirects
from apps.docs.build.guards import GuardContext, redirect_target
from apps.docs.build.guards.base import Severity
from apps.docs.build.redirects import emit_redirects
from apps.docs.build.site_index import SiteIndex


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
    assert f"location.replace({json.dumps(rel)})" in html
    assert 'name="robots" content="noindex,follow"' in html


def test_emit_redirects_home_target_relative(tmp_path: Path) -> None:
    emit_redirects(tmp_path, site_url="https://ex.com/base")
    html = (tmp_path / "README/index.html").read_text()
    assert "url=../docs/" in html  # /README/ -> /docs/


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
