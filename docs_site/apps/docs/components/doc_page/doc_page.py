"""
DocPage - the document page layout component.

Phase 3a Batch 1: external CSS files, FOUC prevention, design tokens.
The template still uses a single-column layout (no header/sidebar/TOC yet);
Batch 2 replaces it with the full 3-column chrome.
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

            <title>{{ page_title }}</title>

            {% if description %}<meta name="description" content="{{ description }}">{% endif %}

            {% if canonical %}<link rel="canonical" href="{{ canonical }}">{% endif %}

            <meta name="robots" content="{{ robots }}">

            <meta name="generator" content="django-components docs builder">

            {% if breadcrumb_jsonld %}
            <script type="application/ld+json">{{ breadcrumb_jsonld }}</script>
            {% endif %}

            {# FOUC prevention: read stored theme before first paint (3a.4) #}
            <script>
                (function() {
                    var t = localStorage.getItem('djc-theme');
                    if (t === 'dark' || t === 'light') {
                        document.documentElement.setAttribute('data-theme', t);
                    }
                })();
            </script>

            {# External stylesheets: tokens first, then site styles, then Pygments #}
            <link rel="stylesheet" href="/static/css/tokens.css">
            <link rel="stylesheet" href="/static/css/site.css">
            <link rel="stylesheet" href="/static/css/pygments-light.css">
            <link rel="stylesheet" href="/static/css/pygments-dark.css">
        </head>
        <body>
            {# Phase 3a Batch 2 will add header + sidebar + TOC here.
               For now, centered single-column with the external styles. #}
            <div style="max-width: 720px; margin: 2rem auto; padding: 0 1.5rem;">
                <article class="prose">
                    {{ content_html|safe }}
                </article>
                {% if version %}
                <footer style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--c-border);
                               font-size: 0.85rem; color: var(--c-fg-muted);">
                    django-components v{{ version }}
                </footer>
                {% endif %}
            </div>
        </body>
        </html>
    """

    def get_template_data(self, args, kwargs, slots, context):
        breadcrumb_jsonld = ""
        if kwargs.canonical and kwargs.title:
            breadcrumb_jsonld = _build_breadcrumb_jsonld(kwargs.canonical, kwargs.title)

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
