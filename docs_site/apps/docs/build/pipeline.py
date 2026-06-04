"""
Three-pass markdown rendering pipeline.

The pipeline converts a markdown source file into a complete HTML page:

    Pre-pass: Fence protection wraps code blocks in {% verbatim %} so Django
              doesn't execute template tags inside documentation examples.
    Pass 1:   Django template engine expands all tags ({% version %},
              {% component %}, {% example %}, etc.) in the markdown source.
    Pass 2:   python-markdown + pymdownx extensions convert the expanded
              markdown to HTML (syntax highlighting, admonitions, TOC, etc.).
    Pass 3:   DocPage component wraps the content HTML in a full page layout
              with <head> metadata, CSS, and page chrome.

The pipeline also captures the post-Pass-1 expanded markdown for use as
.md companion files (raw markdown served alongside HTML for LLM ingestion).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import markdown  # type: ignore[import-untyped]  # python-markdown ships no stubs
from django.conf import settings
from django.template import Context, Engine
from pymdownx.slugs import slugify

from .fence_protection import protect_fences, reset_counter
from .frontmatter import PageMeta, parse_page
from .links import rewrite_internal_md_links

if TYPE_CHECKING:
    from pathlib import Path

    from .nav import NavTree

# Extension set matches the current mkdocs.yml config (minus mkdocs-only plugins).
# These plug into python-markdown directly and don't depend on mkdocs.
MD_EXTENSIONS = [
    "abbr",
    "admonition",
    "attr_list",
    "def_list",
    "tables",
    "md_in_html",  # lets block-level HTML from Pass 1 pass through Pass 2 untouched
    "toc",
    "pymdownx.details",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "pymdownx.snippets",  # --8<-- "path" file inclusion
    "pymdownx.superfences",
    "pymdownx.tabbed",
    "pymdownx.tasklist",
]

MD_EXTENSION_CONFIGS: dict[str, dict[str, Any]] = {
    "pymdownx.highlight": {"anchor_linenums": True},
    "pymdownx.snippets": {"check_paths": True, "base_path": ["."]},
    "pymdownx.tabbed": {"alternate_style": True},
    "pymdownx.tasklist": {"custom_checkbox": True},
    # Match Material's slug algorithm so heading anchors are identical
    "toc": {"permalink": "¤", "slugify": slugify(case="lower")},
}


@dataclass
class RenderResult:
    html: str
    toc_tokens: list
    meta: PageMeta
    # The markdown after Pass 1 (Django expansion) but before Pass 2 (HTML conversion).
    # Used to generate .md companion files for LLM consumption.
    expanded_markdown: str


def render_page(
    source: str,
    *,
    engine: Engine | None = None,
    context: dict[str, Any] | None = None,
    source_path: Path | None = None,
    content_dir: Path | None = None,
    wrap_in_layout: bool = True,
    nav_tree: NavTree | None = None,
    current_path: str = "",
) -> RenderResult:
    """
    Run the full 3-pass pipeline on a markdown source string.

    When content_dir is given (and source_path is under it), internal `.md`
    links in the rendered HTML are rewritten to clean URLs.
    """
    reset_counter()

    # Extract YAML front-matter (title, description, etc.) and separate the body
    meta = parse_page(source)

    # Allow the build context to provide a canonical URL when front-matter doesn't
    if context and context.get("canonical") and not meta.canonical:
        meta.canonical = context["canonical"]

    # Pre-pass: protect code fences from Django template execution
    protected = _pass0_fence_protect(meta.body)

    # Pass 1: expand Django template tags ({% version %}, {% component %}, etc.)
    expanded = _pass1_django(protected, engine=engine, context=context or {})

    # Pass 2: convert markdown to HTML (Pygments highlighting, admonitions, TOC, etc.)
    content_html, toc_tokens = _pass2_markdown(expanded, source_path=source_path)

    # Rewrite internal .md links to clean URLs (e.g. ./other.md -> ../other/)
    if content_dir is not None and source_path is not None:
        content_html = rewrite_internal_md_links(content_html, source_path=source_path, content_dir=content_dir)

    # Pass 3: wrap in DocPage layout (full HTML page with <head>, CSS, chrome)
    if wrap_in_layout:
        page_html = _pass3_layout(
            content_html,
            meta=meta,
            context=context or {},
            nav_tree=nav_tree,
            current_path=current_path,
            toc_tokens=toc_tokens,
        )
    else:
        page_html = content_html

    return RenderResult(
        html=page_html,
        toc_tokens=toc_tokens,
        meta=meta,
        expanded_markdown=expanded,
    )


def _pass0_fence_protect(source: str) -> str:
    return protect_fences(source)


def _pass1_django(
    source: str,
    *,
    engine: Engine | None = None,
    context: dict[str, Any],
) -> str:
    if engine is None:
        engine = Engine.get_default()

    # Auto-load our docs template tags and django-components tags
    # so authors can use {% version %}, {% component %}, etc. in markdown
    preamble = "{% load docs_extras component_tags %}\n"
    template = engine.from_string(preamble + source)
    return template.render(Context(context))


def _pass2_markdown(
    source: str,
    *,
    source_path: Path | None = None,
) -> tuple[str, list]:
    configs = dict(MD_EXTENSION_CONFIGS)

    # Snippet paths (--8<-- "path") resolve relative to both the source file's
    # directory and the repo root, so includes like "docs/examples/foo/component.py" work
    base_paths = [str(settings.REPO_ROOT)]
    if source_path is not None:
        base_paths.insert(0, str(source_path.parent))
    configs = {
        **configs,
        "pymdownx.snippets": {
            **configs.get("pymdownx.snippets", {}),
            "base_path": base_paths,
        },
    }

    md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=configs)
    html = md.convert(source)
    toc_tokens = getattr(md, "toc_tokens", [])
    return html, toc_tokens


def _pass3_layout(
    content_html: str,
    *,
    meta: PageMeta,
    context: dict[str, Any],
    nav_tree: NavTree | None = None,
    current_path: str = "",
    toc_tokens: list | None = None,
) -> str:
    # Lazy import to avoid circular imports at module level
    from apps.docs.components.doc_page.doc_page import DocPage  # noqa: PLC0415

    return DocPage.render(
        kwargs={
            "content_html": content_html,
            "title": meta.title,
            "description": meta.description,
            "canonical": meta.canonical,
            "noindex": meta.noindex,
            "version": context.get("version", ""),
            "nav_tree": nav_tree,
            "current_path": current_path,
            "toc_items": toc_tokens,
        },
    )
