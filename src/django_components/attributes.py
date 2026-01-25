# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py  # noqa: E501
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py  # noqa: E501

import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeAlias

from django.template import Context
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString, mark_safe

from django_components.node import BaseNode

ClassValue: TypeAlias = Sequence["ClassValue"] | str | dict[str, bool]
StyleDict: TypeAlias = dict[str, str | int | Literal[False] | None]
StyleValue: TypeAlias = Sequence["StyleValue"] | str | StyleDict


class HtmlAttrsNode(BaseNode):
    """
    Generate HTML attributes (`key="value"`), combining data from multiple sources,
    whether its template variables or static text.

    It is designed to easily merge HTML attributes passed from outside as well as inside the component.

    **Args:**

    - `attrs` (dict, optional): Optional dictionary that holds HTML attributes. On conflict, overrides
        values in the `default` dictionary.
    - `default` (str, optional): Optional dictionary that holds HTML attributes. On conflict, is overriden
        with values in the `attrs` dictionary.
    - Any extra kwargs will be appended to the corresponding keys

    The attributes in `attrs` and `defaults` are merged and resulting dict is rendered as HTML attributes
    (`key="value"`).

    Extra kwargs (`key=value`) are concatenated to existing keys. So if we have

    ```python
    attrs = {"class": "my-class"}
    ```

    Then

    ```django
    {% html_attrs attrs class="extra-class" %}
    ```

    will result in `class="my-class extra-class"`.

    **Example:**
    ```django
    <div {% html_attrs
        attrs
        defaults:class="default-class"
        class="extra-class"
        data-id="123"
    %}>
    ```

    renders

    ```html
    <div class="my-class extra-class" data-id="123">
    ```

    See more usage examples in
    [HTML attributes](../concepts/fundamentals/html_attributes.md).
    """

    tag = "html_attrs"
    end_tag = None  # inline-only
    allowed_flags = ()

    def render(
        self,
        context: Context,  # noqa: ARG002
        attrs: dict | None = None,
        defaults: dict | None = None,
        **kwargs: Any,
    ) -> SafeString:
        # Merge
        final_attrs = {}
        final_attrs.update(defaults or {})
        final_attrs.update(attrs or {})
        final_attrs = merge_attributes(final_attrs, kwargs)

        # Render to HTML attributes
        return format_attributes(final_attrs)


def format_attributes(attributes: Mapping[str, Any]) -> str:
    """
    Format a dict of attributes into an HTML attributes string.

    Read more about [HTML attributes](../concepts/fundamentals/html_attributes.md).

    **Example:**

    ```python
    format_attributes({"class": "my-class", "data-id": "123"})
    ```

    will return

    ```py
    'class="my-class" data-id="123"'
    ```
    """
    attr_list = []

    for key, value in attributes.items():
        if value is None or value is False:
            continue
        if value is True:
            attr_list.append(conditional_escape(key))
        else:
            attr_list.append(format_html('{}="{}"', key, value))

    return mark_safe(SafeString(" ").join(attr_list))


# TODO_V1 - Remove in v1, keep only `format_attributes` going forward
attributes_to_string = format_attributes
"""
Deprecated. Use [`format_attributes`](api.md#django_components.format_attributes) instead.
"""


def merge_attributes(*attrs: dict) -> dict:
    """
    Merge a list of dictionaries into a single dictionary.

    The dictionaries are treated as HTML attributes and are merged accordingly:

    - If a same key is present in multiple dictionaries, the values are joined with a space
      character.
    - The `class` and `style` keys are handled specially, similar to
      [how Vue does it](https://vuejs.org/api/render-function#mergeprops).

    Read more about [HTML attributes](../concepts/fundamentals/html_attributes.md).

    **Example:**

    ```python
    merge_attributes(
        {"my-attr": "my-value", "class": "my-class"},
        {"my-attr": "extra-value", "data-id": "123"},
    )
    ```

    will result in

    ```python
    {
        "my-attr": "my-value extra-value",
        "class": "my-class",
        "data-id": "123",
    }
    ```

    **The `class` attribute**

    The `class` attribute can be given as a string, or a dictionary.

    - If given as a string, it is used as is.
    - If given as a dictionary, only the keys with a truthy value are used.

    **Example:**

    ```python
    merge_attributes(
        {"class": "my-class extra-class"},
        {"class": {"truthy": True, "falsy": False}},
    )
    ```

    will result in

    ```python
    {
        "class": "my-class extra-class truthy",
    }
    ```

    **The `style` attribute**

    The `style` attribute can be given as a string, a list, or a dictionary.

    - If given as a string, it is used as is.
    - If given as a dictionary, it is converted to a style attribute string.

    **Example:**

    ```python
    merge_attributes(
        {"style": "color: red; background-color: blue;"},
        {"style": {"background-color": "green", "color": False}},
    )
    ```

    will result in

    ```python
    {
        "style": "color: red; background-color: blue; background-color: green;",
    }
    ```
    """
    result: dict = {}

    classes: list[ClassValue] = []
    styles: list[StyleValue] = []
    for attrs_dict in attrs:
        for key, value in attrs_dict.items():
            if key == "class":
                classes.append(value)
            elif key == "style":
                styles.append(value)
            elif key in result:
                # Other keys are concatenated with a space character as separator
                # if given multiple times.
                result[key] = str(result[key]) + " " + str(value)
            else:
                result[key] = value

    # Style and class have special handling based on how Vue does it.
    if classes:
        result["class"] = normalize_class(classes)
    if styles:
        result["style"] = normalize_style(styles)

    return result


