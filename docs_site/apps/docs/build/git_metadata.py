"""
Per-page git metadata (last-updated date + authors).

Replaces the mkdocs `git-revision-date-localized` and `git-authors` plugins
with one `git log` subprocess call per page (feature 3b.24). The DocPage
footer renders the result.

The data comes from the commit history, so CI checkouts must be full clones -
set `fetch-depth: 0` on actions/checkout in the docs workflows, otherwise a
shallow clone makes every page report the checkout commit as its last update.

Spec: docs_site/design/DESIGN_spike_9.md section 2.3.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatch
from functools import cache
from pathlib import Path

# Pages where "last modified" has no meaningful semantics. Matches the
# exclusions in the old mkdocs.yml plugin config, plus the generated
# release-notes pages. Patterns match the content-relative posix path.
EXCLUDE_PATTERNS = (
    "docs/reference/*",
    "docs/releases/*",
    "docs/community/code_of_conduct.md",
    "docs/overview/license.md",
)

# Cap matches the old git-authors behavior; avoids footer clutter on old pages.
MAX_AUTHORS = 5


@dataclass(frozen=True)
class PageGitMeta:
    last_updated: datetime | None
    # First-commit date: the page's creation time, used as JSON-LD datePublished.
    created: datetime | None
    authors: tuple[str, ...]


EMPTY_META = PageGitMeta(last_updated=None, created=None, authors=())


def is_excluded(rel_path: Path) -> bool:
    """True for content pages that shouldn't show git metadata."""
    posix = rel_path.as_posix()
    return any(fnmatch(posix, pattern) for pattern in EXCLUDE_PATTERNS)


@cache
def get_page_git_meta(repo_root: Path, page_path: Path) -> PageGitMeta:
    """
    Return the last-updated timestamp and author list for a file.

    Authors are unique, most-recent-first, capped at MAX_AUTHORS. Returns
    EMPTY_META for files with no git history (new/untracked files, generated
    pages in temp dirs) or when git is unavailable (e.g. tarball builds).
    """
    try:
        rel = page_path.relative_to(repo_root)
    except ValueError:
        return EMPTY_META

    # One subprocess per page: newest-first "date<TAB>author" rows.
    # --follow keeps history across renames (docs files move around a lot).
    try:
        proc = subprocess.run(
            ["git", "log", "--follow", "--format=%cI%x09%an", "--", rel.as_posix()],  # noqa: S607
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return EMPTY_META

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return EMPTY_META

    # Rows are newest-first, so lines[0] is the latest commit and lines[-1] the
    # first (the page's creation).
    last_updated = datetime.fromisoformat(lines[0].split("\t", 1)[0])
    created = datetime.fromisoformat(lines[-1].split("\t", 1)[0])
    # dict.fromkeys dedups while preserving the newest-first order
    authors = dict.fromkeys(line.split("\t", 1)[1] for line in lines if "\t" in line)
    return PageGitMeta(last_updated=last_updated, created=created, authors=tuple(list(authors)[:MAX_AUTHORS]))
