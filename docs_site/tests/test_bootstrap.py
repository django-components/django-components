"""
Tests for the Phase 5b docs-build-all bootstrap walker (features 5b.8 / 5b.12).

Covers the testable core in apps/docs/build/bootstrap.py: config parsing, tag
selection, the idempotency check, and the orchestration loop (driven with a fake
build_one + tag_sha, so no git/worktrees are needed here). The real worktree
machinery in the command is exercised separately by an integration run.
"""

from __future__ import annotations

from pathlib import Path

from apps.docs.build.bootstrap import (
    VersionsConfig,
    bootstrap_versions,
    load_versions_config,
    needs_rebuild,
    select_tags,
    tag_to_version,
)
from apps.docs.build.versioning import load_manifest, write_build_info
from django.conf import settings

# -- config --------------------------------------------------------------------


def test_load_config_parses_toml(tmp_path: Path) -> None:
    (tmp_path / "docs_versions.toml").write_text(
        '[versions]\npattern = "^x"\nexclude = ["0.1"]\noldest = "0.150.0"\n[aliases]\nlatest = "0.151.0"\n',
        encoding="utf-8",
    )
    cfg = load_versions_config(tmp_path / "docs_versions.toml")
    assert cfg.pattern == "^x"
    assert cfg.exclude == ["0.1"]
    assert cfg.oldest == "0.150.0"
    assert cfg.latest_alias == "0.151.0"


def test_load_config_missing_file_uses_defaults(tmp_path: Path) -> None:
    cfg = load_versions_config(tmp_path / "nope.toml")
    assert cfg.pattern  # default pattern present
    assert cfg.exclude == []


def test_repo_config_is_valid() -> None:
    # The real docs_versions.toml (in docs_site/) must parse and set a floor.
    cfg = load_versions_config(settings.VERSIONS_CONFIG)
    assert cfg.pattern
    assert cfg.oldest


# -- tag selection -------------------------------------------------------------


def test_tag_to_version_strips_leading_v() -> None:
    assert tag_to_version("v0.151.0") == "0.151.0"
    assert tag_to_version("0.151.0") == "0.151.0"


def test_select_tags_filters_bounds_excludes_and_sorts() -> None:
    cfg = VersionsConfig(exclude=["0.150.1"], oldest="0.149.0", newest="0.151.0")
    tags = ["0.148.0", "0.149.0", "0.150.0", "0.150.1", "0.151.0", "0.152.0", "random", "v0.149.5"]
    # 0.148 below oldest, 0.152 above newest, 0.150.1 excluded, "random" no match.
    assert select_tags(tags, cfg) == ["0.151.0", "0.150.0", "v0.149.5", "0.149.0"]


def test_select_tags_include_bypasses_pattern() -> None:
    cfg = VersionsConfig(include=["nightly"], oldest="")
    tags = ["0.151.0", "nightly", "not-included"]
    out = select_tags(tags, cfg)
    assert "nightly" in out  # kept despite not matching the version pattern
    assert "not-included" not in out


# -- idempotency ---------------------------------------------------------------


def test_needs_rebuild_when_dir_or_stamp_absent(tmp_path: Path) -> None:
    assert needs_rebuild(tmp_path / "missing", "abc")  # no dir
    (tmp_path / "0.151.0").mkdir()
    assert needs_rebuild(tmp_path / "0.151.0", "abc")  # dir but no stamp


def test_needs_rebuild_compares_source_sha(tmp_path: Path) -> None:
    write_build_info(tmp_path, version="0.151.0", source_sha="abc123")
    assert not needs_rebuild(tmp_path, "abc123")  # same commit -> skip
    assert needs_rebuild(tmp_path, "different")  # different commit -> rebuild


# -- orchestration -------------------------------------------------------------


def _fake_build_one(shas: dict[str, str], no_builder: set[str] = frozenset()):  # type: ignore[assignment]
    """A build_one that writes a fake snapshot + stamp instead of using git."""

    def build_one(tag: str, version: str, version_dir: Path) -> str:
        if version in no_builder:
            return "skipped_no_builder"
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "index.html").write_text("<html>built</html>", encoding="utf-8")
        write_build_info(version_dir, version=version, source_sha=shas[tag])
        return "built"

    return build_one


def test_bootstrap_builds_selected_and_writes_manifest(tmp_path: Path) -> None:
    cfg = VersionsConfig(oldest="0.150.0")
    tags = ["0.149.0", "0.150.0", "0.151.0"]  # 0.149.0 is below the floor
    shas = {t: f"sha-{t}" for t in tags}

    out = bootstrap_versions(
        cfg, versions_root=tmp_path, all_tags=tags, tag_sha=lambda t: shas[t], build_one=_fake_build_one(shas)
    )
    assert set(out.built) == {"0.150.0", "0.151.0"}

    versions = load_manifest(tmp_path)
    assert {str(v.version) for v in versions} == {"0.150.0", "0.151.0"}
    # `latest` defaults to the newest built version and is materialized.
    assert versions["0.151.0"].aliases == {"latest"}
    assert (tmp_path / "latest" / "index.html").is_file()


def test_bootstrap_second_run_is_idempotent(tmp_path: Path) -> None:
    cfg = VersionsConfig(oldest="0.150.0")
    tags = ["0.150.0", "0.151.0"]
    shas = {t: f"sha-{t}" for t in tags}

    def run():
        return bootstrap_versions(
            cfg, versions_root=tmp_path, all_tags=tags, tag_sha=lambda t: shas[t], build_one=_fake_build_one(shas)
        )

    run()
    out2 = run()
    assert out2.built == []
    assert set(out2.skipped_up_to_date) == {"0.150.0", "0.151.0"}


def test_bootstrap_records_failure_without_aborting(tmp_path: Path) -> None:
    cfg = VersionsConfig(oldest="0.150.0")
    tags = ["0.150.0", "0.151.0"]
    shas = {t: f"sha-{t}" for t in tags}

    def build_one(tag: str, version: str, version_dir: Path) -> str:
        if version == "0.151.0":
            raise RuntimeError("boom")
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "index.html").write_text("x", encoding="utf-8")
        write_build_info(version_dir, version=version, source_sha=shas[tag])
        return "built"

    out = bootstrap_versions(
        cfg, versions_root=tmp_path, all_tags=tags, tag_sha=lambda t: shas[t], build_one=build_one
    )
    assert out.failed == ["0.151.0"]
    assert out.built == ["0.150.0"]  # the other tag still built


def test_bootstrap_skips_tags_without_builder(tmp_path: Path) -> None:
    cfg = VersionsConfig(oldest="0.150.0")
    tags = ["0.150.0", "0.151.0"]
    shas = {t: f"sha-{t}" for t in tags}

    out = bootstrap_versions(
        cfg,
        versions_root=tmp_path,
        all_tags=tags,
        tag_sha=lambda t: shas[t],
        build_one=_fake_build_one(shas, no_builder={"0.150.0"}),
    )
    assert out.skipped_no_builder == ["0.150.0"]
    assert out.built == ["0.151.0"]
