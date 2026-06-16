"""
docs-build-all bootstrap walker: config + tag selection + orchestration (5b.8).

`docs-build-all` rebuilds many versions in one shot (initial bootstrap or
disaster recovery): it walks the git tags selected by ``docs_versions.toml``,
checks each out in a worktree, runs ``docs-build`` against it, and finally
rewrites ``versions.json`` from whatever version dirs ended up on disk. See
DESIGN_spike_7.md section 3.

This module holds the pieces that don't touch git directly, so they're unit
testable:

- ``VersionsConfig`` + ``load_versions_config`` - parse the TOML.
- ``select_tags`` - apply pattern / include / exclude / oldest / newest and sort
  newest-first.
- ``needs_rebuild`` - the idempotency check (compare a version dir's build stamp
  against the tag's commit SHA).
- ``bootstrap_versions`` - the orchestration loop. The git/worktree/build side
  effects are injected (``tag_sha`` and ``build_one``), so tests can drive the
  whole loop with fakes while the real command (docs_build_all.py) supplies the
  worktree machinery.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import tomllib
from verspec.loose import LooseVersion

from apps.docs._vendor.mike_versions import Versions
from apps.docs.build.versioning import (
    BUILD_INFO_NAME,
    materialize_alias,
    write_manifest,
)


@dataclass
class VersionsConfig:
    pattern: str = r"^v?\d+\.\d+(\.\d+)?$"
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    oldest: str = ""
    newest: str = ""
    latest_alias: str = ""  # which version `latest/` points at ("" = newest built)


def load_versions_config(path: Path) -> VersionsConfig:
    """Parse ``docs_versions.toml``; missing file / keys fall back to defaults."""
    if not path.is_file():
        return VersionsConfig()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    versions = data.get("versions", {})
    aliases = data.get("aliases", {})
    defaults = VersionsConfig()
    return VersionsConfig(
        pattern=versions.get("pattern") or defaults.pattern,
        include=list(versions.get("include", [])),
        exclude=list(versions.get("exclude", [])),
        oldest=versions.get("oldest", "") or "",
        newest=versions.get("newest", "") or "",
        latest_alias=aliases.get("latest", "") or "",
    )


def tag_to_version(tag: str) -> str:
    """Canonical version string for a tag (strip a single leading ``v``)."""
    return tag.removeprefix("v")


def _lv(tag: str) -> LooseVersion:
    return LooseVersion(tag_to_version(tag))


def select_tags(all_tags: list[str], config: VersionsConfig) -> list[str]:
    """
    Filter ``all_tags`` by the config and return them newest-first.

    Pattern-matched tags are subject to the oldest/newest bounds; ``include``
    entries that are real tags are always kept (they bypass pattern + bounds).
    """
    excluded = set(config.exclude)
    rx = re.compile(config.pattern)

    matched = [t for t in all_tags if t not in excluded and rx.match(t)]
    if config.oldest:
        matched = [t for t in matched if _lv(t) >= _lv(config.oldest)]
    if config.newest:
        matched = [t for t in matched if _lv(t) <= _lv(config.newest)]

    extras = [t for t in config.include if t in all_tags and t not in excluded]
    # dict.fromkeys de-dupes while preserving first-seen order before the sort.
    result = list(dict.fromkeys(matched + extras))
    result.sort(key=_lv, reverse=True)
    return result


def needs_rebuild(version_dir: Path, expected_sha: str) -> bool:
    """
    True if ``version_dir`` is missing, unstamped, or built from a different
    commit than ``expected_sha`` (the idempotency check).
    """
    stamp = version_dir / BUILD_INFO_NAME
    if not stamp.is_file():
        return True
    try:
        data = json.loads(stamp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True
    return data.get("source_sha") != expected_sha


@dataclass
class BootstrapOutcome:
    built: list[str] = field(default_factory=list)
    skipped_up_to_date: list[str] = field(default_factory=list)
    skipped_no_builder: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


# build_one(tag, version, version_dir) -> "built" | "skipped_no_builder".
# Raises on a real build failure (caught per-tag by the orchestrator).
BuildOne = Callable[[str, str, Path], str]


def bootstrap_versions(
    config: VersionsConfig,
    *,
    versions_root: Path,
    all_tags: list[str],
    tag_sha: Callable[[str], str],
    build_one: BuildOne,
    log: Callable[[str], None] = lambda _msg: None,
) -> BootstrapOutcome:
    """
    Walk the selected tags, build the stale ones, then rewrite the manifest.

    A single bad tag is recorded and skipped, not fatal. The manifest is rebuilt
    once at the end from whatever version dirs exist on disk (so it reflects the
    full, consistent set - never a half-state), and the ``latest`` alias is
    materialized as redirects against its target version.
    """
    outcome = BootstrapOutcome()
    selected = select_tags(all_tags, config)
    log(f"Selected {len(selected)} tag(s): {', '.join(selected) or '(none)'}")

    for tag in selected:
        version = tag_to_version(tag)
        version_dir = versions_root / version
        if not needs_rebuild(version_dir, tag_sha(tag)):
            outcome.skipped_up_to_date.append(version)
            log(f"  = {version}: up to date, skipping")
            continue
        try:
            status = build_one(tag, version, version_dir)
        except Exception as e:
            outcome.failed.append(version)
            log(f"  ! {version}: build failed: {type(e).__name__}: {e}")
            continue
        if status == "skipped_no_builder":
            outcome.skipped_no_builder.append(version)
        else:
            outcome.built.append(version)
            log(f"  + {version}: built")

    _rewrite_manifest(versions_root, config, log)
    return outcome


def _rewrite_manifest(versions_root: Path, config: VersionsConfig, log: Callable[[str], None]) -> None:
    """Rebuild versions.json from on-disk version dirs and materialize `latest`."""
    version_dirs = (
        sorted(d.name for d in versions_root.iterdir() if d.is_dir() and (d / BUILD_INFO_NAME).is_file())
        if versions_root.is_dir()
        else []
    )

    versions = Versions()
    for name in version_dirs:
        versions.add(name)

    # Resolve the `latest` alias target: explicit config, else the newest
    # built version (the manifest's first entry by mike's ordering).
    latest = config.latest_alias
    if not latest and len(versions):
        latest = str(next(iter(versions)).version)

    if latest and latest in version_dirs:
        versions.add(latest, aliases=["latest"], update_aliases=True)
        n = materialize_alias(versions_root, "latest", latest)
        log(f"latest/ -> {latest} ({n} redirects)")
    elif latest:
        log(f"WARNING: latest alias target {latest!r} has no built version dir; skipping alias")

    write_manifest(versions_root, versions)
    log(f"Wrote manifest with {len(versions)} version(s)")
