"""
docs-build-all: bootstrap / disaster-recovery rebuild of many versions (5b.8).

Walks the git tags selected by ``docs_versions.toml``, checks each out in a
throwaway git worktree, runs ``docs-build`` against it (writing the snapshot
into docs_site/versions/<version>/), and rewrites versions.json once at the end.
You only run this to bootstrap the version tree or recover a corrupted one; day
to day, each release is a single ``docs-build`` (see DESIGN_spike_7.md section 3).

A tag can only be rebuilt if its checkout contains the docs builder
(docs_site/apps/docs/build/versioning.py). Tags from before the docs-site
migration don't, so they're skipped with a note - rebuilding historical versions
is a deferred decision (spike section 7). The worktree is always removed in a
finally, and stale worktrees are pruned defensively at the start.

Usage:
    cd docs_site
    python manage.py docs_build_all                 # rebuild everything selected
    python manage.py docs_build_all --dry-run       # list what would be built
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pygments_djc  # noqa: F401 -- register the djc_py lexer for the per-tag builds
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.bootstrap import (
    bootstrap_versions,
    load_versions_config,
    needs_rebuild,
    select_tags,
    tag_to_version,
)


def _git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],  # noqa: S607 - `git` from PATH is fine for a dev/CI tool
        capture_output=True,
        text=True,
        check=check,
    )


class Command(BaseCommand):
    help = "Rebuild every version selected by docs_versions.toml into docs_site/versions/."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--config", type=str, default=None, help="Path to docs_versions.toml (default: docs_site/)"
        )
        parser.add_argument(
            "--versions-dir", type=str, default=None, help="Output root (default: settings.VERSIONS_DIR)"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="List selected tags + rebuild status without building"
        )

    def handle(self, *args: object, **options: object) -> None:
        repo_root = settings.REPO_ROOT
        config_path = Path(str(options["config"])) if options["config"] else settings.VERSIONS_CONFIG
        versions_root = Path(str(options["versions_dir"])) if options["versions_dir"] else settings.VERSIONS_DIR

        config = load_versions_config(config_path)
        all_tags = self._all_tags(repo_root)

        if options["dry_run"]:
            self._dry_run(all_tags, config, versions_root, repo_root)
            return

        # Defensive cleanup: a previous interrupted run can leave dangling
        # worktree registrations that would block re-adding the same paths.
        _git(repo_root, "worktree", "prune", check=False)

        build_one = self._make_build_one(repo_root)
        outcome = bootstrap_versions(
            config,
            versions_root=versions_root,
            all_tags=all_tags,
            tag_sha=lambda t: self._tag_sha(repo_root, t),
            build_one=build_one,
            log=self.stdout.write,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(outcome.built)} built, "
                f"{len(outcome.skipped_up_to_date)} up-to-date, "
                f"{len(outcome.skipped_no_builder)} skipped (no builder), "
                f"{len(outcome.failed)} failed"
            )
        )
        if outcome.skipped_no_builder:
            self.stdout.write("Skipped (predate the docs builder): " + ", ".join(outcome.skipped_no_builder))
        if outcome.failed:
            self.stderr.write(self.style.ERROR("Failed: " + ", ".join(outcome.failed)))
            raise SystemExit(1)

    def _all_tags(self, repo_root: Path) -> list[str]:
        return [line for line in _git(repo_root, "tag").stdout.splitlines() if line.strip()]

    def _tag_sha(self, repo_root: Path, tag: str) -> str:
        # ^{commit} dereferences annotated tags to the commit they point at.
        return _git(repo_root, "rev-parse", f"{tag}^{{commit}}").stdout.strip()

    def _dry_run(self, all_tags: list[str], config, versions_root: Path, repo_root: Path) -> None:  # type: ignore[no-untyped-def]
        selected = select_tags(all_tags, config)
        self.stdout.write(f"Would consider {len(selected)} tag(s) (newest first):")
        for tag in selected:
            version = tag_to_version(tag)
            stale = needs_rebuild(versions_root / version, self._tag_sha(repo_root, tag))
            self.stdout.write(f"  {version:<12} {'BUILD' if stale else 'up-to-date'}")

    def _make_build_one(self, repo_root: Path):  # type: ignore[no-untyped-def]
        def build_one(tag: str, version: str, version_dir: Path) -> str:
            tmp_parent = Path(tempfile.mkdtemp(prefix="djc-docs-wt-"))
            worktree = tmp_parent / version
            try:
                _git(repo_root, "worktree", "add", "--detach", str(worktree), tag)
                wt_docs = worktree / "docs_site"
                # Only tags that ship the new builder can be rebuilt; older tags
                # are skipped (historical migration is deferred, spike section 7).
                if (
                    not (wt_docs / "manage.py").is_file()
                    or not (wt_docs / "apps" / "docs" / "build" / "versioning.py").is_file()
                ):
                    return "skipped_no_builder"
                proc = subprocess.run(
                    [  # noqa: S607 - `uv` from PATH is fine for a dev/CI tool
                        "uv",
                        "run",
                        "--project",
                        str(worktree),
                        "python",
                        "manage.py",
                        "build_docs",
                        "--docs-version",
                        version,
                        "--no-manifest-update",
                        "--no-search",
                        "-o",
                        str(version_dir),
                    ],
                    cwd=str(wt_docs),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode != 0:
                    msg = (proc.stderr or proc.stdout)[-600:]
                    raise RuntimeError(f"build_docs exited {proc.returncode}: {msg}")
                return "built"
            finally:
                # Always unregister + delete the worktree, even on failure.
                _git(repo_root, "worktree", "remove", "--force", str(worktree), check=False)
                shutil.rmtree(tmp_parent, ignore_errors=True)

        return build_one
