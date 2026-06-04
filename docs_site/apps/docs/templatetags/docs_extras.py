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
