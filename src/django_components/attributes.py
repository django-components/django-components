# Initial implementation based on attributes.py from django-web-components
# See https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/templatetags/components.py  # noqa: E501
# And https://github.com/Xzya/django-web-components/blob/b43eb0c832837db939a6f8c1980334b0adfdd6e4/django_web_components/attributes.py  # noqa: E501

import re
from collections.abc import Iterator, Mapping, Sequence
from functools import lru_cache
from typing import Any, Literal, TypeAlias

from django.template import Context
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString, mark_safe

from django_components.node import BaseNode

ClassValue: TypeAlias = Sequence["ClassValue"] | str | dict[str, bool]
StyleDict: TypeAlias = dict[str, str | int | Literal[False] | None]
StyleValue: TypeAlias = Sequence["StyleValue"] | str | StyleDict
AttrsSource: TypeAlias = Mapping[str, Any] | list["AttrsSource"] | tuple["AttrsSource", ...]

_INVALID_HTML_ATTR_NAME_CHARS = frozenset(" \t\n\r=/><")


class HtmlAttrsNode(BaseNode):
    """
    Generate HTML attributes (`key="value"`), combining data from multiple sources,
    whether its template variables or static text.

    It is designed to easily merge HTML attributes passed from outside as well as inside the component.

    Args:
        attrs (dict, optional): Optional dictionary that holds HTML attributes. On conflict, overrides
            values in the `default` dictionary.
        default (str, optional): Optional dictionary that holds HTML attributes. On conflict, is overriden
            with values in the `attrs` dictionary.
        **kwargs: Any extra kwargs will be appended to the corresponding keys.

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

    Examples:
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


class AttrsDict(dict[str, Any]):
    """
    Reuse composed HTML attributes as both a dictionary and rendered markup.

    You will usually create an `AttrsDict` with [`compose_attrs()`][compose_attrs]
    in Python or the [`{% attrs %}`][attrs] template tag. Use it like a regular
    dictionary when passing attributes to a component, reading values, or unpacking
    keyword arguments:

    ```python
    attrs = compose_attrs(
        {"id": "save", "class": "button"},
        {"class": {"active": True}},
    )

    attrs["id"]
    # "save"

    str(attrs)
    # 'id="save" class="button active"'
    ```

    In a component template, pass the native dictionary by using `{% attrs %}` as
    the only node in a quoted input:

    ```django
    {% component "table" table_attrs="{% attrs base_attrs local_attrs %}" / %}
    ```

    Unlike `{% html_attrs %}`, these APIs produce a reusable native dictionary in
    addition to rendering attributes. `AttrsDict`,
    [`compose_attrs()`][compose_attrs], and `{% attrs %}` supersede
    `{% html_attrs %}` for attribute composition. Prefer the new APIs in new code;
    `{% html_attrs %}` remains supported for backward compatibility.
    """

    # Do not implement Django's __html__ trusted-markup protocol here. The
    # standalone tag marks its already-escaped output safe, while an AttrsDict
    # reused as an attribute value must still be escaped for that outer context.
    def __str__(self) -> str:
        return str(format_attributes(self))


class AttrsNode(BaseNode):
    """
    Compose mappings into an attribute dictionary and render it as HTML attributes.

    Each argument may be a mapping or an arbitrarily nested list or tuple of
    mappings. Sources are applied from left to right. Ordinary attributes use the
    last value, while `class` and `style` contributions are combined using the same
    structured values as [`normalize_class()`][normalize_class] and
    [`normalize_style()`][normalize_style].

    ```django
    <div {% attrs [base_attrs, [state_attrs]] local_attrs %}></div>
    ```

    When the tag is the sole node in a nested template expression, it returns an
    [`AttrsDict`][AttrsDict] without serializing it. This makes it possible to pass
    the result directly to a component:

    ```django
    {% component "table"
        table_attrs="{% attrs [base_attrs, {'class': 'compact'}] %}"
    / %}
    ```

    Any surrounding text or template nodes cause the result to be serialized to
    an escaped, space-delimited attribute string.

    This tag supersedes `{% html_attrs %}` for attribute composition. Prefer
    `{% attrs %}` in new code; `{% html_attrs %}` remains supported for backward
    compatibility.

    See [HTML attributes](../concepts/fundamentals/html_attributes.md) for details.
    """

    tag = "attrs"
    end_tag = None
    allowed_flags = ()

    # BaseNode declares Django's string-only render contract. This tag intentionally
    # returns a native value when called directly by TemplateExpression.
    def render(self, context: Context, *attrs: AttrsSource) -> AttrsDict:  # type: ignore[override]  # noqa: ARG002
        return compose_attrs(*attrs)

    def render_annotated(self, context: Context) -> SafeString:
        # Django's NodeList requires every node to render a string, while a direct
        # render() call must retain AttrsDict for nested template expressions. Keep
        # string conversion inside Django's exception annotation boundary so errors
        # raised while formatting still point to this tag in debug mode.
        try:
            return mark_safe(str(self.render(context)))
        except Exception as err:
            if context.template.engine.debug:
                culprit_node = getattr(err, "_culprit_node", None)
                if culprit_node is None:
                    culprit_node = self
                    err._culprit_node = culprit_node  # type: ignore[attr-defined]
                if (
                    not hasattr(err, "template_debug")
                    and context.render_context.template.origin == culprit_node.origin
                ):
                    template_debug = context.render_context.template.get_exception_info(err, culprit_node.token)
                    err.template_debug = template_debug  # type: ignore[attr-defined]
            raise


def compose_attrs(*attrs: AttrsSource) -> AttrsDict:
    """
    Compose HTML attribute mappings from left to right.

    Arguments may be mappings or arbitrarily nested lists or tuples whose terminal
    values are mappings. Ordinary keys use the last value without changing their
    first-seen order. All `class` and `style` values are collected and normalized,
    so each source can contribute classes and style properties independently.

    `None` contributes nothing to `class` and `style`. As with ordinary HTML
    attributes, `None` and `False` values are omitted when the returned
    [`AttrsDict`][AttrsDict] is rendered, while `True` renders a bare attribute.

    Unlike the legacy [`merge_attributes()`][merge_attributes], this function does
    not join collisions for ordinary attributes with spaces.

    Examples:
        ```python
        compose_attrs(
            [{"id": "first", "class": "button"}, [{"class": {"active": True}}]],
            {"id": "last"},
        )
        # == {"id": "last", "class": "button active"}
        ```

    Raises:
        TypeError: If a terminal value is not a mapping, or an attribute name is
            not a string.
        ValueError: If the source containers are cyclic, or an attribute name is
            invalid.

    """
    result = AttrsDict()
    classes: list[ClassValue] = []
    styles: list[StyleValue] = []

    for attrs_dict in _iter_attr_mappings(attrs):
        for authored_key, value in attrs_dict.items():
            key = _validate_html_attr_name(authored_key)

            if key == "class":
                # Reserve the key's first-seen position even when this source has
                # no contribution. Empty normalized class values are retained in
                # the mapping and omitted only while formatting.
                result.setdefault(key, None)
                if value is not None:
                    classes.append(value)
            elif key == "style":
                result.setdefault(key, None)
                if value is not None:
                    styles.append(value)
            else:
                result[key] = value

    if classes:
        result["class"] = normalize_class(classes)
    if styles:
        result["style"] = normalize_style(styles)

    return result


def _iter_attr_mappings(sources: Sequence[AttrsSource]) -> Iterator[Mapping[str, Any]]:
    # Use an explicit stack so supported nesting depth is not constrained by
    # Python's recursion limit. Exit markers distinguish a real cycle from the
    # same list or tuple being reused in separate branches.
    stack: list[tuple[AttrsSource, bool]] = [(source, False) for source in reversed(sources)]
    active_container_ids: set[int] = set()

    while stack:
        source, is_exit = stack.pop()
        if is_exit:
            active_container_ids.remove(id(source))
            continue

        if isinstance(source, Mapping):
            yield source
            continue

        if not isinstance(source, (list, tuple)):
            msg = (
                "compose_attrs() arguments must be a mapping or a nested list or tuple of mappings; "
                f"got {type(source).__name__}"
            )
            raise TypeError(msg)

        source_id = id(source)
        if source_id in active_container_ids:
            raise ValueError("compose_attrs() source containers cannot contain a cycle")

        active_container_ids.add(source_id)
        stack.append((source, True))
        stack.extend((item, False) for item in reversed(source))


def format_attributes(attributes: Mapping[str, Any]) -> str:
    """
    Format a mapping of attributes into an HTML attributes string.

    Attribute names must be strings and valid HTML attribute names. `class`
    and `style` accept structured values and are normalized before rendering.
    Empty normalized `class` and `style` values are omitted.

    Read more about [HTML attributes](../concepts/fundamentals/html_attributes.md).

    Examples:
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
        key = _validate_html_attr_name(key)  # noqa: PLW2901

        if key == "class" and value is not None:
            if not isinstance(value, str):
                value = normalize_class(value)  # noqa: PLW2901
            if not value:
                continue
        elif key == "style" and value is not None:
            if not isinstance(value, str):
                value = normalize_style(value)  # noqa: PLW2901
            if not value:
                continue

        if value is None or value is False:
            continue
        if value is True:
            attr_list.append(conditional_escape(key))
        else:
            attr_list.append(format_html('{}="{}"', key, value))

    return mark_safe(SafeString(" ").join(attr_list))


