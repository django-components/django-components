"""
DocPage - the document page layout component (Phase 1 stub).

This is the outermost wrapper for every rendered docs page. It provides:
- A complete <head> block with SEO metadata (title, description, canonical, robots)
- Design tokens from spike 11.11 (OKLCH-based color system)
- Prose CSS for headings, code blocks, admonitions, tables, inline code
- A version footer

Phase 3a replaces this stub with the full chrome: header, sidebar, right-rail TOC,
breadcrumbs, dark mode toggle, search trigger. The template structure will change
significantly at that point - this version is intentionally minimal.
"""

import json
from urllib.parse import urlparse

from django_components import Component, register, types


@register("doc_page")
class DocPage(Component):
    class Kwargs:
        content_html: str
        title: str = ""
        description: str = ""
        canonical: str = ""
        noindex: bool = False
        version: str = ""
        lang: str = "en"
        site_name: str = "Django Components"

    template: types.django_html = """
        <!DOCTYPE html>
        <html lang="{{ lang }}">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">

            {# Title and robots directive are composed in get_template_data #}
            <title>{{ page_title }}</title>

            {# Per-page meta description for search engine snippets #}
            {% if description %}<meta name="description" content="{{ description }}">{% endif %}

            {# Canonical URL - versioned pages point to /latest/ counterpart #}
            {% if canonical %}<link rel="canonical" href="{{ canonical }}">{% endif %}

            {# noindex for old versions so they don't compete with /latest/ in search #}
            <meta name="robots" content="{{ robots }}">

            <meta name="generator" content="django-components docs builder">

            {# JSON-LD BreadcrumbList for search engine rich results #}
            {% if breadcrumb_jsonld %}
            <script type="application/ld+json">{{ breadcrumb_jsonld }}</script>
            {% endif %}

            {# Phase 1 inline styles - extracted to static CSS files in Phase 3a #}
            <style>
                /* Design tokens from spike 11.11 section 10 (light theme) */
                :root {
                    --c-bg: #fbfcfd;
                    --c-fg: #1d2030;
                    --c-fg-muted: #525b6e;
                    --c-border: #d0d5db;
                    --c-link: #3870c5;
                    --c-accent: #0d8a8a;
                    --c-surface-2: #e9edf2;
                    --c-note: #2196f3;
                    --c-warning: #ff9800;
                    --c-info: #009688;
                }

                /* Body: centered single column, comfortable reading width */
                body {
                    max-width: 720px; margin: 2rem auto; padding: 0 1.5rem;
                    font-family: Inter, system-ui, -apple-system, sans-serif;
                    line-height: 1.65; color: var(--c-fg-muted);
                    background: var(--c-bg);
                }

                /* Headings carry the visual weight; body sits lower */
                h1, h2, h3, h4, h5, h6 { color: var(--c-fg); }
                h1 { font-size: 2.25rem; margin-top: 0; }
                h2 { font-size: 1.75rem; margin-top: 3rem; padding-top: 1.5rem;
                     border-top: 1px solid var(--c-border); }
                h3 { font-size: 1.25rem; margin-top: 2rem; }

                a { color: var(--c-link); text-decoration: none; }
                a:hover { text-decoration: underline; }

                /* Code blocks: subtle left accent border */
                pre { background: var(--c-surface-2); padding: 1rem 1.25rem;
                      border-radius: 0.5rem; overflow-x: auto;
                      border-left: 3px solid var(--c-link); }
                code { font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;
                       font-size: 0.875em; }

                /* Inline code: accent-colored pill (spike 11.11 section 5.4) */
                :not(pre) > code { color: var(--c-accent); background: rgba(13,138,138,0.1);
                                   padding: 0.1em 0.35em; border-radius: 0.2em; }

                /* Admonitions: left-border accent + tinted background */
                .admonition { border-left: 3px solid var(--c-note); padding: 0.5rem 1rem;
                              margin: 1rem 0; background: rgba(33,150,243,0.06);
                              border-radius: 0 0.25rem 0.25rem 0; }
                .admonition.warning { border-left-color: var(--c-warning);
                                      background: rgba(255,152,0,0.06); }
                .admonition.info { border-left-color: var(--c-info);
                                   background: rgba(0,150,136,0.06); }
                .admonition-title { font-weight: 600; font-size: 0.85rem;
                                    text-transform: uppercase; letter-spacing: 0.05em; }

                /* Tables */
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid var(--c-border); padding: 0.5rem 0.75rem; text-align: left; }
                th { background: var(--c-surface-2); font-weight: 600; }

                /* pymdownx.tabbed, pymdownx.details, pymdownx.tasklist */
                .tabbed-set { margin: 1rem 0; }
                .tabbed-set > input { display: none; }
                details { margin: 1rem 0; }
                summary { cursor: pointer; font-weight: 600; }
                .task-list-item { list-style: none; }
                .task-list-item input[type="checkbox"] { margin-right: 0.5rem; }
            </style>
        </head>
        <body>
            <article class="prose">
                {# content_html is already-rendered HTML from our pipeline - mark safe #}
                {{ content_html|safe }}
            </article>
            {% if version %}
            <footer style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--c-border);
                           font-size: 0.85rem; color: var(--c-fg-muted);">
                django-components v{{ version }}
            </footer>
            {% endif %}
        </body>
        </html>
    """

    def get_template_data(self, args, kwargs, slots, context):
        # Build JSON-LD BreadcrumbList from the canonical URL path segments
        breadcrumb_jsonld = ""
        if kwargs.canonical and kwargs.title:
            breadcrumb_jsonld = _build_breadcrumb_jsonld(kwargs.canonical, kwargs.title)

        # Compose the <title> ("Page - Site", or just "Site" on the home page) and the
        # robots directive here so the template stays declarative.
        if kwargs.title and kwargs.title != kwargs.site_name:
            page_title = f"{kwargs.title} - {kwargs.site_name}"
        else:
            page_title = kwargs.site_name
        robots = "noindex,follow" if kwargs.noindex else "index,follow"

        return {
            "content_html": kwargs.content_html,
            "page_title": page_title,
            "description": kwargs.description,
            "canonical": kwargs.canonical,
            "robots": robots,
            "version": kwargs.version,
            "lang": kwargs.lang,
            "breadcrumb_jsonld": breadcrumb_jsonld,
        }


def _build_breadcrumb_jsonld(canonical: str, title: str) -> str:
    """
    Generate a BreadcrumbList JSON-LD object from a canonical URL.

    Extracts path segments after /v/<version>/ and builds a breadcrumb
    trail ending with the current page title.
    """
    parsed = urlparse(canonical)
    path = parsed.path.strip("/")
    segments = [s for s in path.split("/") if s]

    # Skip the site prefix segments (e.g. "django-components", "v", "0.150.0")
    # to get to the content path
    content_start = 0
    for i, seg in enumerate(segments):
        if seg == "v" and i + 1 < len(segments):
            content_start = i + 2
            break

    content_segments = segments[content_start:]
    if not content_segments:
        return ""

    base_url = f"{parsed.scheme}://{parsed.netloc}/{'/'.join(segments[:content_start])}"
    items = []
    for i, seg in enumerate(content_segments):
        item_url = f"{base_url}/{'/'.join(content_segments[: i + 1])}/"
        # Last segment uses the page title; earlier ones use the slug as-is
        name = title if i == len(content_segments) - 1 else seg.replace("_", " ").title()
        items.append(
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": name,
                "item": item_url,
            }
        )

    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items,
        },
        ensure_ascii=False,
    )
