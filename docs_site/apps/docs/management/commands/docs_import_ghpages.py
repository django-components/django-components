"""
docs-import-ghpages: one-time mirror of the old mike/gh-pages version tree into
``docs_site/versions/`` (Phase 6, feature 6.2).

The historical documentation versions were built by the old mkdocs + mike stack.
Their git tags predate the new ``docs_site`` builder, so they CANNOT be rebuilt
with it (``docs-build-all`` skips them - see that command's docstring). Instead
we copy each version's already-built HTML verbatim out of ``origin/gh-pages``.

What this does, once, at cutover:

1. Reads the version manifest from the gh-pages branch (already in the vendored
   mike ``versions.json`` format the new code uses).
2. For each listed version, extracts its subtree from gh-pages into
   ``docs_site/versions/<version>/`` verbatim (the old HTML uses version-dir-
   relative links, so it keeps working when served under ``/v/<version>/``).
3. Stamps each imported dir with a synthesized ``_build_info.json`` (recording
   the version's release-tag commit), because the version validator requires a
   stamp on every version dir. Imported dirs are marked with a distinct
   ``builder_version`` so they are never confused with new-builder output.
4. Writes the manifest and re-materializes each alias (e.g. ``latest``) as
   redirect stubs. gh-pages stores ``latest`` as a symlink, which is a
   cross-platform footgun; the new tree uses redirect HTML instead.

Run once:

    cd docs_site
    python manage.py docs_import_ghpages                 # mirror origin/gh-pages
    python manage.py docs_import_ghpages --ref origin/gh-pages
    python manage.py docs_import_ghpages --dry-run       # list what would import
"""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.docs._vendor.mike_versions import Versions
from apps.docs.build.versioning import (
    IMPORTED_BUILDER_VERSION,
    MANIFEST_NAME,
    materialize_alias,
    write_build_info,
    write_manifest,
)


class Command(BaseCommand):
    help = "One-time mirror of the old mike/gh-pages version tree into docs_site/versions/."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--ref",
            type=str,
            default="origin/gh-pages",
            help="Git ref of the old gh-pages branch (default: origin/gh-pages).",
        )
        parser.add_argument(
            "--versions-dir",
            type=str,
            default=None,
            help="Output root (default: settings.VERSIONS_DIR).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the versions that would be imported without writing anything.",
        )

    def handle(self, *args: object, **options: object) -> None:
        repo_root: Path = settings.REPO_ROOT
        ref = str(options["ref"])
        versions_root = Path(str(options["versions_dir"])) if options["versions_dir"] else settings.VERSIONS_DIR

        # The manifest lives at the gh-pages root and is already in the vendored
        # mike format, so we can load it directly.
        try:
            manifest_text = self._git_show(repo_root, f"{ref}:{MANIFEST_NAME}")
        except subprocess.CalledProcessError as exc:
            raise CommandError(
                f"Could not read {MANIFEST_NAME} from '{ref}'. Is the gh-pages branch "
                f"fetched? Try `git fetch origin gh-pages`. ({exc.stderr.strip()})"
            ) from exc
        versions = Versions.loads(manifest_text)

        if options["dry_run"]:
            self.stdout.write(f"Would import {len(versions)} version(s) from '{ref}' into {versions_root}:")
            for info in versions:
                aliases = f"  (aliases: {', '.join(sorted(info.aliases))})" if info.aliases else ""
                self.stdout.write(f"  {info.version!s:<12}{aliases}")
            return

        versions_root.mkdir(parents=True, exist_ok=True)
        imported = 0
        for info in versions:
            version = str(info.version)
            dest = versions_root / version
            # Re-importable: clear any prior copy so a re-run is a clean mirror.
            if dest.exists():
                shutil.rmtree(dest)
            n_files = self._extract_subtree(repo_root, f"{ref}:{version}", dest)

            sha, tag, built_at = self._provenance(repo_root, version, ref)
            write_build_info(
                dest,
                version=version,
                source_sha=sha,
                source_tag=tag,
                builder_version=IMPORTED_BUILDER_VERSION,
                built_at=built_at,
            )
            imported += 1
            self.stdout.write(f"  imported {version:<12} ({n_files} files, tag {tag or '-'})")

        # Normalize and write the manifest through the vendored class (newest-first).
        write_manifest(versions_root, versions)

        # Re-materialize aliases as redirect stubs (gh-pages stored `latest` as a
        # symlink). materialize_alias mirrors every page of the target version.
        for info in versions:
            for alias in sorted(info.aliases):
                count = materialize_alias(versions_root, alias, str(info.version))
                self.stdout.write(f"  alias '{alias}/' -> {info.version} ({count} redirect stubs)")

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} version(s) into {versions_root}"))

    def _git_show(self, repo_root: Path, target: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo_root), "show", target],  # noqa: S607 - `git` from PATH is fine for a dev/CI tool
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def _extract_subtree(self, repo_root: Path, tree_ish: str, dest: Path) -> int:
        """
        Extract a gh-pages subtree (e.g. ``origin/gh-pages:0.151.0``) into ``dest``
        verbatim via ``git archive`` piped through tar. Returns the file count.
        """
        dest.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".tar") as tmp:
            subprocess.run(
                ["git", "-C", str(repo_root), "archive", "--format=tar", tree_ish],  # noqa: S607
                stdout=tmp,
                check=True,
            )
            tmp.flush()
            tmp.seek(0)
            with tarfile.open(tmp.name) as tar:
                members = tar.getmembers()
                # filter="data" rejects path-traversal/symlink members (the
                # extracted tree is trusted gh-pages content, but be safe anyway).
                tar.extractall(dest, filter="data")
        return sum(1 for m in members if m.isfile())

    def _provenance(self, repo_root: Path, version: str, ref: str) -> tuple[str, str | None, str]:
        """
        Resolve (source_sha, source_tag, built_at) for an imported version.

        Prefers the release tag matching the version (tags carry no ``v`` prefix
        in this repo, but try both). Falls back to the gh-pages commit itself for
        versions with no tag (e.g. ``dev``), so the stamp is always populated.
        """
        for candidate in (version, f"v{version}"):
            sha = self._rev_parse(repo_root, f"{candidate}^{{commit}}")
            if sha:
                date = self._commit_date(repo_root, candidate)
                return sha, candidate, date
        # No matching tag (e.g. "dev"): stamp from the gh-pages commit.
        sha = self._rev_parse(repo_root, ref) or ""
        return sha, None, self._commit_date(repo_root, ref)

    def _rev_parse(self, repo_root: Path, rev: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", rev],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.stdout.strip()

    def _commit_date(self, repo_root: Path, rev: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%cI", rev],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.stdout.strip()
