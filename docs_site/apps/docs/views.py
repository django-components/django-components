"""
Live-serving views for the docs dev server.

Renders markdown pages on the fly through the same pipeline the build command
uses, so authors can preview changes via `docs_serve` without a full build.
Each request resolves a URL to a content markdown file and renders it.
"""

from __future__ import annotations

from importlib.metadata import version as get_version
from pathlib import Path

import pygments_djc  # noqa: F401 -- register the djc_py Pygments lexer
from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.test import RequestFactory

from apps.docs.build.examples import examples_index_markdown
from apps.docs.build.git_metadata import EMPTY_META, get_page_git_meta, is_excluded
from apps.docs.build.nav import load_nav
from apps.docs.build.paths import edit_url_for, md_to_url, url_to_md
from apps.docs.build.pipeline import render_page
from apps.docs.build.reference import get_reference_staging_dir
from apps.docs.build.release_notes import get_release_staging_dir
from apps.docs.examples import get_example_registry


def serve_page(request: HttpRequest, url_path: str = "") -> HttpResponse:
    """
    Resolve a URL to a content markdown file and render it to HTML.

    This is the catch-all view for the dev server. It maps incoming URLs
    to markdown source files under CONTENT_DIR using the same path logic
    as the build command, then renders through the 3-pass pipeline.

    Example autodiscovery runs on first request (cached) so that pages
    using {% example %} can resolve their references.
    """
    # Ensure examples are discovered before any page with {% example %} renders
    registry = get_example_registry()

    # /examples/ is a generated index page (like in the static build)
    if url_path.strip("/") == "examples":
        ver = get_version("django_components")
        result = render_page(
            examples_index_markdown(registry),
            context={"version": ver, "site_url": f"{settings.SITE_URL}/v/{ver}"},
            nav_tree=load_nav(settings.CONTENT_DIR / "_nav.yml"),
            current_path="examples/",
        )
        return HttpResponse(result.html)

    content_root = settings.CONTENT_DIR
    md_path = url_to_md(content_root, url_path)

    # /docs/releases/ pages are generated from CHANGELOG.md, not stored in
    # content/. Generate on demand (cached on changelog mtime) for live preview.
    if md_path is None and (url_path.strip("/") == "docs/releases" or url_path.startswith("docs/releases/")):
        content_root = get_release_staging_dir(settings.CHANGELOG_PATH)
        md_path = url_to_md(content_root, url_path)

    # /docs/reference/ pages generated from source docstrings (Phase 4) aren't in
    # content/ either; generate on demand for live preview. Only the migrated
    # pages fall through here - the others are still content stubs.
    if md_path is None and url_path.startswith("docs/reference/"):
        content_root = get_reference_staging_dir()
        md_path = url_to_md(content_root, url_path)

    if md_path is None:
        # Not a renderable page - it may be a content asset, e.g. an image a page
        # references relatively (docs/images/foo.png). The static build copies
        # these into the output; here we serve them straight from CONTENT_DIR so
        # the live preview matches.
        asset = _content_asset(url_path)
        if asset is not None:
            return FileResponse(asset.open("rb"))
        raise Http404(f"No docs page for /{url_path}")

    rel = md_path.relative_to(content_root)
    ver = get_version("django_components")
    page_url = md_to_url(rel)

    # Footer metadata from git history; mirrors the build command
    git_meta = EMPTY_META if is_excluded(rel) else get_page_git_meta(settings.REPO_ROOT, md_path)

    # Mirror the build command's current-version build (preview mode): canonical
    # to the latest (root) URL, not the versioned one (the dev server previews
    # the current-version site).
    site_base = str(settings.SITE_URL).rstrip("/")
    ctx = {
        "version": ver,
        "canonical": f"{site_base}/{page_url}",
        "site_url": site_base,
        "git_meta": git_meta,
        "edit_url": edit_url_for(md_path),
    }

    nav_tree = load_nav(settings.CONTENT_DIR / "_nav.yml")

    source = md_path.read_text(encoding="utf-8")
    result = render_page(
        source,
        context=ctx,
        source_path=md_path,
        content_dir=content_root,
        nav_tree=nav_tree,
        current_path=page_url,
    )
    return HttpResponse(result.html)


def _content_asset(url_path: str) -> Path | None:
    """
    The content file backing ``url_path`` (e.g. an image), if one exists.

    Resolved under CONTENT_DIR and confined to it (no path traversal). Markdown is
    excluded - it's rendered as a page, not served raw.
    """
    root = settings.CONTENT_DIR.resolve()
    candidate = (root / url_path.strip("/")).resolve()
    if not candidate.is_relative_to(root) or candidate.suffix == ".md":
        return None
    return candidate if candidate.is_file() else None


def serve_example(request: HttpRequest, name: str) -> HttpResponse:
    """Serve an example's full page live during development."""
    registry = get_example_registry()
    if name not in registry:
        raise Http404(f"Unknown example: {name}")

    info = registry[name]
    view_fn = info.page_cls.as_view()
    return view_fn(request)


def serve_example_fragment(request: HttpRequest, name: str, variant: str) -> HttpResponse:
    """
    Serve a fragment variant live during development.

    Looks up the query params for the variant from DocsExample.fragments
    and forwards them to the example's View.get().
    """
    registry = get_example_registry()
    if name not in registry:
        raise Http404(f"Unknown example: {name}")

    info = registry[name]
    if variant not in info.fragments:
        raise Http404(f"Unknown fragment variant: {name}/{variant}")

    # Build a new request with the declared query params for this variant
    query_params = info.fragments[variant]
    fake_request = RequestFactory().get(request.path, data=query_params)
    view_fn = info.page_cls.as_view()
    return view_fn(fake_request)
