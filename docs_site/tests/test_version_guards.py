"""
Tests for the Phase 5b version guards (features 5b.13 / 5b.14 / 5b.15).

Builds synthetic docs_site/versions/ trees with the real versioning helpers and
asserts the guards pass on a healthy tree and flag each kind of corruption:
manifest <-> filesystem drift, half-built dirs, broken aliases, bad stamps, and
dangling links across version subtrees.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from apps.docs.build.guards import VERSION_GUARDS, GuardContext, Severity, run_guards
from apps.docs.build.guards.cross_version_link import check as link_check
from apps.docs.build.guards.versions_manifest import check as manifest_check
from apps.docs.build.versioning import (
    BUILD_INFO_NAME,
    IMPORTED_BUILDER_VERSION,
    is_frozen_import,
    materialize_alias,
    update_manifest,
    write_build_info,
)


def _ctx(root: Path) -> GuardContext:
    return GuardContext(
        content_dir=root, examples_dir=root, nav_path=root / "_nav.yml", static_dir=root, versions_root=root
    )


def _build_version(root: Path, version: str, *, pages: tuple[str, ...] = ("index.html",), sha: str = "sha1") -> None:
    vdir = root / version
    for page in pages:
        fp = vdir / page
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("<html><body><a href='./'>self</a></body></html>", encoding="utf-8")
    write_build_info(vdir, version=version, source_sha=sha)


def _clean_tree(root: Path) -> None:
    _build_version(root, "0.150.0")
    _build_version(root, "0.151.0")
    update_manifest(root, "0.150.0")
    update_manifest(root, "0.151.0", aliases=("latest",))
    materialize_alias(root, "latest", "0.151.0")


def _errors(results: list) -> list:
    return [r for r in results if r.severity is Severity.ERROR]


# -- versions_manifest guard ---------------------------------------------------


def test_clean_tree_passes_both_guards(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    assert list(manifest_check(_ctx(tmp_path))) == []
    assert list(link_check(_ctx(tmp_path))) == []


def test_absent_versions_root_is_noop(tmp_path: Path) -> None:
    assert list(manifest_check(_ctx(tmp_path / "nope"))) == []
    assert list(link_check(_ctx(tmp_path / "nope"))) == []


def test_orphan_version_dir_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    _build_version(tmp_path, "0.149.0")  # stamped dir, never added to the manifest
    msgs = [r.message for r in _errors(list(manifest_check(_ctx(tmp_path))))]
    assert any("0.149.0" in m and "not listed" in m for m in msgs)


def test_half_built_missing_index_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "0.151.0" / "index.html").unlink()
    msgs = [r.message for r in _errors(list(manifest_check(_ctx(tmp_path))))]
    assert any("no index.html" in m for m in msgs)


def test_half_built_missing_stamp_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "0.151.0" / BUILD_INFO_NAME).unlink()
    msgs = [r.message for r in _errors(list(manifest_check(_ctx(tmp_path))))]
    assert any(BUILD_INFO_NAME in m for m in msgs)


def test_manifest_entry_without_dir_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    # Manifest knows 0.152.0 but it was never built.
    update_manifest(tmp_path, "0.152.0")
    msgs = [r.message for r in _errors(list(manifest_check(_ctx(tmp_path))))]
    assert any("0.152.0" in m and "does not exist" in m for m in msgs)


def test_broken_alias_missing_dir_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    shutil.rmtree(tmp_path / "latest")
    msgs = [r.message for r in _errors(list(manifest_check(_ctx(tmp_path))))]
    assert any("latest" in m and "does not exist" in m for m in msgs)


def test_alias_pointing_at_wrong_version_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    # Manifest says latest -> 0.151.0, but materialize it against 0.150.0.
    materialize_alias(tmp_path, "latest", "0.150.0")
    msgs = [r.message for r in _errors(list(manifest_check(_ctx(tmp_path))))]
    assert any("latest" in m and "does not redirect" in m for m in msgs)


def test_stamp_missing_required_field_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "0.151.0" / BUILD_INFO_NAME).write_text('{"version": "0.151.0"}', encoding="utf-8")
    msgs = [r.message for r in _errors(list(manifest_check(_ctx(tmp_path))))]
    assert any("missing field" in m for m in msgs)


# -- cross_version_link guard --------------------------------------------------


def test_dangling_intra_version_link_flagged(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "0.151.0" / "index.html").write_text(
        '<html><body><a href="missing/page/">x</a></body></html>', encoding="utf-8"
    )
    errs = _errors(list(link_check(_ctx(tmp_path))))
    assert any("missing/page" in r.message for r in errs)


def test_external_absolute_and_anchor_links_skipped(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    (tmp_path / "0.151.0" / "index.html").write_text(
        "<html><body>"
        '<a href="https://example.com">ext</a>'
        '<a href="/static/x.js">abs</a>'
        '<a href="#section">frag</a>'
        '<a href="mailto:a@b.c">mail</a>'
        "</body></html>",
        encoding="utf-8",
    )
    assert list(link_check(_ctx(tmp_path))) == []


def test_markdown_and_asset_links_skipped(tmp_path: Path) -> None:
    # Raw .md companions and image assets are skipped (mirrors internal_link), so
    # they don't fail even when absent. A clean-URL version dir like 0.150.0/,
    # whose ".0" reads as an extension, must NOT be mistaken for an asset.
    _clean_tree(tmp_path)
    (tmp_path / "0.151.0" / "index.html").write_text(
        '<html><body><a href="../nope.md">md</a><a href="./img.png">img</a></body></html>',
        encoding="utf-8",
    )
    assert list(link_check(_ctx(tmp_path))) == []


def test_cross_version_link_resolution(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    # 0.151.0 -> 0.150.0 resolves (exists); -> 0.149.0 does not.
    (tmp_path / "0.151.0" / "index.html").write_text(
        '<html><body><a href="../0.150.0/">ok</a><a href="../0.149.0/">dead</a></body></html>',
        encoding="utf-8",
    )
    msgs = [r.message for r in _errors(list(link_check(_ctx(tmp_path))))]
    assert any("0.149.0" in m for m in msgs)
    assert not any("0.150.0" in m for m in msgs)


# -- frozen gh-pages imports (feature 6.2) -------------------------------------


def _import_version(root: Path, version: str, *, pages: tuple[str, ...] = ("index.html",)) -> None:
    """A version mirrored verbatim from gh-pages: stamped with the imported sentinel."""
    vdir = root / version
    for page in pages:
        fp = vdir / page
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("<html><body><a href='./'>self</a></body></html>", encoding="utf-8")
    write_build_info(vdir, version=version, source_sha="frozensha", builder_version=IMPORTED_BUILDER_VERSION)


def test_is_frozen_import_distinguishes_imported_from_built(tmp_path: Path) -> None:
    _build_version(tmp_path, "0.151.0")  # new-builder stamp
    _import_version(tmp_path, "0.120")  # imported stamp
    assert is_frozen_import(tmp_path / "0.120") is True
    assert is_frozen_import(tmp_path / "0.151.0") is False
    assert is_frozen_import(tmp_path / "nope") is False  # no stamp at all


def test_frozen_import_without_index_passes_manifest(tmp_path: Path) -> None:
    # 0.111 shipped from the old mkdocs deploy with no root index.html. A new
    # build with that gap is half-built (flagged), but a frozen import inherits
    # the old deploy as-is, so the guard must not flag it.
    _build_version(tmp_path, "0.151.0")
    _import_version(tmp_path, "0.111", pages=("overview/index.html",))  # NB: no root index.html
    update_manifest(tmp_path, "0.151.0", aliases=("latest",))
    update_manifest(tmp_path, "0.111")
    materialize_alias(tmp_path, "latest", "0.151.0")
    assert list(manifest_check(_ctx(tmp_path))) == []


def test_frozen_import_broken_links_not_checked(tmp_path: Path) -> None:
    # Old historical HTML has long-dead relative links and mkdocs theme templates
    # with raw Jinja - we never rebuild it, so cross_version_link skips it. The
    # same broken link in a new-builder version IS still flagged.
    _clean_tree(tmp_path)
    _import_version(tmp_path, "0.120")
    update_manifest(tmp_path, "0.120")
    broken = '<html><body><a href="long/dead/link/">x</a></body></html>'
    (tmp_path / "0.120" / "index.html").write_text(broken, encoding="utf-8")
    assert list(link_check(_ctx(tmp_path))) == []

    # Control: the identical broken link in a new-builder version is flagged.
    (tmp_path / "0.151.0" / "index.html").write_text(broken, encoding="utf-8")
    assert any("long/dead/link" in r.message for r in _errors(list(link_check(_ctx(tmp_path)))))


# -- harness integration -------------------------------------------------------


def test_run_guards_with_version_guards(tmp_path: Path) -> None:
    _clean_tree(tmp_path)
    results, ok = run_guards(_ctx(tmp_path), strict=True, guards=VERSION_GUARDS)
    assert ok
    assert results == []
