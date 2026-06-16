"""
Release-notes generator: CHANGELOG.md -> per-release markdown pages.

Port of the old mkdocs gen-files script (docs_old/scripts/gen_release_notes.py)
with mkdocs_gen_files swapped for plain file writes (feature 3b.5).

Pages are generated into a throwaway staging directory at build time and
rendered through the same 3-pass pipeline as regular content - nothing is
committed under content/. The dev server generates them on demand into a
cached temp dir so /releases/ URLs work in live preview too.

Spec: docs_site/design/DESIGN_spike_9.md section 2.1.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Release:
    slug: str  # filename/URL-safe version, e.g. "v0.140.0"
    title: str  # display title, e.g. "🚨📢 v0.140.0 (2024-09-11)"
    body: str  # markdown body without the "## vX.Y.Z" header line


# A release may carry its date in the body as an italic line. We accept the
# long-standing "_11 Sep 2024_" form and also ISO "_2024-09-11_"; both render in
# the title as ISO. Tried in order, first match wins.
_DATE_FORMATS = (
    (re.compile(r"_(\d{1,2}\s+\w{3}\s+\d{4})_"), "%d %b %Y"),
    (re.compile(r"_(\d{4}-\d{2}-\d{2})_"), "%Y-%m-%d"),
)


def parse_changelog(changelog_path: Path) -> list[Release]:
    """Split CHANGELOG.md into one Release per "## vX.Y.Z" section."""
    content = changelog_path.read_text(encoding="utf-8")

    # Positive lookahead keeps each "## ..." header at the start of its chunk.
    chunks = re.split(r"(?=^##\s+)", content, flags=re.MULTILINE)

    releases: list[Release] = []
    # chunks[0] is the "# Release notes" preamble before the first version.
    for chunk in chunks[1:]:
        stripped = chunk.strip()
        header_line, _, body = stripped.partition("\n")
        body = body.strip()

        # Pull the release date (if any) out of the body and into the title.
        parsed_date = None
        for pattern, fmt in _DATE_FORMATS:
            date_match = pattern.search(body)
            if date_match:
                parsed_date = datetime.strptime(date_match.group(1), fmt)  # noqa: DTZ007 -- date-only, no tz in source
                body = body.replace(date_match.group(0), "").strip()
                break

        # Full header text, e.g. "🚨📢 v0.140.0"
        title = header_line.removeprefix("##").strip()

        # Clean version string for the filename/URL, e.g. "v0.140.0"
        # (drops emojis, whitespace, and other non-alphanumeric chars).
        slug = re.sub(r"[^a-zA-Z0-9.\-_]", "", title)
        if not slug.startswith("v"):
            slug = "v" + slug

        if parsed_date is not None:
            title += f" ({parsed_date.strftime('%Y-%m-%d')})"

        releases.append(Release(slug=slug, title=title, body=body))

    return releases


def generate_release_notes(changelog_path: Path, target_dir: Path) -> list[Path]:
    """
    Write docs/releases/<slug>.md per release + an index.md into target_dir.

    Returns the written paths. Pages carry their title as the H1 (the pipeline
    extracts <title> from the H1), and the index links use clean URLs so no
    .md link rewriting is needed.
    """
    releases = parse_changelog(changelog_path)
    # Release notes live under the /docs/ section (spike 11.11 sections 4.2-4.3)
    releases_dir = target_dir / "docs" / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for release in releases:
        page_path = releases_dir / f"{release.slug}.md"
        page_path.write_text(f"# {release.title}\n\n{release.body}\n", encoding="utf-8")
        written.append(page_path)

    index_lines = [
        "# Release notes",
        "",
        "Here you can find the release notes for all versions of Django-Components.",
        "",
    ]
    # Relative clean URL: "v0.140.0/" resolves to /releases/v0.140.0/
    index_lines.extend(f"* [{release.title}]({release.slug}/)" for release in releases)
    index_path = releases_dir / "index.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    written.append(index_path)

    return written


# Dev-server cache: (changelog mtime, staging dir). The staging dir is
# regenerated whenever CHANGELOG.md changes on disk.
_staging_cache: tuple[float, Path] | None = None


def get_release_staging_dir(changelog_path: Path) -> Path:
    """Generate (and cache) the release pages for the dev server's live preview."""
    global _staging_cache  # noqa: PLW0603 -- module-level cache for the dev server

    mtime = changelog_path.stat().st_mtime
    if _staging_cache is not None and _staging_cache[0] == mtime and _staging_cache[1].is_dir():
        return _staging_cache[1]

    # resolve() because gettempdir() may be a symlink (e.g. /var -> /private/var
    # on macOS), while url_to_md compares fully-resolved paths
    staging = (Path(tempfile.gettempdir()) / "djc-docs-releases").resolve()
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    generate_release_notes(changelog_path, staging)
    _staging_cache = (mtime, staging)
    return staging
