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

from .fence_protection import protect_fences, reset_counter
from .frontmatter import PageMeta, parse_page
from .links import linkify_headings, mark_external_links, rewrite_internal_md_links
from .toc import merge_html_headings_into_toc

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
    "pymdownx.magiclink",  # bare-URL autolinking + #123 / user/repo issue shorthand
    "pymdownx.snippets",  # --8<-- "path" file inclusion
    "pymdownx.superfences",
    "pymdownx.tabbed",
    "pymdownx.tasklist",
]

MD_EXTENSION_CONFIGS: dict[str, dict[str, Any]] = {
    # anchor_linenums is intentionally OFF: line numbers aren't displayed
    # (no `linenums`), so it would only emit an empty `<a href id name>` per code
    # line - thousands of invisible, unreferenced links that fail Lighthouse's
    # "links do not have a discernible name" a11y audit for zero benefit (nothing
    # deep-links to a code line). Leaving it off removes that whole class.
    "pymdownx.highlight": {"anchor_linenums": False},
    "pymdownx.magiclink": {
        "repo_url_shorthand": True,
        "user": "django-components",
        "repo": "django-components",
    },
    "pymdownx.snippets": {"check_paths": True, "base_path": ["."]},
    "pymdownx.tabbed": {"alternate_style": True},
    "pymdownx.tasklist": {"custom_checkbox": True},
    # Heading anchors must match the deployed mkdocs site, which used
    # python-markdown's DEFAULT toc slugify (mkdocs.yml set only the permalink).
    # pymdownx.slugs.slugify is NOT compatible: it keeps whitespace runs as
    # double hyphens ("default-js--css-locations") where the default collapses
    # them ("default-js-css-locations"), breaking every inbound anchor link.
    "toc": {"permalink": "¤"},
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

    # Title fallback chain: front-matter > H1 (both handled by parse_page) >
    # nav title. Most ported pages have neither front-matter nor an H1; the
    # old mkdocs site took their titles from awesome-nav the same way.
    if not meta.title and nav_tree is not None:
        meta.title = nav_tree.find_title(current_path)

    # Pre-pass: protect code fences from Django template execution
    protected = _pass0_fence_protect(meta.body)

    # Pass 1: expand Django template tags ({% version %}, {% component %}, etc.).
    # Expose the page's clean URL so tags like {% docstring %} can build links
    # relative to the current page.
    pass1_context = {**(context or {}), "current_path": current_path}
    expanded = _pass1_django(protected, engine=engine, context=pass1_context)

    # Resolve `[text][Key]` bracket cross-refs to real relative links (the analog
    # of the old mkdocstrings autorefs), skipping fenced code. This covers every
    # page: content prose, generated reference prefaces, and any `[x][y]` left in
    # Pass-1 output (docstring *bodies* resolve their own refs inside Pass 1). The
    # .md companion keeps the source `[x][y]` form.
    from apps.docs.reference.crossrefs import resolve_crossrefs_in_prose  # noqa: PLC0415

    resolved_md, _unresolved = resolve_crossrefs_in_prose(expanded, current_url=current_path)

    # Pass 2: convert markdown to HTML (Pygments highlighting, admonitions, TOC, etc.)
    content_html, toc_tokens = _pass2_markdown(resolved_md, source_path=source_path)

    # Rewrite internal .md links to clean URLs (e.g. ./other.md -> ../other/)
    if content_dir is not None and source_path is not None:
        content_html = rewrite_internal_md_links(content_html, source_path=source_path, content_dir=content_dir)

    # Off-site links open in a new tab (runs on content only; chrome links in
    # Pass 3 already set their own target where needed)
    content_html = mark_external_links(content_html)

    # Fold raw-HTML headings (e.g. API reference symbols, which bypass the
    # markdown toc extension) into the TOC so they reach the right-rail + scroll-spy.
    toc_tokens = merge_html_headings_into_toc(content_html, toc_tokens)

    # Make the whole heading the permalink (not just the trailing ¤). After the
    # TOC merge so it reads the original heading markup for labels.
    content_html = linkify_headings(content_html)

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
        # The companion (.md) and llms-full.txt are built from this, so resolve
        # `--8<--` includes here too (Pass 2 only resolved them in the HTML).
        expanded_markdown=expand_snippets(expanded),
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

    # Snippet paths (--8<-- "path") resolve against the repo root ONLY, same
    # as the old mkdocs config (base_path: .). Do NOT add the source file's
    # dir: on case-insensitive filesystems (macOS) a root-relative include
    # like "CODE_OF_CONDUCT.md" then resolves to the including page itself
    # (community/code_of_conduct.md), and pymdownx's self-inclusion guard
    # silently produces an empty page.
    base_paths = [str(settings.REPO_ROOT)]
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


def expand_snippets(source: str) -> str:
    """
    Inline pymdownx `--8<--` file includes, returning markdown (not HTML).

    Pass 2 expands these when converting to HTML, but the `.md` companions (and
    the llms-full.txt built from them) are taken from the Pass-1 output, where
    the directives are still literal. Running just the snippet *preprocessor*
    here - with the same repo-root base path Pass 2 uses - resolves them in place
    so includes like `--8<-- "LICENSE"` appear as content, not as a raw directive.

    This mirrors Pass 2 exactly, so the companion matches the rendered page. Note
    that (like Pass 2, where snippets run as a preprocessor before fence parsing)
    a `--8<--` inside a ``` code fence is still expanded, not shown literally.
    """
    if "--8<--" not in source:
        return source  # fast path: nothing to expand
    configs = {"pymdownx.snippets": {"check_paths": True, "base_path": [str(settings.REPO_ROOT)]}}
    md = markdown.Markdown(extensions=["pymdownx.snippets"], extension_configs=configs)
    return "\n".join(md.preprocessors["snippet"].run(source.split("\n")))


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

    # Per-page git metadata (last-updated + authors) for the footer, if the
    # build provided it (see build/git_metadata.py)
    git_meta = context.get("git_meta")

    return DocPage.render(
        kwargs={
            "content_html": content_html,
            "title": meta.title,
            "description": meta.description,
            "canonical": meta.canonical,
            "noindex": meta.noindex,
            "boost": meta.boost,
            "version": context.get("version", ""),
            "nav_tree": nav_tree,
            "current_path": current_path,
            "toc_items": toc_tokens,
            "last_updated": git_meta.last_updated if git_meta else None,
            "created": git_meta.created if git_meta else None,
            "authors": list(git_meta.authors) if git_meta else [],
            "og_image": _resolve_og_image(meta.og_image),
            "edit_url": context.get("edit_url", ""),
        },
    )


# Site-level fallback OG image. Pages render with this; build/social_cards.py
# rewrites og:image/twitter:image to the per-page 1200x630 PNG where one was
# generated, leaving this valid default in place otherwise (so it never 404s).
DEFAULT_OG_IMAGE_PATH = "/static/img/favicon.png"


def default_og_image_url() -> str:
    """Absolute URL of the site-level fallback OG image (the social-card rewrite target)."""
    return f"{str(settings.SITE_URL).rstrip('/')}{DEFAULT_OG_IMAGE_PATH}"


def _resolve_og_image(og_image: str) -> str:
    """
    Resolve the page's OG/Twitter card image to an absolute URL.

    Uses the front-matter `og_image` when set (absolute URL kept as-is, otherwise
    treated as a site-root-relative path). Falls back to the site-level default,
    which the social-card build step (build/social_cards.py) later swaps for the
    page's generated 1200x630 card when one exists.
    """
    site_root = str(settings.SITE_URL).rstrip("/")
    if not og_image:
        return default_og_image_url()
    if og_image.startswith(("http://", "https://")):
        return og_image
    return f"{site_root}/{og_image.lstrip('/')}"