def normalize_class(value: ClassValue) -> str:
    """
    Normalize a class value.

    Class may be given as a string, a list, or a dictionary:

    - If given as a string, it is used as is.
    - If given as a dictionary, only the keys with a truthy value are used.
    - If given as a list, each item is converted to a dict, the dicts are merged, and resolved as above.

    If a class is given multiple times, the last value is used.

    This is based on Vue's [`mergeProps` function](https://vuejs.org/api/render-function#mergeprops).

    **Example:**

    ```python
    normalize_class([
        "my-class other-class",
        {"extra-class": True, "other-class": False}
    ])
    ```

    will result in
    ```python
    "my-class extra-class"
    ```

    Where:
    - `my-class` is used as is
    - `extra-class` is used because it has a truthy value
    - `other-class` is ignored because it's last value is falsy
    """
    res: dict[str, bool] = {}
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        # List items may be strings, dicts, or other lists/tuples
        for item in value:
            # NOTE: One difference from Vue is that if a class is given multiple times,
            # and the last value is falsy, then it will be removed.
            # E.g.
            # `{"class": ["my-class", "extra-class", {"extra-class": False}]}`
            # will result in `class="my-class"`
            # while in Vue it will result in `class="my-class extra-class"`
            normalized = _normalize_class(item)
            res.update(normalized)
    elif isinstance(value, dict):
        # Take only those keys whose value is truthy. So
        # `{"class": True, "extra": False}` will result in `class="extra"`
        # while
        # `{"class": True, "extra": True}` will result in `class="class extra"`
        res = value
    else:
        raise TypeError(f"Invalid class value: {value}")

    res_str = ""
    for key, val in res.items():
        if val:
            res_str += key + " "
    return res_str.strip()


whitespace_re = re.compile(r"\s+")


# Similar to `normalize_class`, but returns a dict instead of a string.
def _normalize_class(value: ClassValue) -> dict[str, bool]:
    res: dict[str, bool] = {}
    if isinstance(value, str):
        class_parts = whitespace_re.split(value)
        res.update({part: True for part in class_parts if part})
    elif isinstance(value, (list, tuple)):
        # List items may be strings, dicts, or other lists/tuples
        for item in value:
            normalized = _normalize_class(item)
            res.update(normalized)
    elif isinstance(value, dict):
        res = value
    else:
        raise TypeError(f"Invalid class value: {value}")
    return res


def normalize_style(value: StyleValue) -> str:
    """
    Normalize a style value.

    Style may be given as a string, a list, or a dictionary:

    - If given as a string, it is parsed as an inline CSS style,
      e.g. `"color: red; background-color: blue;"`.
    - If given as a dictionary, it is assumed to be a dict of style properties,
      e.g. `{"color": "red", "background-color": "blue"}`.
    - If given as a list, each item may itself be a list, string, or a dict.
      The items are converted to dicts and merged.

    If a style property is given multiple times, the last value is used.

    If, after merging, a style property has a literal `False` value, it is removed.

    Properties with a value of `None` are ignored.

    This is based on Vue's [`mergeProps` function](https://vuejs.org/api/render-function#mergeprops).

    **Example:**

    ```python
    normalize_style([
        "color: red; background-color: blue; width: 100px;",
        {"color": "green", "background-color": None, "width": False},
    ])
    ```

    will result in
    ```python
    "color: green; background-color: blue;"
    ```

    Where:
    - `color: green` overwrites `color: red`
    - `background-color": None` is ignored, so `background-color: blue` is used
    - `width` is omitted because it is given with a `False` value
    """
    res: StyleDict = {}
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        # List items may be strings, dicts, or other lists/tuples
        for item in value:
            normalized = _normalize_style(item)
            res.update(normalized)
    elif isinstance(value, dict):
        # Remove entries with `None` value
        res = _normalize_style(value)
    else:
        raise TypeError(f"Invalid style value: {value}")

    # By the time we get here, all `None` values have been removed.
    # If the final dict has `None` or `False` values, they are removed, so those
    # properties are not rendered.
    res_parts = []
    for key, val in res.items():
        if val is not None and val is not False:
            res_parts.append(f"{key}: {val};")
    return " ".join(res_parts).strip()


def _normalize_style(value: StyleValue) -> StyleDict:
    res: StyleDict = {}
    if isinstance(value, str):
        # Generate a dict of style properties from a string
        normalized = parse_string_style(value)
        res.update(normalized)
    elif isinstance(value, (list, tuple)):
        # List items may be strings, dicts, or other lists/tuples
        for item in value:
            normalized = _normalize_style(item)
            res.update(normalized)
    elif isinstance(value, dict):
        # Skip assigning entries with `None` value
        for key, val in value.items():
            if val is not None:
                res[key] = val
    else:
        raise TypeError(f"Invalid style value: {value}")
    return res


# Match CSS comments `/* ... */`
style_comment_re = re.compile(r"/\*.*?\*/", re.DOTALL)
# Split CSS properties by semicolon, but not inside parentheses
list_delimiter_re = re.compile(r";(?![^(]*\))", re.DOTALL)
# Split CSS property name and value
property_delimiter_re = re.compile(r":(.+)", re.DOTALL)


def parse_string_style(css_text: str) -> StyleDict:
    """
    Parse a string of CSS style properties into a dictionary.

    **Example:**

    ```python
    parse_string_style("color: red; background-color: blue; /* comment */")
    ```

    will result in

    ```python
    {"color": "red", "background-color": "blue"}
    ```
    """
    # Remove comments
    css_text = style_comment_re.sub("", css_text)

    ret: StyleDict = {}

    # Split by semicolon, but not inside parentheses
    for item in list_delimiter_re.split(css_text):
        if item:
            parts = property_delimiter_re.split(item)
            if len(parts) > 1:
                ret[parts[0].strip()] = parts[1].strip()
    return ret
