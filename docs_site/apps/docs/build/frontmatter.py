"""
Front-matter parsing and validation for docs pages.

Extracts YAML front-matter from the top of markdown files and derives
metadata (title, description) from the content when front-matter doesn't
provide them. The fallback chain for each field:

    title:       front-matter "title:" > first # H1 in body > empty
    description: front-matter "description:" > first paragraph of body > empty

Schema fields (all optional):
    title:       Override the H1-derived title
    description: Per-page meta description (155 char cap recommended)
    og_image:    Custom OG image path
    noindex:     If true, emit <meta name="robots" content="noindex,follow">
    canonical:   Override the auto-computed canonical URL
    tags:        List of string tags (reserved for future taxonomy)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import frontmatter

KNOWN_FIELDS = frozenset({"title", "description", "og_image", "noindex", "canonical", "tags"})

# Matches the opening of a fenced code block (used to skip H1s inside fences)
_FENCE_OPEN = re.compile(r"^(\s*)(```+|~~~+)")

# Matches the first "real" paragraph - skips headings, admonitions, blockquotes,
# tables, fences, task lists, tabbed blocks, collapsible details, and bold labels
_FIRST_PARAGRAPH = re.compile(
    r"(?:^|\n\n)"
    r"(?!#|!|>|\||```|-\s\[|={3}|\?{3}|\*{3})"
    r"([^\n]+(?:\n(?!#|\n)[^\n]+)*)",
)


@dataclass
class PageMeta:
    title: str = ""
    description: str = ""
    og_image: str = ""
    noindex: bool = False
    canonical: str = ""
    tags: list[str] = field(default_factory=list)
    # The markdown body with front-matter stripped
    body: str = ""


def parse_page(source: str, *, strict: bool = False) -> PageMeta:
    """
    Parse YAML front-matter and derive metadata from a markdown source.

    In strict mode, unknown front-matter fields raise ValueError (used by CI guardrails).
    """
    post = frontmatter.loads(source)
    meta: dict[str, Any] = dict(post.metadata)
    body: str = post.content

    if strict:
        unknown = set(meta.keys()) - KNOWN_FIELDS
        if unknown:
            raise ValueError(f"Unknown front-matter fields: {', '.join(sorted(unknown))}")

    # Title: front-matter > first H1 in body (skipping H1s inside code fences)
    title = str(meta.get("title", ""))
    if not title:
        title = _extract_first_h1(body)

    # Description: front-matter > first paragraph (stripped of markdown formatting)
    description = str(meta.get("description", ""))
    if not description:
        description = _extract_first_paragraph(body)

    return PageMeta(
        title=title,
        description=description,
        og_image=str(meta.get("og_image", "")),
        noindex=bool(meta.get("noindex", False)),
        canonical=str(meta.get("canonical", "")),
        tags=list(meta.get("tags", [])),
        body=body,
    )


def _extract_first_h1(body: str) -> str:
    """
    Find the first # H1 heading that's NOT inside a fenced code block.

    Naive regex search would match H1-like lines in code examples (e.g.
    `# This is a Python comment`), producing wrong titles.
    """
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line in body.splitlines():
        if not in_fence:
            m = _FENCE_OPEN.match(line)
            if m:
                marker = m.group(2)
                fence_char = marker[0]
                fence_len = len(marker)
                in_fence = True
                continue
            stripped = line.strip()
            # Match "# Title" but not "## Subtitle"
            if stripped.startswith("# ") and not stripped.startswith("## "):
                return stripped[2:].strip()
        else:
            # Check for fence close
            stripped = line.lstrip()
            if stripped.startswith(fence_char * fence_len) and not stripped.startswith(fence_char * (fence_len + 1)):
                in_fence = False
    return ""


def _extract_first_paragraph(body: str) -> str:
    """
    Extract the first real paragraph from markdown body for use as meta description.

    Strips markdown formatting (links, bold, backticks) and caps at 155 chars
    (the typical search-engine snippet length).
    """
    m = _FIRST_PARAGRAPH.search(body)
    if not m:
        return ""
    text = m.group(1).strip()
    # Strip markdown link syntax [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Strip inline formatting markers
    text = re.sub(r"[`*_]", "", text)
    if len(text) > 155:
        text = text[:152].rsplit(" ", 1)[0] + "..."
    return text
