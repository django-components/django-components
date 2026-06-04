"""
Live-serving views for the docs dev server.

Renders markdown pages on the fly through the same pipeline the build command
uses, so authors can preview changes via `docs_serve` without a full build.
Each request resolves a URL to a content markdown file and renders it.
"""

from __future__ import annotations

from importlib.metadata import version as get_version

import pygments_djc  # noqa: F401 -- register the djc_py Pygments lexer
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.test import RequestFactory

from apps.docs.build.paths import md_to_url, url_to_md
from apps.docs.build.pipeline import render_page
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
    get_example_registry()

    md_path = url_to_md(settings.CONTENT_DIR, url_path)
    if md_path is None:
        raise Http404(f"No docs page for /{url_path}")

    rel = md_path.relative_to(settings.CONTENT_DIR)
    ver = get_version("django_components")
    page_url = md_to_url(rel)

    # Mirror the build command's context so the live preview matches the build output
    ctx = {
        "version": ver,
        "canonical": f"{settings.SITE_URL}/v/{ver}/{page_url}",
        "site_url": f"{settings.SITE_URL}/v/{ver}",
    }

    source = md_path.read_text(encoding="utf-8")
    result = render_page(source, context=ctx, source_path=md_path, content_dir=settings.CONTENT_DIR)
    return HttpResponse(result.html)


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
