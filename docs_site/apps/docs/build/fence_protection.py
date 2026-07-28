"""
Pre-pass: wrap code regions in {% verbatim %} before Django template rendering.

Without this pass, Django's template engine would try to execute {% component %}
or {{ variable }} tags that appear inside code fences as documentation examples.
The fix: wrap every code region in {% verbatim %}...{% endverbatim %} so Django
treats the content as literal text.

Handles:
- ``` and ~~~ fenced code blocks (including nested/escaped fences)
- `inline code` spans containing {% %} or {{ }} patterns

Does NOT handle 4-space indented code blocks (project convention: use fenced blocks).
"""

from __future__ import annotations

import re

# Matches the opening of a fenced code block: optional indent + 3+ backticks or tildes
FENCE_OPEN = re.compile(r"^(\s*)(```+|~~~+)")

# Matches inline backtick spans that contain Django template syntax
DJANGO_PATTERN_IN_INLINE = re.compile(r"`[^`]*(\{%|\{\{)[^`]*`")

# Each {% verbatim %} block gets a unique name so nested verbatim tags
# (e.g. a fence whose content demonstrates the verbatim tag itself) still work.
_VERBATIM_COUNTER = 0


def _next_verbatim_name() -> str:
    global _VERBATIM_COUNTER  # noqa: PLW0603
    _VERBATIM_COUNTER += 1
    return f"fence{_VERBATIM_COUNTER}"


def reset_counter() -> None:
    global _VERBATIM_COUNTER  # noqa: PLW0603
    _VERBATIM_COUNTER = 0


def protect_fences(source: str) -> str:
    """Wrap every fenced code block in {% verbatim name %}...{% endverbatim name %}."""
    lines = source.split("\n")
    out: list[str] = []
    in_fence = False
    fence_indent = ""
    fence_char = ""
    fence_len = 0
    verbatim_name = ""

    for line in lines:
        if not in_fence:
            m = FENCE_OPEN.match(line)
            if m:
                # Entering a fenced code block - record its indent and marker style
                # so we can match the closing fence correctly
                fence_indent = m.group(1)
                fence_marker = m.group(2)
                fence_char = fence_marker[0]  # "`" or "~"
                fence_len = len(fence_marker)  # typically 3, but can be more
                verbatim_name = _next_verbatim_name()
                out.append(f"{{% verbatim {verbatim_name} %}}")
                out.append(line)
                in_fence = True
                continue

            # Outside fences, protect any inline code spans that contain Django syntax
            out.append(_protect_inline_code(line))
        else:
            # Inside a fence - emit the line as-is (Django won't touch it)
            out.append(line)

            # Check if this line closes the fence: same char repeated at least
            # fence_len times, at the same or lesser indent, and NOT a longer
            # run of the same char (which would be a nested fence opener)
            stripped = line.lstrip()
            current_indent = line[: len(line) - len(stripped)]
            if (
                stripped.startswith(fence_char * fence_len)
                and not stripped.startswith(fence_char * (fence_len + 1))
                and len(current_indent) <= len(fence_indent)
            ):
                out.append(f"{{% endverbatim {verbatim_name} %}}")
                in_fence = False

    # Safety net: if the source has an unclosed fence, close the verbatim block
    if in_fence:
        out.append(f"{{% endverbatim {verbatim_name} %}}")

    return "\n".join(out)


def _protect_inline_code(line: str) -> str:
    """
    Wrap inline backtick spans containing Django syntax in {% verbatim %}.

    For example, `{% component "x" %}` in prose would otherwise be executed
    by Django in Pass 1. We wrap just the backtick span in verbatim so the
    template tag passes through as literal text, and markdown later renders
    it as <code>.
    """
    # Fast path: skip lines with no Django syntax in inline code
    if not DJANGO_PATTERN_IN_INLINE.search(line):
        return line

    result: list[str] = []
    i = 0
    while i < len(line):
        if line[i] == "`":
            # Find the closing backtick for this inline code span
            end = line.find("`", i + 1)
            if end == -1:
                # Unclosed backtick - emit the rest as-is
                result.append(line[i:])
                break
            span = line[i + 1 : end]
            if "{%" in span or "{{" in span:
                # This span contains Django syntax - wrap it in verbatim
                name = _next_verbatim_name()
                result.append(f"{{% verbatim {name} %}}`{span}`{{% endverbatim {name} %}}")
            else:
                result.append(f"`{span}`")
            i = end + 1
        else:
            result.append(line[i])
            i += 1

    return "".join(result)
