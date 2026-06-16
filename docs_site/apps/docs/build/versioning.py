"""
Docs versioning: manifest, per-version build stamp, and alias redirects (5b).

Built doc versions live under ``docs_site/versions/<version>/`` (committed to
the repo), alongside a sibling ``versions.json`` manifest and redirect stubs
for aliases like ``latest/``. This module is the thin layer the build commands
use to read and write that tree:

- ``load_manifest`` / ``update_manifest`` - read/merge ``versions.json`` using
  the vendored mike ``Versions`` data model (which also gives us the
  LooseVersion ordering, with ``dev`` sorting above releases).
- ``write_build_info`` - the per-version ``_build_info.json`` stamp that lets
  ``docs-build-all`` decide whether a version dir is up to date (idempotency).
- ``materialize_alias`` - rebuild ``<alias>/`` as ``<meta refresh>`` redirect
  stubs mirroring every page of the target version (the vendored mike redirect
  template). Redirect mode is preferred over symlink/copy so the committed tree
  is cross-platform and tiny (see DESIGN_spike_7.md section 2.4).

The layout mirrors what gets mounted at ``/v/`` on the deployed site, so the
version picker's ``../versions.json`` lookup and the alias redirects resolve
the same on disk as in production.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from apps.docs._vendor.mike_versions import Versions

# Stamped into every _build_info.json. Bump when the builder's output format
# changes in a way that warrants reflowing historical versions (the planned
# `docs-build-all --rebuild-if-builder-older-than=<v>`, spike 7 section 3.3).
DOCS_BUILDER_VERSION = "1.0.0"

MANIFEST_NAME = "versions.json"
BUILD_INFO_NAME = "_build_info.json"

# Vendored mike redirect template (one per aliased page).
_REDIRECT_TEMPLATE = Path(__file__).resolve().parent.parent / "_vendor" / "mike_redirect.html"


def load_manifest(versions_root: Path) -> Versions:
    """Read ``versions_root/versions.json`` into a ``Versions``; empty if absent."""
    manifest = versions_root / MANIFEST_NAME
    if manifest.is_file():
        return Versions.loads(manifest.read_text(encoding="utf-8"))
    return Versions()


def write_manifest(versions_root: Path, versions: Versions) -> None:
    """Write ``versions`` to ``versions_root/versions.json`` (newest-first, pretty)."""
    versions_root.mkdir(parents=True, exist_ok=True)
    (versions_root / MANIFEST_NAME).write_text(versions.dumps() + "\n", encoding="utf-8")


def update_manifest(
    versions_root: Path,
    version: str,
    *,
    title: str | None = None,
    aliases: tuple[str, ...] = (),
) -> Versions:
    """
    Add or update ``version`` (with ``aliases``) in the manifest and write it.

    ``update_aliases=True`` moves an alias like ``latest`` off whatever version
    previously held it onto this one, which is exactly what a new release wants.
    """
    versions = load_manifest(versions_root)
    versions.add(version, title=title, aliases=list(aliases), update_aliases=True)
    write_manifest(versions_root, versions)
    return versions


def git_head_sha(repo_root: Path) -> str:
    """Current ``HEAD`` commit SHA, or "" if git is unavailable (best-effort stamp)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return ""
    return out.stdout.strip()


def write_build_info(
    version_dir: Path,
    *,
    version: str,
    source_sha: str,
    source_tag: str | None = None,
    builder_version: str = DOCS_BUILDER_VERSION,
) -> dict[str, str]:
    """
    Write ``version_dir/_build_info.json`` recording how this version was built.

    The stamp is what makes ``docs-build-all`` idempotent: it compares
    ``source_sha`` against the tag's commit and skips the rebuild when they
    match. Returns the written payload (handy for tests/logging).
    """
    info = {
        "version": version,
        "source_sha": source_sha,
        "source_tag": source_tag if source_tag is not None else version,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "builder_version": builder_version,
    }
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / BUILD_INFO_NAME).write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return info


def render_redirect(href: str) -> str:
    """Render the vendored mike redirect stub pointing at ``href``."""
    return _REDIRECT_TEMPLATE.read_text(encoding="utf-8").replace("{{href}}", href)


def materialize_alias(versions_root: Path, alias: str, target_version: str) -> int:
    """
    Rebuild ``versions_root/<alias>/`` as redirect stubs mirroring every ``.html``
    page under ``versions_root/<target_version>/``. Returns the redirect count.

    The alias dir is cleared first so an alias that moves (e.g. ``latest`` from
    an old release to a new one) doesn't leave stale redirects behind. Each stub
    points at the matching page via a relative href, so it resolves whether the
    tree is served from the repo or from the deploy artifact.
    """
    target_dir = versions_root / target_version
    alias_dir = versions_root / alias
    if alias_dir.exists():
        shutil.rmtree(alias_dir)

    count = 0
    for html in sorted(target_dir.rglob("*.html")):
        rel = html.relative_to(target_dir)
        dest = alias_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Relative href from the alias stub to the real page under the version
        # dir (e.g. latest/foo/index.html -> ../../<version>/foo/index.html).
        href = os.path.relpath(html, dest.parent).replace(os.sep, "/")
        dest.write_text(render_redirect(href), encoding="utf-8")
        count += 1
    return count
