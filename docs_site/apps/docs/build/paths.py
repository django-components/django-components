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