@lru_cache(maxsize=512)
def _is_valid_exact_html_attr_name(name: str) -> bool:
    return bool(name) and not any(char in _INVALID_HTML_ATTR_NAME_CHARS for char in name) and "{#" not in name


def _validate_html_attr_name(name: Any) -> str:
    if not isinstance(name, str):
        msg = f"HTML attributes must use string attribute names, got {type(name).__name__} key {name!r}."
        raise TypeError(msg)

    # Convert subclasses to an exact string without invoking custom __str__
    # behavior, and never retain arbitrary subclasses in the shared cache.
    exact_name = name if type(name) is str else str.__str__(name)
    if not _is_valid_exact_html_attr_name(exact_name):
        msg = (
            f"HTML attributes contain invalid HTML attribute name {exact_name!r}. Attribute names must be non-empty "
            "and cannot contain whitespace, '=', '/', '>', '<', or the template-comment opener '{#'."
        )
        raise ValueError(msg)

    # A str subclass can customize __str__ or Django's __html__ trusted-markup
    # protocol. Reject a name whose formatted representation differs from its
    # actual string value instead of silently discarding or rendering that payload.
    if type(name) is not str:
        rendered_name = str(conditional_escape(name))
        expected_name = str(conditional_escape(exact_name))
        if rendered_name != expected_name:
            msg = (
                f"HTML attributes contain invalid HTML attribute name {rendered_name!r}. Attribute name objects must "
                "render exactly as their string value and cannot contain whitespace, '=', '/', '>', '<', or the "
                "template-comment opener '{#'."
            )
            raise ValueError(msg)

    return exact_name


# TODO_V1 - Remove in v1, keep only `format_attributes` going forward
attributes_to_string = format_attributes
"""
Deprecated. Use [`format_attributes`][format_attributes] instead.
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

    Examples:
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

    Examples:
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

    Examples:
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

    Examples:
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

    Examples:
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

    Examples:
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
