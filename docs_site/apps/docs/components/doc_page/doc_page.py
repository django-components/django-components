"""
DocPage - the document page layout component.

The outermost wrapper for every rendered docs page. Provides:
- Full <head> block with SEO metadata (title, description, canonical, robots)
- FOUC prevention script (reads theme from localStorage before first paint)
- 3-column layout: left sidebar (nav) / content / right TOC (scroll-spy)
- Sticky header with logo, nav links, theme picker, version badge, GitHub link
- Breadcrumbs, prev/next page navigation, version footer
- Resizable sidebar dividers (widths persisted to localStorage)

The nav tree, breadcrumbs, and prev/next links are computed from _nav.yml
via NavTree (apps/docs/build/nav.py). The right-rail TOC is built from
python-markdown's toc_tokens output.

Spec: docs_site/design/DESIGN_spike_11.md sections 2-7.
"""

import json
from datetime import datetime
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
        # Footer git metadata (see build/git_metadata.py); None/[] hides it
        last_updated: datetime | None = None
        authors: list | None = None

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
                    {# Hamburger: opens the nav drawer on mobile (<768px) #}
                    <button
                        class="djc-hamburger"
                        aria-label="Open navigation"
                        aria-controls="djc-sidebar"
                        aria-expanded="false"
                    >
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                            <line x1="3" y1="6" x2="21" y2="6"/>
                            <line x1="3" y1="12" x2="21" y2="12"/>
                            <line x1="3" y1="18" x2="21" y2="18"/>
                        </svg>
                    </button>
                    <a class="djc-logo" href="/">
                        <span class="djc-logo__wordmark">django-components</span>
                    </a>
                    <nav class="djc-header__nav">
                        <a href="/docs/">Docs</a>
                        <a href="/examples/">Examples</a>
                        <a href="/plugins/">Plugins</a>
                    </nav>
                    <div class="djc-header__actions">
                        {# Theme picker: 3 buttons (light / auto / dark) #}
                        <div class="djc-theme-picker" role="radiogroup" aria-label="Color theme">
                            <button
                                class="djc-theme-picker__btn"
                                data-theme-value="light"
                                aria-label="Light theme"
                                title="Light"
                            >
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
                            </button>
                            <button
                                class="djc-theme-picker__btn"
                                data-theme-value="auto"
                                aria-label="System theme"
                                title="System"
                            >
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect x="2" y="3" width="20" height="14" rx="2"/>
                                    <line x1="8" y1="21" x2="16" y2="21"/>
                                    <line x1="12" y1="17" x2="12" y2="21"/>
                                </svg>
                            </button>
                            <button
                                class="djc-theme-picker__btn"
                                data-theme-value="dark"
                                aria-label="Dark theme"
                                title="Dark"
                            >
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                                </svg>
                            </button>
                        </div>
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

                        {# Overflow menu: collapses version + theme + GitHub on mobile (<768px) #}
                        <div class="djc-overflow">
                            <button
                                class="djc-overflow__btn"
                                aria-label="More options"
                                aria-haspopup="true"
                                aria-expanded="false"
                            >
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                    <circle cx="12" cy="5" r="2"/>
                                    <circle cx="12" cy="12" r="2"/>
                                    <circle cx="12" cy="19" r="2"/>
                                </svg>
                            </button>
                            <div class="djc-overflow__menu">
                                <div class="djc-overflow__row">
                                    <span class="djc-overflow__label">Theme</span>
                                    {# Same data-theme-value hooks as the desktop picker; site.js wires both #}
                                    <div class="djc-theme-picker" role="radiogroup" aria-label="Color theme">
                                        <button class="djc-theme-picker__btn djc-theme-picker__btn--text" data-theme-value="light">Light</button>
                                        <button class="djc-theme-picker__btn djc-theme-picker__btn--text" data-theme-value="auto">Auto</button>
                                        <button class="djc-theme-picker__btn djc-theme-picker__btn--text" data-theme-value="dark">Dark</button>
                                    </div>
                                </div>
                                {% if version %}
                                <div class="djc-overflow__row">
                                    <span class="djc-overflow__label">Version</span>
                                    <span class="djc-version-badge">v{{ version }}</span>
                                </div>
                                {% endif %}
                                <a
                                    class="djc-overflow__link"
                                    href="https://github.com/django-components/django-components"
                                    target="_blank"
                                    rel="noopener"
                                >GitHub</a>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {# ============================================================ #}
            {# LAYOUT: sidebar / content / toc                               #}
            {# ============================================================ #}
            <div class="djc-layout">

                {# LEFT SIDEBAR (off-canvas drawer below 768px) #}
                <aside class="djc-sidebar" id="djc-sidebar">
                    {# Drawer-only: top-nav links live in the drawer on mobile (header nav is hidden) #}
                    <nav class="djc-sidebar__topnav">
                        <a href="/docs/">Docs</a>
                        <a href="/examples/">Examples</a>
                        <a href="/plugins/">Plugins</a>
                    </nav>
                    <nav class="djc-sidebar__nav">
                        {% for section in nav_sections %}
                        <div class="djc-sidebar__section{% if section.is_standalone %} djc-sidebar__section--standalone{% endif %}">
                            {% if section.is_standalone %}
                            {# A section that is just a page (no children) renders as a
                               link, not an uppercase category label, so its appearance
                               matches its behavior: it's clickable. #}
                            <a
                                class="djc-sidebar__link djc-sidebar__link--top{% if section.active %} is-active{% endif %}"
                                href="{{ section.path }}"
                            >{{ section.label }}</a>
                            {% else %}
                            {# Category label: purely organizational, never a link. #}
                            <div class="djc-sidebar__label">{{ section.label }}</div>

                            {% if section.index_path or section.child_items %}
                            <ul class="djc-sidebar__items">
                                {% if section.index_path %}
                                {# The section's own landing page, surfaced as a child item
                                   so the category label itself can stay inert. #}
                                <li>
                                    <a
                                        class="djc-sidebar__link{% if section.index_active %} is-active{% endif %}"
                                        href="{{ section.index_path }}"
                                    >Overview</a>
                                </li>
                                {% endif %}
                                {% for item in section.child_items %}
                                <li>
                                    <a
                                        class="djc-sidebar__link{% if item.active %} is-active{% endif %}"
                                        href="{{ item.path }}"
                                    >{{ item.title }}</a>
                                </li>
                                {% endfor %}
                            </ul>
                            {% endif %}

                            {% if section.child_groups %}
                            {% for group in section.child_groups %}
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
                            {% endif %}
                        </div>
                        {% endfor %}
                    </nav>
                </aside>

                {# Dimmed backdrop behind the open drawer; click closes it #}
                <div class="djc-drawer-overlay"></div>

                {# Resize handle: sidebar | content #}
                <div class="djc-resize-handle" data-target="djc-sidebar" data-direction="left"></div>

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

                    {# Mobile TOC: the right rail is hidden below 1024px, so offer a disclosure instead #}
                    {% if toc_items %}
                    <details class="djc-toc-mobile">
                        <summary>On this page</summary>
                        {# No collapse on mobile: members are shown inline when the disclosure is open. #}
                        <ul class="djc-toc__list">
                            {% for item in toc_items %}
                            <li class="djc-toc__item">
                                <span class="djc-toc__row">
                                    {% if item.kind %}<span class="doc-symbol doc-symbol-{{ item.kind }}"></span>{% endif %}
                                    <a class="djc-toc__link" href="#{{ item.id }}">{{ item.name }}</a>
                                </span>
                                {% if item.children %}
                                <ul class="djc-toc__sublist">
                                    {% for child in item.children %}
                                    <li class="djc-toc__subitem">
                                        {% if child.kind %}<span class="doc-symbol doc-symbol-{{ child.kind }}"></span>{% endif %}
                                        <a class="djc-toc__link" href="#{{ child.id }}">{{ child.name }}</a>
                                    </li>
                                    {% endfor %}
                                </ul>
                                {% endif %}
                            </li>
                            {% endfor %}
                        </ul>
                    </details>
                    {% endif %}

                    <article class="prose">
                        {# Pages without their own H1 get one from the page title,
                           mirroring how Material injected nav titles on the old site #}
                        {% if inject_title %}<h1>{{ title }}</h1>{% endif %}
                        {# content_html is already-rendered HTML from our pipeline - mark safe #}
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

                    {% if version or last_updated %}
                    <footer class="djc-footer">
                        {% if last_updated %}
                        <div class="djc-footer__meta">
                            Last updated {{ last_updated|date:"j M Y" }}{% if authors %} by {{ authors|join:", " }}{% endif %}
                        </div>
                        {% endif %}
                        {% if version %}
                        <div>django-components v{{ version }}</div>
                        {% endif %}
                    </footer>
                    {% endif %}
                </main>

                {# RIGHT TOC #}
                {% if toc_items %}
                {# Resize handle: content | TOC #}
                <div class="djc-resize-handle" data-target="djc-toc" data-direction="right"></div>

                <aside class="djc-toc" id="djc-toc">
                    <div class="djc-toc__label">On this page</div>
                    <ul class="djc-toc__list">
                        {% for item in toc_items %}
                        <li class="djc-toc__item{% if item.collapsible %} djc-toc__item--collapsible{% endif %}">
                            <span class="djc-toc__row">
                                {% if item.collapsible %}<button type="button" class="djc-toc__toggle" aria-expanded="false" aria-label="Toggle members of {{ item.name }}"></button>{% endif %}
                                {% if item.kind %}<span class="doc-symbol doc-symbol-{{ item.kind }}"></span>{% endif %}
                                <a class="djc-toc__link" href="#{{ item.id }}">{{ item.name }}</a>
                            </span>
                            {% if item.children %}
                            <ul class="djc-toc__sublist">
                                {% for child in item.children %}
                                <li class="djc-toc__subitem">
                                    {% if child.kind %}<span class="doc-symbol doc-symbol-{{ child.kind }}"></span>{% endif %}
                                    <a class="djc-toc__link" href="#{{ child.id }}">{{ child.name }}</a>
                                </li>
                                {% endfor %}
                            </ul>
                            {% endif %}
                        </li>
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

        nav_sections_raw: list[NavSection] = []
        breadcrumbs: list[tuple[str, str]] = []
        prev_page: NavItem | None = None
        next_page: NavItem | None = None

        if kwargs.nav_tree:
            kwargs.nav_tree.set_active(kwargs.current_path)
            nav_sections_raw = kwargs.nav_tree.sections
            breadcrumbs = kwargs.nav_tree.find_breadcrumbs(kwargs.current_path)
            prev_page, next_page = kwargs.nav_tree.find_prev_next(kwargs.current_path)

        nav_sections = _build_nav_view(nav_sections_raw, kwargs.current_path)

        toc_items = _flatten_toc(kwargs.toc_items) if kwargs.toc_items else []

        # Inject an <h1> from the page title when the content brings none
        # (raw toc_tokens still include H1 entries, unlike the flattened list)
        has_h1 = any(token.get("level") == 1 for token in (kwargs.toc_items or []))
        inject_title = bool(kwargs.title) and not has_h1

        return {
            "title": kwargs.title,
            "inject_title": inject_title,
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
            "last_updated": kwargs.last_updated,
            "authors": kwargs.authors or [],
        }


def _build_nav_view(sections: "list[NavSection]", current_path: str) -> list[dict]:
    """
    Build the sidebar view model from nav sections.

    Splits each section into one of two render shapes so appearance encodes
    behavior (the rule: uppercase label = inert category, normal text = page):

    - A section that is just a page (a path, no children) -> a standalone link.
    - A section with children -> an inert category label. If it also has its own
      landing page (a path *and* children, e.g. the API reference index), that
      page is surfaced as an "Overview" child item so the label stays inert.
    """
    current = current_path.strip("/")
    view: list[dict] = []
    for section in sections:
        has_children = bool(section.items) or bool(section.groups)
        is_standalone = bool(section.path) and not has_children
        section_norm = (section.path or "").strip("/")
        view.append(
            {
                "label": section.label,
                "path": section.path,
                "is_standalone": is_standalone,
                "active": is_standalone and section_norm == current,
                # Landing page of a category section, rendered as its first child
                "index_path": section.path if (section.path and has_children) else "",
                "index_active": bool(section.path) and has_children and section_norm == current,
                # Renamed off "items"/"groups" so Django template var resolution
                # can't mistake them for dict.items() / dict-method lookups
                "child_items": section.items,
                "child_groups": section.groups,
            }
        )
    return view


def _flatten_toc(toc_tokens: list) -> list[dict]:
    """
    Convert the toc token tree into the right-rail's render model.

    The page H1 (the title) is unwrapped so its sections become the top level -
    the rail lists sections, not the redundant page title (matching the old
    reference TOC). Each item keeps one level of children. ``kind`` (the symbol
    type) drives the badge; ``collapsible`` (children that carry a kind, i.e.
    class members) drives the expand/collapse affordance, so plain content
    subsections stay always-visible while a class's members fold away.
    """
    top: list = []
    for token in toc_tokens:
        if token.get("level") == 1:
            top.extend(token.get("children", []))
        else:
            top.append(token)

    items = []
    for token in top:
        children = [
            {"id": c["id"], "name": c["name"], "level": c.get("level", 4), "kind": c.get("kind", "")}
            for c in token.get("children", [])
        ]
        items.append(
            {
                "id": token["id"],
                "name": token["name"],
                "level": token.get("level", 2),
                "kind": token.get("kind", ""),
                "children": children,
                "collapsible": any(c["kind"] for c in children),
            }
        )
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
