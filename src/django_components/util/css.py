import re

CSS_FUNC_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\(")


def is_css_func(value: str) -> bool:
    """
    Check if a string value is a CSS function call.

    CSS functions follow the pattern: one or more alphanumeric characters (or hyphens/underscores)
    followed by an opening parenthesis.

    **Examples:**

    - `calc(100% - 20px)` -> True
    - `var(--color)` -> True
    - `rgba(255, 0, 0, 0.5)` -> True
    - `linear-gradient(to right, red, blue)` -> True
    - `Hello World` -> False
    - `red` -> False
    """
    return bool(CSS_FUNC_PATTERN.match(value.strip()))


def serialize_css_var_value(value: str | float | None) -> str:
    """
    Serialize a CSS variable value to a valid CSS string.

    - Numbers (int, float) are converted to strings without quotes
    - Strings are kept as-is (CSS handles quoting automatically for most cases)
    - None is converted to empty string
    - Special handling for values that need quoting (contain spaces, special chars)
    """
    if value is None:
        return ""

    # Convert to string
    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        # If the string contains spaces or special characters that might break CSS,
        # we should quote it. However, most CSS values (colors, sizes, etc.) don't need quotes.
        # CSS will handle most values correctly without quotes.
        # Only quote if it looks like it might be problematic (contains spaces and isn't a CSS function)
        if " " in value and not is_css_func(value):
            return f'"{value}"'
        return value

    # For other types, convert to string
    return str(value)
