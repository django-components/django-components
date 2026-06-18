"""
URL <-> content-file path mapping.

Shared by the build command (markdown file -> output HTML path / URL) and the
dev view (incoming URL -> source markdown file), so both stay consistent.

Slug convention:
    foo.md         -> /foo/   (output: foo/index.html)
    bar/index.md   -> /bar/   (output: bar/index.html)
    index.md       -> /       (output: index.html)
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings


def md_to_html_path(output_dir: Path, rel: Path) -> Path:
    """Output HTML path for a content markdown file (relative to content dir)."""
    if rel.stem == "index":
        return output_dir / rel.parent / "index.html"
    return output_dir / rel.with_suffix("") / "index.html"


def md_companion_path(output_dir: Path, rel: Path) -> Path:
    """Output .md companion path - same slug logic as the HTML file."""
    if rel.stem == "index":
        return output_dir / rel.parent / "index.md"
    return output_dir / rel.with_suffix("") / "index.md"


def md_to_url(rel: Path) -> str:
    """Clean URL path for a content markdown file (e.g. 'foo/' or 'bar/baz/')."""
    if rel.stem == "index":
        parent = str(rel.parent)
        return parent + "/" if parent != "." else ""
    return str(rel.with_suffix("")) + "/"


def edit_url_for(md_path: Path) -> str:
    """
    GitHub "edit this page" URL for a content source file, or "" if it has none.

    Only real content pages (under the repo) get a link. Generated pages
    (release notes, API reference, examples index) are rendered from a temp
    staging dir outside the repo, so relative_to() raises and they correctly
    get no edit link.
    """
    try:
        rel = md_path.relative_to(settings.REPO_ROOT)
    except ValueError:
        return ""
    repo_url = str(settings.REPO_URL).strip("/ ")
    return f"{repo_url}/edit/{settings.SOURCE_CODE_GIT_BRANCH}/{rel.as_posix()}"


def url_to_md(content_dir: Path, url_path: str) -> Path | None:
    """
    Resolve an incoming URL path to a source markdown file, or None if not found.

    Reverse of md_to_url. Tries both the flat form (foo -> foo.md) and the
    directory-index form (foo -> foo/index.md). Guards against path traversal
    outside the content directory.
    """
    clean = url_path.strip("/")
    if not clean:
        candidates = ["index.md"]
    else:
        candidates = [f"{clean}.md", f"{clean}/index.md"]

    base = content_dir.resolve()
    for rel in candidates:
        candidate = (base / rel).resolve()
        # Reject paths that escape the content directory (e.g. via "../")
        if not candidate.is_relative_to(base):
            continue
        if candidate.is_file():
            return candidate
    return None
