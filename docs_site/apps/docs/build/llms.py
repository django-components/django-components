"""
Post-build AI index files: /llms.txt and /llms-full.txt.

`llms.txt` is the [llmstxt.org](https://llmstxt.org/) convention - a short,
nav-ordered markdown table of contents an AI agent can fetch in one shot.
`llms-full.txt` concatenates every page's markdown so a model can ingest the
whole site at once.

Both are built from artifacts the page build already produced: the nav tree
(`_nav.yml`) for ordering, and the per-page `.md` companions (front-matter +
fully expanded markdown - Django tags like `{% example %}` / `{% docstring %}` /
`{% include_file %}` and pymdownx `--8<--` file includes are all resolved; see
pipeline.expand_snippets). `parse_page()` on a companion yields its title,
description, and front-matter-stripped body in one call.

Like the crawl files (see seo.py), these are site-root artifacts, generated for
the current-version build (preview mode), which IS the deployed latest site.
They need the `.md` companions, so they're skipped when companions are disabled.

Spec: docs_site/design/DESIGN_spike_12.md section 3.B.1 (feature 5c.10).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.docs.build.frontmatter import PageMeta, parse_page

if TYPE_CHECKING:
    from pathlib import Path

    from apps.docs.build.nav import NavTree

# Standalone nav sections (a landing page, no children) are listed under the
# llms.txt "Optional" heading per the convention (lower-priority links). "Home"
# is the title/blockquote source and is dropped from the body entirely.
_TITLE_SECTION = "Home"


def generate_llms_files(content_dir: Path, output_dir: Path, nav_tree: NavTree, *, site_url: str) -> tuple[int, int]:
    """
    Write llms.txt and llms-full.txt into a built site.

    Returns (llms_txt_links, llms_full_pages). llms-full.txt is skipped (0) when
    the `.md` companions are absent (e.g. a --no-companions build).
    """
    base = site_url.rstrip("/")
    links = write_llms_txt(output_dir, nav_tree, site_url=base)
    pages = write_llms_full_txt(output_dir, nav_tree, site_url=base)
    return links, pages


def _companion_meta(output_dir: Path, path: str) -> PageMeta | None:
    """Parse the `.md` companion backing a clean URL path, or None if it's missing."""
    companion = output_dir / path.strip("/") / "index.md"
    if not companion.is_file():
        return None
    return parse_page(companion.read_text(encoding="utf-8"))


def _bullet(title: str, path: str, output_dir: Path, site_url: str) -> str:
    """One llms.txt list entry: `- [Title](url): description` (description optional)."""
    meta = _companion_meta(output_dir, path)
    desc = meta.description if meta else ""
    entry = f"- [{title}]({site_url}{path})"
    return f"{entry}: {desc}" if desc else entry


def write_llms_txt(output_dir: Path, nav_tree: NavTree, *, site_url: str) -> int:
    """Write the llms.txt nav index. Returns the number of link entries."""
    home = _companion_meta(output_dir, "/")
    title = (home.title if home and home.title else "Django Components").strip()
    summary = home.description if home and home.description else ""

    lines = [f"# {title}", ""]
    if summary:
        lines += [f"> {summary}", ""]

    optional: list[tuple[str, str]] = []
    count = 0
    for section in nav_tree.sections:
        if section.label == _TITLE_SECTION:
            continue
        # A section that's just a landing page (no children) is an "Optional" link.
        if section.path and not section.items and not section.groups:
            optional.append((section.label, section.path))
            continue

        lines += [f"## {section.label}", ""]
        # The section's own landing page (e.g. the API Reference index), if any.
        if section.path:
            lines.append(_bullet(f"{section.label} overview", section.path, output_dir, site_url))
            count += 1
        # Sections hold EITHER items OR groups; flatten group items into the list.
        items = list(section.items) + [it for group in section.groups for it in group.items]
        for item in items:
            lines.append(_bullet(item.title, item.path, output_dir, site_url))
            count += 1
        lines.append("")

    if optional:
        lines += ["## Optional", ""]
        for label, path in optional:
            lines.append(_bullet(label, path, output_dir, site_url))
            count += 1
        lines.append("")

    (output_dir / "llms.txt").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return count


def write_llms_full_txt(output_dir: Path, nav_tree: NavTree, *, site_url: str) -> int:
    """Write the full-content llms-full.txt. Returns the number of pages concatenated."""
    blocks: list[str] = []
    for item in nav_tree.flat_pages():
        meta = _companion_meta(output_dir, item.path)
        if meta is None:
            continue  # no companion (page failed to build, or companions disabled)
        heading = item.title or meta.title or item.path
        blocks.append(f"# {heading}\n\nSource: {site_url}{item.path}\n\n{meta.body.strip()}")

    if not blocks:
        return 0
    # A horizontal rule between pages keeps boundaries clear for a reading model.
    (output_dir / "llms-full.txt").write_text("\n\n---\n\n".join(blocks) + "\n", encoding="utf-8")
    return len(blocks)
