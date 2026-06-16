"""
Tests for the Phase 5b versioning layer.

Covers the vendored mike `Versions` data model (ordering, alias coalescing,
JSON round-trip) and the manifest / build-stamp / alias-redirect helpers in
apps/docs/build/versioning.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from apps.docs._vendor.mike_versions import Versions
from apps.docs.build.versioning import (
    BUILD_INFO_NAME,
    DOCS_BUILDER_VERSION,
    MANIFEST_NAME,
    load_manifest,
    materialize_alias,
    render_redirect,
    update_manifest,
    write_build_info,
    write_manifest,
)

# -- vendored Versions data model ----------------------------------------------


def test_versions_sort_newest_first_with_dev_on_top() -> None:
    versions = Versions()
    for v in ["0.149.0", "0.151.0", "0.150.0", "dev"]:
        versions.add(v)
    order = [str(info.version) for info in versions]
    # `dev` (no leading digit) floats above releases; releases sort descending.
    assert order == ["dev", "0.151.0", "0.150.0", "0.149.0"]


def test_versions_two_part_sorts_below_three_part() -> None:
    versions = Versions()
    for v in ["0.139", "0.139.1"]:
        versions.add(v)
    assert [str(info.version) for info in versions] == ["0.139.1", "0.139"]


def test_alias_moves_to_newest_with_update_aliases() -> None:
    versions = Versions()
    versions.add("0.150.0", aliases=["latest"])
    versions.add("0.151.0", aliases=["latest"], update_aliases=True)
    assert versions["0.151.0"].aliases == {"latest"}
    assert versions["0.150.0"].aliases == set()


def test_versions_json_round_trip() -> None:
    versions = Versions()
    versions.add("0.151.0", aliases=["latest"])
    versions.add("0.150.0")
    restored = Versions.loads(versions.dumps())
    assert restored.to_json() == versions.to_json()
    # Manifest shape is mike-compatible: a list of {version, title, aliases}.
    first = json.loads(versions.dumps())[0]
    assert set(first) == {"version", "title", "aliases"}


# -- manifest helpers ----------------------------------------------------------


def test_load_manifest_absent_is_empty(tmp_path: Path) -> None:
    assert len(load_manifest(tmp_path)) == 0


def test_update_manifest_adds_and_persists(tmp_path: Path) -> None:
    update_manifest(tmp_path, "0.150.0")
    update_manifest(tmp_path, "0.151.0", aliases=("latest",))

    manifest = tmp_path / MANIFEST_NAME
    assert manifest.is_file()
    versions = load_manifest(tmp_path)
    assert {str(v.version) for v in versions} == {"0.150.0", "0.151.0"}
    assert versions["0.151.0"].aliases == {"latest"}


def test_update_manifest_moves_alias_to_new_release(tmp_path: Path) -> None:
    update_manifest(tmp_path, "0.150.0", aliases=("latest",))
    update_manifest(tmp_path, "0.151.0", aliases=("latest",))
    versions = load_manifest(tmp_path)
    assert versions["0.151.0"].aliases == {"latest"}
    assert versions["0.150.0"].aliases == set()


def test_write_manifest_is_newline_terminated(tmp_path: Path) -> None:
    versions = Versions()
    versions.add("0.151.0")
    write_manifest(tmp_path, versions)
    assert (tmp_path / MANIFEST_NAME).read_text(encoding="utf-8").endswith("\n")


# -- build-info stamp ----------------------------------------------------------


def test_write_build_info_payload(tmp_path: Path) -> None:
    info = write_build_info(tmp_path, version="0.151.0", source_sha="abc123")
    assert info["version"] == "0.151.0"
    assert info["source_sha"] == "abc123"
    assert info["source_tag"] == "0.151.0"  # defaults to version
    assert info["builder_version"] == DOCS_BUILDER_VERSION
    assert "built_at" in info

    on_disk = json.loads((tmp_path / BUILD_INFO_NAME).read_text(encoding="utf-8"))
    assert on_disk == info


def test_write_build_info_explicit_tag(tmp_path: Path) -> None:
    info = write_build_info(tmp_path, version="dev", source_sha="deadbeef", source_tag="dev")
    assert info["source_tag"] == "dev"


# -- alias redirect materializer -----------------------------------------------


def _make_version_dir(root: Path, version: str, pages: list[str]) -> None:
    for page in pages:
        path = root / version / page
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html><body>page</body></html>", encoding="utf-8")


def test_render_redirect_substitutes_href() -> None:
    html = render_redirect("../0.151.0/index.html")
    assert html.count("../0.151.0/index.html") >= 2  # <meta refresh> + JS replace
    assert "window.location.replace" in html


def test_materialize_alias_mirrors_pages_with_relative_hrefs(tmp_path: Path) -> None:
    _make_version_dir(tmp_path, "0.151.0", ["index.html", "foo/index.html"])

    count = materialize_alias(tmp_path, "latest", "0.151.0")
    assert count == 2

    root_stub = (tmp_path / "latest" / "index.html").read_text(encoding="utf-8")
    assert "../0.151.0/index.html" in root_stub
    nested_stub = (tmp_path / "latest" / "foo" / "index.html").read_text(encoding="utf-8")
    assert "../../0.151.0/foo/index.html" in nested_stub


def test_materialize_alias_clears_stale_stubs_when_target_moves(tmp_path: Path) -> None:
    # latest first points at 0.150.0, which has a page 0.151.0 lacks.
    _make_version_dir(tmp_path, "0.150.0", ["index.html", "removed/index.html"])
    materialize_alias(tmp_path, "latest", "0.150.0")
    assert (tmp_path / "latest" / "removed" / "index.html").exists()

    # Moving latest to 0.151.0 must drop the stale `removed/` redirect.
    _make_version_dir(tmp_path, "0.151.0", ["index.html"])
    materialize_alias(tmp_path, "latest", "0.151.0")
    assert not (tmp_path / "latest" / "removed").exists()
    assert (tmp_path / "latest" / "index.html").exists()
