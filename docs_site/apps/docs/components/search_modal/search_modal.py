"""
SearchModal - the docs-site search overlay (Phase 5a, features 5a.2 / 5a.4).

Renders the markup for the centered search modal: the search input, a results
container that search.js fills from the Pagefind API, an empty-state list of
popular pages, and a keyboard-help footer. The header trigger button that opens
this modal lives inline in DocPage; the behavior (lazy Pagefind load, debounced
search, result rendering, keyboard navigation) lives in static/js/search.js.

The whole overlay carries `data-pagefind-ignore` so the search UI never indexes
itself, and it is excluded from the indexed region anyway (the index is scoped
to the `<article data-pagefind-body>` content, see doc_page.py).

The quick-link `<a href>`s render into every page's HTML, so the post-build
internal_link guard validates them - a moved target fails CI rather than rotting
silently.

Spec: docs_site/design/DESIGN_spike_11.md section 8; main doc section 11.1.G.5.
"""

from __future__ import annotations

from typing import Any

from django_components import Component, register, types

# Popular pages shown in the empty state (before the user types). Editorial, not
# derived - kept short per the spike ("5 most-common pages"). Validated by the
# internal_link guard because they render as real links on every page.
DEFAULT_QUICK_LINKS = [
    {"label": "Installation", "path": "/docs/getting_started/installation/"},
    {"label": "Your first component", "path": "/docs/getting_started/your_first_component/"},
    {"label": "Adding slots", "path": "/docs/getting_started/adding_slots/"},
    {"label": "Adding JS and CSS", "path": "/docs/getting_started/adding_js_and_css/"},
    {"label": "Examples", "path": "/examples/"},
]

# Where search.js dynamically imports the Pagefind bundle from. Absolute from the
# site root, matching the non-versioned build; per-version search (Phase 5b) can
# override this kwarg to point at /v/<version>/pagefind/pagefind.js.
DEFAULT_PAGEFIND_PATH = "/pagefind/pagefind.js"


@register("search_modal")
class SearchModal(Component):
    class Kwargs:
        quick_links: list = DEFAULT_QUICK_LINKS
        pagefind_path: str = DEFAULT_PAGEFIND_PATH

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict:
        return {
            "quick_links": kwargs.quick_links,
            "pagefind_path": kwargs.pagefind_path,
        }

    template: types.django_html = """
        {# data-pagefind-ignore: belt-and-suspenders so the search UI is never
           indexed (it is already outside the data-pagefind-body region). #}
        <div class="djc-search" data-pagefind-ignore>
            <div
                class="djc-search__overlay"
                data-pagefind-path="{{ pagefind_path }}"
                hidden
            >
                {# Click-to-dismiss backdrop behind the dialog #}
                <div class="djc-search__backdrop" data-search-close></div>

                <div
                    class="djc-search__dialog"
                    id="djc-search-dialog"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Search documentation"
                >
                    {# Input bar #}
                    <div class="djc-search__inputbar">
                        <svg
                            class="djc-search__input-icon"
                            viewBox="0 0 24 24"
                            width="18"
                            height="18"
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
                        <input
                            type="search"
                            class="djc-search__input"
                            placeholder="Search the docs…"
                            autocomplete="off"
                            autocorrect="off"
                            autocapitalize="off"
                            spellcheck="false"
                            aria-label="Search documentation"
                            aria-controls="djc-search-results"
                        >
                        <button class="djc-search__esc" type="button" data-search-close aria-label="Close search">Esc</button>
                    </div>

                    {# Results region; search.js swaps between these states #}
                    <div class="djc-search__results" id="djc-search-results" role="listbox" aria-label="Search results">
                        {# Empty state: popular pages before the user types #}
                        <div class="djc-search__empty" data-search-empty>
                            <div class="djc-search__section-label">Popular pages</div>
                            <ul class="djc-search__quicklinks">
                                {% for link in quick_links %}
                                <li>
                                    <a class="djc-search__quicklink" href="{{ link.path }}">{{ link.label }}</a>
                                </li>
                                {% endfor %}
                            </ul>
                        </div>

                        {# No-results state #}
                        <div class="djc-search__message" data-search-noresults hidden></div>

                        {# Error state (Pagefind failed to load) #}
                        <div class="djc-search__message" data-search-error hidden></div>

                        {# Live results injected here by search.js #}
                        <div class="djc-search__list" data-search-list></div>
                    </div>

                    {# Keyboard help footer #}
                    <div class="djc-search__footer">
                        <span class="djc-search__hint"><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
                        <span class="djc-search__hint"><kbd>↵</kbd> select</span>
                        <span class="djc-search__hint"><kbd>esc</kbd> close</span>
                    </div>
                </div>
            </div>
        </div>
    """
