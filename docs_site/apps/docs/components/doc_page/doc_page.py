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
from django.conf import settings

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
        # Search-ranking multiplier (front-matter `boost:`); 1.0 = no boost
        boost: float = 1.0
        # When False, the article omits data-pagefind-body so Pagefind skips the
        # page entirely (used by the 404 page, which shouldn't appear in search).
        searchable: bool = True
        version: str = ""
        lang: str = "en"
        site_name: str = "Django Components"
        nav_tree: NavTree | None = None
        current_path: str = ""
        toc_items: list | None = None
        # Footer git metadata (see build/git_metadata.py); None/[] hides it
        last_updated: datetime | None = None
        # First-commit date, used as TechArticle datePublished (None omits it)
        created: datetime | None = None
        authors: list | None = None
        # Absolute URL of the OG/Twitter card image (see pipeline._resolve_og_image)
        og_image: str = ""
        # GitHub "edit this page" URL; "" hides the link (generated pages)
        edit_url: str = ""

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

            {# Canonical URL - the current-version build points at the latest (root)
               URL; versioned snapshots self-reference (see build_site / feature 6.12) #}
            {% if canonical %}<link rel="canonical" href="{{ canonical }}">{% endif %}

            {# noindex for old versions so they don't compete with /latest/ in search #}
            <meta name="robots" content="{{ robots }}">
            <meta name="generator" content="django-components docs builder">

            {# Google Search Console ownership proof (see settings.GOOGLE_SITE_VERIFICATION) #}
            {% if google_site_verification %}<meta name="google-site-verification" content="{{ google_site_verification }}">{% endif %}

            {# Open Graph + Twitter card metadata for link previews on social
               sites, chat apps, and search result cards. og:image is resolved
               to an absolute URL in the build pipeline. #}
            <meta property="og:type" content="article">
            <meta property="og:site_name" content="{{ site_name }}">
            <meta property="og:title" content="{{ title|default:site_name }}">
            {% if description %}<meta property="og:description" content="{{ description }}">{% endif %}
            {% if canonical %}<meta property="og:url" content="{{ canonical }}">{% endif %}
            {% if og_image %}<meta property="og:image" content="{{ og_image }}">{% endif %}
            <meta name="twitter:card" content="summary_large_image">
            <meta name="twitter:title" content="{{ title|default:site_name }}">
            {% if description %}<meta name="twitter:description" content="{{ description }}">{% endif %}
            {% if og_image %}<meta name="twitter:image" content="{{ og_image }}">{% endif %}

            {# JSON-LD structured data for search engine rich results: a
               BreadcrumbList on every page, plus a TechArticle on content pages. #}
            {% if breadcrumb_jsonld %}
            <script type="application/ld+json">{{ breadcrumb_jsonld|safe }}</script>
            {% endif %}
            {% if article_jsonld %}
            <script type="application/ld+json">{{ article_jsonld|safe }}</script>
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

            {# Point AI agents at the site's markdown index (llmstxt.org) #}
            <link rel="alternate" type="text/markdown" href="/llms.txt" title="LLM index">

            <link rel="icon" type="image/svg+xml" href="/static/img/favicon.svg">
            <link rel="icon" type="image/png" href="/static/img/favicon.png">
            <link rel="apple-touch-icon" href="/static/img/favicon.png">

            <link rel="stylesheet" href="/static/css/tokens.css">
            <link rel="stylesheet" href="/static/css/site.css">
            <link rel="stylesheet" href="/static/css/search.css">
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
                        {# Search trigger: opens the modal (data-search-open). Shows
                           a ⌘K hint on desktop, shrinks to icon-only on mobile.
                           Global / and Ctrl+K shortcuts are wired in Phase 5a Chunk 3. #}
                        <button
                            class="djc-search-trigger"
                            type="button"
                            data-search-open
                            aria-label="Search"
                            aria-haspopup="dialog"
                            aria-controls="djc-search-dialog"
                            aria-expanded="false"
                        >
                            <svg
                                class="djc-search-trigger__icon"
                                viewBox="0 0 24 24"
                                width="16"
                                height="16"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                aria-hidden="true"
                            >
                                <circle cx="11" cy="11" r="8"/>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                            </svg>
                            <span class="djc-search-trigger__label">Search…</span>
                            <kbd class="djc-search-trigger__key">⌘K</kbd>
                        </button>
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
                        {% component "version_picker" current_version=version / %}
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
                        {# Icon paths are FontAwesome 7 free brand marks (CC BY 4.0),
                           copied verbatim from the bundled `material` package's
                           .icons/fontawesome/brands/ - the same source the old
                           mkdocs `extra.social` referenced. 20x20 box matches the
                           GitHub mark; preserveAspectRatio letterboxes (no distortion). #}
                        <a
                            class="djc-social-link"
                            href="https://pypi.org/project/django-components/"
                            aria-label="PyPI"
                            target="_blank"
                            rel="noopener"
                        >
                            <svg
                                viewBox="0 0 448 512"
                                width="20"
                                height="20"
                                fill="currentColor"
                            >
                                <path d="M439.8 200.5c-7.7-30.9-22.3-54.2-53.4-54.2h-40.1v47.4c0 36.8-31.2 67.8-66.8 67.8H172.7c-29.2 0-53.4 25-53.4 54.3v101.8c0 29 25.2 46 53.4 54.3 33.8 9.9 66.3 11.7 106.8 0 26.9-7.8 53.4-23.5 53.4-54.3v-40.7H226.2v-13.6h160.2c31.1 0 42.6-21.7 53.4-54.2 11.2-33.5 10.7-65.7 0-108.6M286.2 444.7a20.4 20.4 0 1 1 0-40.7 20.4 20.4 0 1 1 0 40.7M167.8 248.1h106.8c29.7 0 53.4-24.5 53.4-54.3V91.9c0-29-24.4-50.7-53.4-55.6-35.8-5.9-74.7-5.6-106.8.1-45.2 8-53.4 24.7-53.4 55.6v40.7h106.9v13.6h-147c-31.1 0-58.3 18.7-66.8 54.2-9.8 40.7-10.2 66.1 0 108.6 7.6 31.6 25.7 54.2 56.8 54.2H101v-48.8c0-35.3 30.5-66.4 66.8-66.4m-6.6-183.4a20.4 20.4 0 1 1 0 40.8 20.4 20.4 0 1 1 0-40.8"/>
                            </svg>
                        </a>
                        <a
                            class="djc-social-link"
                            href="https://discord.gg/NaQ8QPyHtD"
                            aria-label="Discord"
                            target="_blank"
                            rel="noopener"
                        >
                            <svg
                                viewBox="0 0 576 512"
                                width="20"
                                height="20"
                                fill="currentColor"
                            >
                                <path d="M492.5 69.8c-.2-.3-.4-.6-.8-.7-38.1-17.5-78.4-30-119.7-37.1-.4-.1-.8 0-1.1.1s-.6.4-.8.8c-5.5 9.9-10.5 20.2-14.9 30.6-44.6-6.8-89.9-6.8-134.4 0-4.5-10.5-9.5-20.7-15.1-30.6-.2-.3-.5-.6-.8-.8s-.7-.2-1.1-.2C162.5 39 122.2 51.5 84.1 69c-.3.1-.6.4-.8.7C7.1 183.5-13.8 294.6-3.6 404.2c0 .3.1.5.2.8s.3.4.5.6c44.4 32.9 94 58 146.8 74.2.4.1.8.1 1.1 0s.7-.4.9-.7c11.3-15.4 21.4-31.8 30-48.8.1-.2.2-.5.2-.8s0-.5-.1-.8-.2-.5-.4-.6-.4-.3-.7-.4c-15.8-6.1-31.2-13.4-45.9-21.9-.3-.2-.5-.4-.7-.6s-.3-.6-.3-.9 0-.6.2-.9.3-.5.6-.7c3.1-2.3 6.2-4.7 9.1-7.1.3-.2.6-.4.9-.4s.7 0 1 .1c96.2 43.9 200.4 43.9 295.5 0 .3-.1.7-.2 1-.2s.7.2.9.4c2.9 2.4 6 4.9 9.1 7.2.2.2.4.4.6.7s.2.6.2.9-.1.6-.3.9-.4.5-.6.6c-14.7 8.6-30 15.9-45.9 21.8-.2.1-.5.2-.7.4s-.3.4-.4.7-.1.5-.1.8.1.5.2.8c8.8 17 18.8 33.3 30 48.8.2.3.6.6.9.7s.8.1 1.1 0c52.9-16.2 102.6-41.3 147.1-74.2.2-.2.4-.4.5-.6s.2-.5.2-.8c12.3-126.8-20.5-236.9-86.9-334.5zm-302 267.7c-29 0-52.8-26.6-52.8-59.2s23.4-59.2 52.8-59.2c29.7 0 53.3 26.8 52.8 59.2 0 32.7-23.4 59.2-52.8 59.2m195.4 0c-29 0-52.8-26.6-52.8-59.2s23.4-59.2 52.8-59.2c29.7 0 53.3 26.8 52.8 59.2 0 32.7-23.2 59.2-52.8 59.2"/>
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
                                    {% component "version_picker" current_version=version / %}
                                </div>
                                {% endif %}
                                <a
                                    class="djc-overflow__link"
                                    href="https://github.com/django-components/django-components"
                                    target="_blank"
                                    rel="noopener"
                                >GitHub</a>
                                <a
                                    class="djc-overflow__link"
                                    href="https://pypi.org/project/django-components/"
                                    target="_blank"
                                    rel="noopener"
                                >PyPI</a>
                                <a
                                    class="djc-overflow__link"
                                    href="https://discord.gg/NaQ8QPyHtD"
                                    target="_blank"
                                    rel="noopener"
                                >Discord</a>
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

                    {# data-pagefind-body scopes the search index to article content
                       only, so the header, sidebar, TOC, prev/next, and footer are
                       never indexed. data-pagefind-weight applies the front-matter
                       `boost:` as a per-page ranking multiplier (omitted when 1.0). #}
                    <article
                        class="prose"
                        {% if searchable %}data-pagefind-body{% endif %}
                        {% if pagefind_weight %}data-pagefind-weight="{{ pagefind_weight }}"{% endif %}
                    >
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

                    {% if version or last_updated or edit_url %}
                    <footer class="djc-footer">
                        {% if edit_url %}
                        <div class="djc-footer__edit">
                            <a href="{{ edit_url }}" target="_blank" rel="noopener">Edit this page on GitHub</a>
                        </div>
                        {% endif %}
                        {% if last_updated %}
                        <div class="djc-footer__meta">
                            Last updated {{ last_updated|date:"j M Y" }}{% if authors %} by {{ authors|join:", " }}{% endif %}
                        </div>
                        {% endif %}
                        {% if version %}
                        <div>django-components version: {{ version }}</div>
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

            {# Back-to-top: hidden until the reader scrolls down; site.js reveals
               it and wires the smooth scroll (mirrors Material's navigation.top) #}
            <button class="djc-back-to-top" type="button" aria-label="Back to top" hidden>
                <svg
                    viewBox="0 0 24 24"
                    width="20"
                    height="20"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                >
                    <line x1="12" y1="19" x2="12" y2="5"/>
                    <polyline points="5 12 12 5 19 12"/>
                </svg>
            </button>

            {# Search overlay (hidden until opened by the header trigger) #}
            {% component "search_modal" / %}

            <script src="/static/js/site.js"></script>
            <script src="/static/js/search.js"></script>
        </body>
        </html>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict:
        breadcrumb_jsonld = ""
        if kwargs.canonical and kwargs.title:
            breadcrumb_jsonld = _build_breadcrumb_jsonld(kwargs.canonical, kwargs.title)

        # TechArticle JSON-LD on content pages only. The homepage and community
        # pages are navigational/policy, not articles, so they're skipped (the
        # BreadcrumbList above still covers them).
        path_norm = kwargs.current_path.strip("/")
        is_article_page = bool(path_norm) and not path_norm.startswith("docs/community")
        article_jsonld = ""
        if is_article_page and kwargs.canonical and kwargs.title:
            article_jsonld = _build_article_jsonld(
                canonical=kwargs.canonical,
                title=kwargs.title,
                description=kwargs.description,
                created=kwargs.created,
                last_updated=kwargs.last_updated,
                site_name=kwargs.site_name,
            )

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

        # Per-page search weight: emit data-pagefind-weight only when boosted,
        # so unboosted pages keep Pagefind's neutral default (1.0).
        pagefind_weight = str(kwargs.boost) if kwargs.boost != 1.0 else ""

        return {
            "searchable": kwargs.searchable,
            "title": kwargs.title,
            "inject_title": inject_title,
            "content_html": kwargs.content_html,
            "page_title": page_title,
            "description": kwargs.description,
            "canonical": kwargs.canonical,
            "robots": robots,
            "version": kwargs.version,
            "lang": kwargs.lang,
            "site_name": kwargs.site_name,
            "google_site_verification": settings.GOOGLE_SITE_VERIFICATION,
            "og_image": kwargs.og_image,
            "edit_url": kwargs.edit_url,
            "breadcrumb_jsonld": breadcrumb_jsonld,
            "article_jsonld": article_jsonld,
            "nav_sections": nav_sections,
            "breadcrumbs": breadcrumbs,
            "prev_page": prev_page,
            "next_page": next_page,
            "toc_items": toc_items,
            "last_updated": kwargs.last_updated,
            "authors": kwargs.authors or [],
            "pagefind_weight": pagefind_weight,
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


def _jsonld_dumps(data: dict[str, Any]) -> str:
    """
    Serialize a JSON-LD object for safe embedding in a `<script>` element.

    The template marks the result `|safe` (so Django doesn't HTML-escape the
    quotes, which a browser would NOT decode inside a script element, breaking
    the JSON). To stay safe we instead escape the three characters that could
    end the script element or be misread, as unicode escapes - the standard
    `json_script` technique.
    """
    raw = json.dumps(data, ensure_ascii=False)
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _build_article_jsonld(
    *,
    canonical: str,
    title: str,
    description: str,
    created: datetime | None,
    last_updated: datetime | None,
    site_name: str,
) -> str:
    """Generate a TechArticle JSON-LD object for a content page."""
    org = {"@type": "Organization", "name": site_name}
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title,
        "mainEntityOfPage": canonical,
        "url": canonical,
        "author": org,
        "publisher": org,
    }
    if description:
        data["description"] = description
    # Dates come from git history (omitted on pages with no tracked history).
    if created is not None:
        data["datePublished"] = created.isoformat()
    if last_updated is not None:
        data["dateModified"] = last_updated.isoformat()
    return _jsonld_dumps(data)


def _build_breadcrumb_jsonld(canonical: str, title: str) -> str:
    """Generate a BreadcrumbList JSON-LD object from a canonical URL."""
    parsed = urlparse(canonical)
    segments = [s for s in parsed.path.strip("/").split("/") if s]

    # Strip the site's base-path prefix (the GitHub Pages project path, e.g.
    # "django-components"), then an optional "/v/<version>/" snapshot prefix.
    # What remains are the content path segments forming the breadcrumb trail.
    # (We can't rely on the "/v/" marker to locate content: the current-version
    # build's canonical has no version segment.)
    prefix: list[str] = []
    base_segs = [s for s in urlparse(str(settings.SITE_URL)).path.strip("/").split("/") if s]
    if base_segs and segments[: len(base_segs)] == base_segs:
        prefix += base_segs
        segments = segments[len(base_segs) :]
    if len(segments) >= 2 and segments[0] == "v":
        prefix += segments[:2]
        segments = segments[2:]

    if not segments:
        return ""

    base_url = f"{parsed.scheme}://{parsed.netloc}/{'/'.join(prefix)}".rstrip("/")
    items = []
    for i, seg in enumerate(segments):
        item_url = f"{base_url}/{'/'.join(segments[: i + 1])}/"
        name = title if i == len(segments) - 1 else seg.replace("_", " ").title()
        items.append(
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": name,
                "item": item_url,
            }
        )

    return _jsonld_dumps(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items,
        }
    )
