"""
NotFoundPage - the content of the custom 404 page (Phase 5a, feature 5a.6).

Renders the inner content for the 404: a short message, a prominent button that
opens the search modal, a list of popular destinations, and an issue link. The
builder (build/builder.py::generate_not_found) wraps this in DocPage chrome and
writes it to `<output>/404.html`, which GitHub Pages serves on any 404 within
the deployed path.

The headline itself is injected by DocPage from the page title ("Page not
found"), so this template starts below the H1. Destination links are absolute
on purpose: a 404 is served at arbitrary deep URLs, so relative links would
resolve against the wrong base.

Spec: docs_site/design/DESIGN_spike_12.md section 2.A.12.
"""

from __future__ import annotations

from typing import Any

from django_components import Component, register, types

# Top destinations for someone who hit a dead link. Absolute URLs (see module
# docstring). Rendered into 404.html, so the internal_link guard validates them.
DEFAULT_DESTINATIONS = [
    {"label": "Documentation home", "path": "/docs/"},
    {"label": "Getting started", "path": "/docs/getting_started/installation/"},
    {"label": "API reference", "path": "/docs/reference/"},
    {"label": "Examples", "path": "/examples/"},
]

DEFAULT_ISSUES_URL = "https://github.com/django-components/django-components/issues"


@register("not_found_page")
class NotFoundPage(Component):
    class Kwargs:
        destinations: list = DEFAULT_DESTINATIONS
        issues_url: str = DEFAULT_ISSUES_URL

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict:
        return {
            "destinations": kwargs.destinations,
            "issues_url": kwargs.issues_url,
        }

    template: types.django_html = """
        <p>The page you're looking for doesn't exist or may have moved.</p>

        <p>
            {# Opens the same search modal as the header trigger (search.js wires
               every [data-search-open]). #}
            <button class="djc-notfound__search" type="button" data-search-open>
                Search the documentation
            </button>
        </p>

        <h2>Popular destinations</h2>
        <ul>
            {% for dest in destinations %}
            <li><a href="{{ dest.path }}">{{ dest.label }}</a></li>
            {% endfor %}
        </ul>

        <p>
            If a page that recently existed is now missing,
            <a href="{{ issues_url }}" target="_blank" rel="noopener">open an issue</a>
            and we'll fix the link.
        </p>
    """
