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
    boost:       Search-ranking multiplier (>1 ranks the page higher, <1 lower);
                 emitted as data-pagefind-weight. Default 1.0 (no boost).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import frontmatter

KNOWN_FIELDS = frozenset({"title", "description", "og_image", "noindex", "canonical", "tags", "boost"})

# Pagefind's neutral page weight; pages with this value emit no weight attribute.
DEFAULT_BOOST = 1.0

# Matches the opening of a fenced code block (used to skip H1s inside fences)
_FENCE_OPEN = re.compile(r"^(\s*)(```+|~~~+)")

# Matches the first "real" paragraph - skips headings, admonitions, blockquotes,
# tables, fences, task lists, tabbed blocks, collapsible details, and bold labels
_FIRST_PARAGRAPH = re.compile(
    r"(?:^|\n\n)"
    r"(?!#|!|>|\||```|-\s\[|={3}|\?{3}|\*{3})"
    r"([^\n]+(?:\n(?!#|\n)[^\n]+)*)",
)

# Version-change annotations (e.g. "_New in version 0.89_") are standalone
# italic paragraphs that often precede the first real prose. They make a useless
# meta/OG description ("New in version 0.89"), so the extractor skips them and
# walks to the next paragraph. Matched after inline formatting is stripped.
_VERSION_ANNOTATION = re.compile(r"^(New|Changed|Deprecated|Removed) in version\b", re.IGNORECASE)


@dataclass
class PageMeta:
    title: str = ""
    description: str = ""
    og_image: str = ""
    noindex: bool = False
    canonical: str = ""
    tags: list[str] = field(default_factory=list)
    boost: float = DEFAULT_BOOST
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
        boost=float(meta.get("boost", DEFAULT_BOOST)),
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

    Walks candidate paragraphs in order, skipping ones that make a useless
    description - version-change annotations ("New in version ..."), raw HTML
    (tags/comments), and snippet-include directives ("--8<-- ...") - and returns
    the first prose paragraph. Strips markdown formatting (links, bold, italic,
    code) and caps at 155 chars (the typical search-engine snippet length).
    """
    for m in _FIRST_PARAGRAPH.finditer(body):
        raw = m.group(1).strip()
        # Raw HTML (e.g. "<img ...>", "<!-- ... -->") and snippet directives
        # ("--8<-- \"LICENSE\"") are not prose; skip to the next paragraph.
        if raw.startswith(("<", "--8<--")):
            continue
        text = _strip_inline_formatting(raw)
        if not text or _VERSION_ANNOTATION.match(text):
            continue
        if len(text) > 155:
            text = text[:152].rsplit(" ", 1)[0] + "..."
        return text
    return ""


def _strip_inline_formatting(text: str) -> str:
    """Reduce markdown inline syntax to plain text (links, bold/italic, code)."""
    # Drop images entirely - their alt text isn't useful description prose
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # Drop now-empty link shells, e.g. badge links [![alt](img)](url) once the
    # inner image is gone leave "[](url)"
    text = re.sub(r"\[\]\([^)]*\)", "", text)
    # Reference cross-refs [text][Key] -> text (the autoref form used in docstrings)
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    # Inline links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Strip code/bold/asterisk-italic markers
    text = re.sub(r"[`*]", "", text)
    # Strip emphasis underscores but keep snake_case identifiers (django_components)
    # intact: protect any underscore flanked by word chars, drop the rest, restore.
    text = re.sub(r"(?<=\w)_(?=\w)", "\x00", text)
    return text.replace("_", "").replace("\x00", "_").strip()
