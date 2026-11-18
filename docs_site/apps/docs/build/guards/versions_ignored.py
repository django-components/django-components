"""
Fails when `git add` would skip a file under docs_site/versions/.

`git add docs_site/versions/` silently skips any file that a .gitignore rule matches
and still succeeds for the other files. A release run would then commit a snapshot
with pages missing, and the deploy would serve 404s for them. This guard lists the
files git would skip, so `docs_versions_check` fails before the release workflow
commits. It asks git for its own ignore rules, so it matches what `git add` does.

Runs only when ``ctx.versions_root`` is set (the docs_versions_check command). It
does nothing when git is missing or the tree is not inside a git work tree, such as
a source archive.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator

from .base import GuardContext, GuardResult

# How many ignored paths the message names; the count covers the rest.
_MAX_LISTED = 5


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    root = ctx.versions_root
    if root is None or not root.is_dir():
        return

    try:
        proc = subprocess.run(
            # --others --ignored lists untracked files that a .gitignore rule matches, the
            # same ones `git add` leaves out. Tracked files are already committed.
            ["git", "-C", str(root), "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", "."],  # noqa: S607 - `git` from PATH is fine for a dev/CI tool
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return
    # A non-zero exit usually means this is not a git work tree. Skip, because there
    # are no ignore rules to compare against.
    if proc.returncode != 0:
        return

    ignored = [path for path in proc.stdout.split("\0") if path]
    if not ignored:
        return
    listed = ", ".join(ignored[:_MAX_LISTED])
    more = f" and {len(ignored) - _MAX_LISTED} more" if len(ignored) > _MAX_LISTED else ""
    yield GuardResult.error(
        guard="versions_ignored",
        message=(
            f"{len(ignored)} file(s) under docs_site/versions/ match a .gitignore rule, so `git add` would "
            f"leave them out of the commit (paths relative to that folder): {listed}{more}. "
            "Re-include them with `!docs_site/versions/**` as the last line of .gitignore."
        ),
        source=ignored[0],
    )
