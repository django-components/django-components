"""
VersionPicker - the header docs-version dropdown (Phase 5b, feature 5b.11).

Renders a native ``<select>`` seeded with the version the current page was built
as. The behavior (fetch versions.json, populate the other versions, redirect on
change) lives in static/js/site.js, keyed off the ``data-version-picker``
attribute - the same markup-only + site.js split the theme picker and overflow
menu use.

Why a native ``<select>``: it is keyboard- and screen-reader-accessible for
free, and it degrades gracefully. If the page isn't served under a
``/v/<version>/`` prefix (e.g. the local dev server, where versions aren't
mounted) or the manifest can't be fetched, the control just shows the current
version and does nothing.

The manifest URL and the redirect target are derived client-side from the
page's own ``/v/<version>/`` path prefix, so the picker works regardless of the
site's base path (e.g. the ``/django-components/`` GitHub Pages prefix) without
the build baking in an absolute URL.

Spec: docs_site/design/DESIGN_spike_7.md section 5; main doc section 4.6.
"""

from __future__ import annotations

from typing import Any

from django_components import Component, register, types


@register("version_picker")
class VersionPicker(Component):
    class Kwargs:
        current_version: str = ""

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict:
        return {"current_version": kwargs.current_version}

    template: types.django_html = """
        {% if current_version %}
        <div class="djc-version-picker" data-version-picker data-current="{{ current_version }}">
            <select class="djc-version-picker__select" aria-label="Choose docs version">
                {# Seed: replaced by site.js with the full list once versions.json loads. #}
                <option value="{{ current_version }}" selected>{{ current_version }}</option>
            </select>
            <svg
                class="djc-version-picker__caret"
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
            >
                <polyline points="6 9 12 15 18 9"/>
            </svg>
        </div>
        {% endif %}
    """
