"""
DocPage - the full document page layout component.

Phase 3a Batch 2: 3-column layout with header, sidebar, right-rail TOC,
breadcrumbs, and prev/next page navigation.

Spec: docs_site/design/DESIGN_spike_11.md sections 2-7.
"""

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from apps.docs.build.nav import NavTree

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.build.nav import NavItem, NavSection


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
        nav_tree: NavTree | None = None
        current_path: str = ""
        toc_items: list | None = None

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

            {# FOUC prevention: read stored theme before first paint #}
            <script>
                (function() {
                    var t = localStorage.getItem('djc-theme');
                    if (t === 'dark' || t === 'light') {
                        document.documentElement.setAttribute('data-theme', t);
                    }
                })();
            </script>

            <link rel="stylesheet" href="/static/css/tokens.css">
            <link rel="stylesheet" href="/static/css/site.css">
            <link rel="stylesheet" href="/static/css/pygments-light.css">
            <link rel="stylesheet" href="/static/css/pygments-dark.css">
        </head>
        <body>

            {# ============================================================ #}
            {# TOP HEADER (sticky 64px)                                      #}
            {# ============================================================ #}
            <header class="djc-header">
                <div class="djc-header__inner">
                    <a class="djc-logo" href="/">
                        <span class="djc-logo__wordmark">django-components</span>
                    </a>
                    <nav class="djc-header__nav">
                        <a href="/">Docs</a>
                        <a href="/examples/">Examples</a>
                    </nav>
                    <div class="djc-header__actions">
                        <button
                            class="djc-theme-toggle"
                            aria-label="Toggle theme"
                            title="Toggle theme"
                        >
                            <svg
                                class="djc-theme-toggle__icon djc-theme-toggle__icon--light"
                                viewBox="0 0 24 24"
                                width="20"
                                height="20"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <circle cx="12" cy="12" r="5"/>
                                <line x1="12" y1="1" x2="12" y2="3"/>
                                <line x1="12" y1="21" x2="12" y2="23"/>
                                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                                <line x1="1" y1="12" x2="3" y2="12"/>
                                <line x1="21" y1="12" x2="23" y2="12"/>
                                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                            </svg>
                            <svg
                                class="djc-theme-toggle__icon djc-theme-toggle__icon--dark"
                                viewBox="0 0 24 24"
                                width="20"
                                height="20"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                            </svg>
                        </button>
                        {% if version %}
                        <span class="djc-version-badge">v{{ version }}</span>
                        {% endif %}
                        <a
                            class="djc-gh-link"
                            href="https://github.com/django-components/django-components"
                            aria-label="GitHub"
                            target="_blank"
                            rel="noopener"
                        >
                            <svg
                                viewBox="0 0 16 16"
                                width="20"
                                height="20"
                                fill="currentColor"
                            >
                                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                            </svg>
                        </a>
                    </div>
                </div>
            </header>

            {# ============================================================ #}
            {# LAYOUT: sidebar / content / toc                               #}
            {# ============================================================ #}
            <div class="djc-layout">

                {# LEFT SIDEBAR #}
                <aside class="djc-sidebar" id="djc-sidebar">
                    <nav class="djc-sidebar__nav">
                        {% for section in nav_sections %}
                        <div class="djc-sidebar__section">
                            {% if section.path %}
                            <a class="djc-sidebar__label" href="{{ section.path }}">{{ section.label }}</a>
                            {% else %}
                            <div class="djc-sidebar__label">{{ section.label }}</div>
                            {% endif %}

                            {% if section.items %}
                            <ul class="djc-sidebar__items">
                                {% for item in section.items %}
                                <li>
                                    <a
                                        class="djc-sidebar__link{% if item.active %} is-active{% endif %}"
                                        href="{{ item.path }}"
                                    >{{ item.title }}</a>
                                </li>
                                {% endfor %}
                            </ul>
                            {% endif %}

                            {% if section.groups %}
                            {% for group in section.groups %}
                            <div class="djc-sidebar__group" data-open="{{ group.expanded|yesno:'true,false' }}">
                                <button
                                    class="djc-sidebar__group-label"
                                    aria-expanded="{{ group.expanded|yesno:'true,false' }}"
                                >
                                    <span>{{ group.label }}</span>
                                    <span class="djc-sidebar__caret">&#9662;</span>
                                </button>
                                <ul class="djc-sidebar__items" {% if not group.expanded %}hidden{% endif %}>
                                    {% for item in group.items %}
                                    <li>
                                        <a
                                            class="djc-sidebar__link{% if item.active %} is-active{% endif %}"
                                            href="{{ item.path }}"
                                        >{{ item.title }}</a>
                                    </li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endfor %}
                            {% endif %}
                        </div>
                        {% endfor %}
                    </nav>
                </aside>

                {# CONTENT #}
                <main class="djc-content">
                    {% if breadcrumbs %}
                    <nav class="djc-breadcrumbs" aria-label="Breadcrumb">
                        {% for label, path in breadcrumbs %}
                        {% if not forloop.last %}
                        {% if path %}<a href="{{ path }}">{{ label }}</a>{% else %}<span>{{ label }}</span>{% endif %}
                        <span class="djc-breadcrumbs__sep">/</span>
                        {% else %}
                        <span class="djc-breadcrumbs__current">{{ label }}</span>
                        {% endif %}
                        {% endfor %}
                    </nav>
                    {% endif %}

                    <article class="prose">
                        {{ content_html|safe }}
                    </article>

                    {# PREV / NEXT PAGE NAV #}
                    {% if prev_page or next_page %}
                    <nav class="djc-page-nav">
                        {% if prev_page %}
                        <a class="djc-page-nav__card djc-page-nav__prev" href="{{ prev_page.path }}">
                            <span class="djc-page-nav__direction">&larr; Previous</span>
                            <strong>{{ prev_page.title }}</strong>
                        </a>
                        {% else %}
                        <div class="djc-page-nav__card djc-page-nav__placeholder"></div>
                        {% endif %}
                        {% if next_page %}
                        <a class="djc-page-nav__card djc-page-nav__next" href="{{ next_page.path }}">
                            <span class="djc-page-nav__direction">Next &rarr;</span>
                            <strong>{{ next_page.title }}</strong>
                        </a>
                        {% else %}
                        <div class="djc-page-nav__card djc-page-nav__placeholder"></div>
                        {% endif %}
                    </nav>
                    {% endif %}

                    {% if version %}
                    <footer class="djc-footer">
                        django-components v{{ version }}
                    </footer>
                    {% endif %}
                </main>

                {# RIGHT TOC #}
                {% if toc_items %}
                <aside class="djc-toc" id="djc-toc">
                    <div class="djc-toc__label">On this page</div>
                    <ul class="djc-toc__list">
                        {% for item in toc_items %}
                        <li class="djc-toc__item djc-toc__item--{{ item.level }}">
                            <a class="djc-toc__link" href="#{{ item.id }}">{{ item.name }}</a>
                        </li>
                        {% if item.children %}
                        {% for child in item.children %}
                        <li class="djc-toc__item djc-toc__item--{{ child.level }}">
                            <a class="djc-toc__link" href="#{{ child.id }}">{{ child.name }}</a>
                        </li>
                        {% endfor %}
                        {% endif %}
                        {% endfor %}
                    </ul>
                </aside>
                {% endif %}
            </div>

            <script src="/static/js/site.js"></script>
        </body>
        </html>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict:
        breadcrumb_jsonld = ""
        if kwargs.canonical and kwargs.title:
            breadcrumb_jsonld = _build_breadcrumb_jsonld(kwargs.canonical, kwargs.title)

        if kwargs.title and kwargs.title != kwargs.site_name:
            page_title = f"{kwargs.title} - {kwargs.site_name}"
        else:
            page_title = kwargs.site_name
        robots = "noindex,follow" if kwargs.noindex else "index,follow"

        nav_sections: list[NavSection] = []
        breadcrumbs: list[tuple[str, str]] = []
        prev_page: NavItem | None = None
        next_page: NavItem | None = None

        if kwargs.nav_tree:
            kwargs.nav_tree.set_active(kwargs.current_path)
            nav_sections = kwargs.nav_tree.sections
            breadcrumbs = kwargs.nav_tree.find_breadcrumbs(kwargs.current_path)
            prev_page, next_page = kwargs.nav_tree.find_prev_next(kwargs.current_path)

        toc_items = _flatten_toc(kwargs.toc_items) if kwargs.toc_items else []

        return {
            "content_html": kwargs.content_html,
            "page_title": page_title,
            "description": kwargs.description,
            "canonical": kwargs.canonical,
            "robots": robots,
            "version": kwargs.version,
            "lang": kwargs.lang,
            "breadcrumb_jsonld": breadcrumb_jsonld,
            "nav_sections": nav_sections,
            "breadcrumbs": breadcrumbs,
            "prev_page": prev_page,
            "next_page": next_page,
            "toc_items": toc_items,
        }


def _flatten_toc(toc_tokens: list) -> list[dict]:
    """
    Convert python-markdown toc_tokens into a flat list of {id, name, level, children}.

    toc_tokens is nested: [{id, name, level, children: [{...}]}].
    We keep children one level deep (H2 with H3 children) for the right-rail TOC.
    """
    items = []
    for token in toc_tokens:
        children = []
        for child in token.get("children", []):
            children.append({"id": child["id"], "name": child["name"], "level": child.get("level", 3)})
        items.append({
            "id": token["id"],
            "name": token["name"],
            "level": token.get("level", 2),
            "children": children,
        })
    return items


def _build_breadcrumb_jsonld(canonical: str, title: str) -> str:
    """Generate a BreadcrumbList JSON-LD object from a canonical URL."""
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
