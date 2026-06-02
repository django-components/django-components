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

from apps.docs.build.paths import md_to_url, url_to_md
from apps.docs.build.pipeline import render_page


def serve_page(request: HttpRequest, url_path: str = "") -> HttpResponse:
    """Resolve a URL to a content markdown file and render it to HTML."""
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
