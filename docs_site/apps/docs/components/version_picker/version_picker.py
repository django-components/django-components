"""
VersionPicker - the header docs-version dropdown (Phase 5b, feature 5b.11).

Renders a native ``<select>`` seeded with the version the current page was built
as. The behavior (fetch versions.json, populate the other versions, redirect on
change) lives in static/js/site.js, keyed off the ``data-version-picker``
attribute - the same markup-only + site.js split the theme picker and overflow
menu use.

Why a native ``<select>``: it is keyboard- and screen-reader-accessible for
free, and it degrades gracefully - if there's no manifest to fetch, the control
just shows the current version and does nothing.

Populating the dropdown on the **root** pages (the current docs, not just the
``/v/<version>/`` archives) is an intentional, wanted feature - keep it. site.js
finds the manifest two ways: on a ``/v/<version>/`` page from that path prefix;
on other pages from the ``data-versions-root`` attribute that ``docs_assemble``
injects. That attribute is set ONLY by ``docs_assemble`` (the builder that
actually produces ``/v/versions.json``), so a plain ``build_docs`` site - local
preview, the Lighthouse build - has no attribute, doesn't fetch, and so never
404s on a manifest that isn't there. Both paths are base-path agnostic (e.g. the
``/django-components/`` GitHub Pages prefix) without baking in an absolute URL.

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
