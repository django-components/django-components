"""
Docstring -> HTML rendering (feature 4.38, ``DocstringBody``).

Converts a griffe docstring value to HTML. The value arrives already enriched by
the griffe extensions (a ``Bases: ...`` line and a "See source code" link
prepended as raw HTML), so the markdown converter must allow raw block HTML to
pass through - which ``md_in_html`` does. Bracket cross-refs are resolved first,
while the content is still markdown.

This is a function rather than a Django component: the work is a markdown
transform with no template surface, and keeping it callable makes it easy to
unit-test. It can be promoted to a component if template-level reuse appears.
"""

from __future__ import annotations

from apps.docs.components.reference.crossrefs import resolve_crossrefs


def render_docstring_html(value: str, *, current_url: str) -> tuple[str, list[str]]:
    """
    Render a docstring value to HTML.

    Returns the HTML and the list of unresolved cross-ref keys (for future
    forward-reference guards). An empty / whitespace-only value renders to "".
    """
    if not value or not value.strip():
        return "", []

    # Reuse the site's markdown extension set so docstrings get the same
    # treatment as page content (admonitions, code highlighting, md_in_html for
    # the extensions' raw HTML, etc.).
    import markdown  # type: ignore[import-untyped]  # noqa: PLC0415  # python-markdown ships no stubs
    from apps.docs.build.pipeline import MD_EXTENSION_CONFIGS, MD_EXTENSIONS  # noqa: PLC0415

    md_text, unresolved = resolve_crossrefs(value, current_url=current_url)
    md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=dict(MD_EXTENSION_CONFIGS))
    return md.convert(md_text), unresolved
