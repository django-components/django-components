"""
Versions manifest <-> filesystem parity guard (features 5b.13 / 5b.14).

Validates the committed docs_site/versions/ tree against its versions.json:

- every manifest version has a built ``<version>/`` dir with an index.html and a
  ``_build_info.json`` (no half-built dirs);
- every on-disk version dir (one carrying ``_build_info.json``) appears in the
  manifest (no orphans either way);
- each ``_build_info.json`` parses and has the required fields;
- every alias in the manifest (e.g. ``latest``) has a redirect dir pointing at
  its target version.

Runs only when ``ctx.versions_root`` is set (the docs_versions_check command);
it's a no-op for the per-build content suite. Spec: DESIGN_spike_7.md section 11.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import TYPE_CHECKING

from apps.docs._vendor.mike_versions import Versions
from apps.docs.build.versioning import BUILD_INFO_NAME, MANIFEST_NAME, is_frozen_import

from .base import GuardResult

if TYPE_CHECKING:
    from pathlib import Path

    from .base import GuardContext

_REQUIRED_STAMP_FIELDS = ("version", "source_sha", "built_at", "builder_version")


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    root = ctx.versions_root
    if root is None or not root.is_dir():
        return

    manifest_path = root / MANIFEST_NAME
    # On-disk version dirs are the ones carrying a build stamp (alias dirs like
    # latest/ hold redirect stubs and have no stamp).
    on_disk = {d.name for d in root.iterdir() if d.is_dir() and (d / BUILD_INFO_NAME).is_file()}

    if not manifest_path.is_file():
        if on_disk:
            yield GuardResult.error(
                guard="versions_manifest",
                message=f"{MANIFEST_NAME} is missing but version dirs exist: {', '.join(sorted(on_disk))}",
                source=MANIFEST_NAME,
            )
        return

    try:
        versions = Versions.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as e:
        yield GuardResult.error(
            guard="versions_manifest", message=f"{MANIFEST_NAME} is unreadable: {e}", source=MANIFEST_NAME
        )
        return

    manifest_versions = {str(v.version) for v in versions}
    aliases = {alias: str(v.version) for v in versions for alias in v.aliases}

    # Orphans: a stamped dir with no manifest entry (and not an alias dir).
    for name in sorted(on_disk - manifest_versions - set(aliases)):
        yield GuardResult.error(
            guard="versions_manifest",
            message=f"Version dir {name!r} is not listed in {MANIFEST_NAME}",
            source=name,
        )

    # Every manifest version must have a complete build on disk.
    for version in sorted(manifest_versions):
        vdir = root / version
        if not vdir.is_dir():
            yield GuardResult.error(
                guard="versions_manifest",
                message=f"Manifest lists {version!r} but {version}/ does not exist",
                source=version,
            )
            continue
        # New-builder versions must have a homepage; frozen gh-pages imports
        # inherit whatever the old deploy shipped (0.111 never had a root
        # index.html, so /v/0.111/ 404s the same as the old live site did).
        if not is_frozen_import(vdir) and not (vdir / "index.html").is_file():
            yield GuardResult.error(
                guard="versions_manifest",
                message=f"{version}/ is half-built: no index.html",
                source=version,
            )
        yield from _check_stamp(vdir / BUILD_INFO_NAME, version)

    # Every alias must have a redirect dir pointing at its target version.
    for alias, target in sorted(aliases.items()):
        yield from _check_alias(root, alias, target)


def _check_stamp(stamp: Path, version: str) -> Iterator[GuardResult]:
    if not stamp.is_file():
        yield GuardResult.error(
            guard="versions_manifest",
            message=f"{version}/ is half-built: no {BUILD_INFO_NAME}",
            source=version,
        )
        return
    try:
        data = json.loads(stamp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        yield GuardResult.error(
            guard="versions_manifest", message=f"{version}/{BUILD_INFO_NAME} is unreadable: {e}", source=version
        )
        return
    missing = [f for f in _REQUIRED_STAMP_FIELDS if not data.get(f)]
    if missing:
        yield GuardResult.error(
            guard="versions_manifest",
            message=f"{version}/{BUILD_INFO_NAME} is missing field(s): {', '.join(missing)}",
            source=version,
        )


def _check_alias(root: Path, alias: str, target: str) -> Iterator[GuardResult]:
    adir = root / alias
    if not adir.is_dir():
        yield GuardResult.error(
            guard="versions_manifest",
            message=f"Alias {alias!r} -> {target} is in the manifest but {alias}/ does not exist",
            source=alias,
        )
        return
    index = adir / "index.html"
    if not index.is_file():
        yield GuardResult.error(
            guard="versions_manifest",
            message=f"Alias {alias}/ has no index.html redirect",
            source=alias,
        )
        return
    # The redirect stub points at the target version; assert it references it.
    if f"/{target}/" not in index.read_text(encoding="utf-8"):
        yield GuardResult.error(
            guard="versions_manifest",
            message=f"Alias {alias}/ does not redirect to its manifest target {target!r}",
            source=alias,
        )
