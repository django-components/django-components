"""
Custom template tags for use in markdown docs pages.

These tags are auto-loaded in Pass 1 of the pipeline via
{% load docs_extras %} and are available in any markdown file.
They're the "docs sugar" layer described in design doc section 11.4.D.

Tags defined here are Django simple_tags that return HTML strings.
They run during Pass 1 (Django template expansion), before markdown
conversion in Pass 2.
"""

from __future__ import annotations

from pathlib import Path

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def example(name: str) -> str:
    """
    Embed a tabbed example widget (Component code / Page code / Live demo).

    Usage in markdown: {% example "fragments" %}
    """
    from apps.docs.components.example_card.example_card import ExampleCard  # noqa: PLC0415
    from apps.docs.examples import get_example_registry  # noqa: PLC0415

    registry = get_example_registry()
    if name not in registry:
        return f'<p class="error">Unknown example: {escape(name)}</p>'
    info = registry[name]
    result = ExampleCard.render(kwargs={"name": name, "info": info})
    # Strip leading whitespace from the component output so python-markdown
    # sees block-level HTML at column 0 (4+ spaces = code block in markdown).
    # But preserve whitespace inside <pre> blocks where it's significant
    # (Pygments uses raw leading spaces for code indentation).
    result = _lstrip_outside_pre(result)
    return mark_safe(f"\n\n{result}\n\n")


@register.simple_tag(takes_context=True)
def docstring(context: template.Context, path: str) -> str:
    """
    Render the API reference for one public symbol.

    Resolves `path` (e.g. "django_components.AlreadyRegistered") against the
    discovered reference entries and renders it with the matching per-kind
    component. This is the direct analog of the old mkdocstrings `::: path`
    directive (feature 4.57).

    Usage in markdown: {% docstring "django_components.Component" %}
    """
    from apps.docs.reference.discovery.registry import entry_index  # noqa: PLC0415
    from apps.docs.reference.render import render_entry  # noqa: PLC0415

    entry = entry_index().get(path)
    if entry is None:
        return mark_safe(f'<p class="error">Unknown reference symbol: {escape(path)}</p>')

    html = render_entry(entry, current_url=context.get("current_path", ""))
    # Flush-left + blank-line padding so python-markdown treats the output as
    # block-level HTML (same treatment as {% example %} / {% people %}).
    html = _lstrip_outside_pre(html)
    return mark_safe(f"\n\n{html}\n\n")


@register.simple_tag
def people(group: str) -> str:
    """
    Render the avatar grid for a group of people from community/people.yml.

    Replaces the old mkdocs-macros Jinja loop in community/people.md. The
    contributor grid also shows each person's merged-PR count.

    Usage in markdown: {% people "maintainers" %} or {% people "contributors" %}
    """
    import yaml  # type: ignore[import-untyped]  # noqa: PLC0415
    from django.conf import settings  # noqa: PLC0415

    from apps.docs.components.user_grid.user_grid import UserGrid  # noqa: PLC0415

    people_path = settings.CONTENT_DIR / "docs" / "community" / "people.yml"
    if not people_path.is_file():
        return f'<p class="error">People data not found: {escape(str(people_path))}</p>'

    data = yaml.safe_load(people_path.read_text(encoding="utf-8")) or {}
    users = data.get(group)
    if users is None:
        return f'<p class="error">Unknown people group: {escape(group)}</p>'

    result = UserGrid.render(kwargs={"users": users, "show_count": group == "contributors"})
    # Flush-left + blank-line padding so python-markdown treats the output
    # as block-level HTML (same treatment as the {% example %} tag).
    result = _lstrip_outside_pre(result)
    return mark_safe(f"\n\n{result}\n\n")


@register.simple_tag
def version() -> str:
    """
    Return the current django-components version.

    Usage in markdown: {% version %}
    Output: e.g. "0.150.1"
    """
    from importlib.metadata import version as get_version  # noqa: PLC0415

    return get_version("django_components")


@register.simple_tag
def include_file(path: str, language: str = "") -> str:
    """
    Include a file's contents as a fenced code block.

    The language for syntax highlighting is inferred from the file extension
    if not explicitly provided. The output is a markdown fenced code block
    that Pass 2 will convert to highlighted HTML.

    Usage in markdown: {% include_file "path/to/file.py" %}
    Usage with explicit language: {% include_file "path/to/file" language="python" %}
    """
    file_path = Path(path)
    if not file_path.exists():
        return f'<p class="error">File not found: {escape(path)}</p>'

    content = file_path.read_text(encoding="utf-8")
    if not language:
        language = _ext_to_language(file_path.suffix)

    # Return a markdown fenced code block - Pass 2 will highlight it
    return f"\n```{language}\n{content}\n```\n"


@register.simple_tag
def image(src: str, alt: str = "", width: str = "", css_class: str = "") -> str:
    """
    Render an image tag with optional width and CSS class.

    Provides a consistent wrapper around <img> for docs pages. Markdown's
    native ![alt](src) syntax also works - this tag is sugar for cases
    that need width constraints or CSS classes.

    Usage: {% image "path/to/img.png" alt="Screenshot" width="400" %}
    """
    attrs = [f'src="{escape(src)}"', f'alt="{escape(alt)}"']
    if width:
        attrs.append(f'width="{escape(width)}"')
    if css_class:
        attrs.append(f'class="{escape(css_class)}"')
    return f"<img {' '.join(attrs)}>"


_EXT_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".html": "html",
    ".css": "css",
    ".sh": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
}


def _ext_to_language(ext: str) -> str:
    return _EXT_MAP.get(ext.lower(), "text")


def _lstrip_outside_pre(html: str) -> str:
    """
    Strip leading whitespace from HTML lines, but preserve it inside <pre>.

    Django templates add indentation to rendered output. Markdown treats
    4+ leading spaces as a code block, so outer HTML must be flush-left.
    But whitespace inside <pre> is significant (Pygments uses raw spaces
    for code indentation), so those lines must stay untouched.
    """
    lines = html.splitlines()
    result = []
    in_pre = False
    for line in lines:
        if not in_pre and ("<pre>" in line or "<pre " in line):
            in_pre = True
        if in_pre:
            result.append(line)
        else:
            result.append(line.lstrip())
        if in_pre and "</pre>" in line:
            in_pre = False
    return "\n".join(result)
