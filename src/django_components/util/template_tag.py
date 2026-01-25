"""
This file is for logic that focuses on transforming the AST of template tags
(as parsed from tag_parser) into a form that can be used by the Nodes.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from typing import (
    Any,
    NamedTuple,
    Protocol,
)

from django.template import NodeList, Variable, VariableDoesNotExist
from django.template.base import Parser, Token
from django.template.exceptions import TemplateSyntaxError
from djc_core.safe_eval import safe_eval
from djc_core.template_parser import GenericTag, ParserConfig, TagAttr, compile_tag, parse_tag
from djc_core.template_parser.parse import TagUnion

from django_components.expression import TemplateExpression


# Data obj to give meaning to the parsed tag fields
class ParsedTag(NamedTuple):
    start_tag_source: str
    flags: dict[str, bool]
    params: list[TagAttr]
    parse_body: Callable[[], tuple[NodeList, str | None]]


def parse_template_tag(
    tag: str,
    end_tag: str | None,
    tag_parser_config: ParserConfig,
    django_parser: Parser,
    token: Token,
) -> ParsedTag:
    # For better error messages, we add the enclosing `{% %}` to the tag contents.
    # So if parser encounters an error, it will include the enclosing `{% %}` in the error message.
    # E.g. `{% slot "content" default / %}` instead of just `slot "content" default /`
    start_tag_source = "{% " + token.contents + " %}"
    parsed_tag_info = parse_tag(start_tag_source, tag_parser_config)

    # Sanity checks
    parsed_tag_name = parsed_tag_info.meta.name.content
    if parsed_tag_name != tag:
        raise TemplateSyntaxError(f"Tag parser received tag '{parsed_tag_name}', expected '{tag}'")

    # There's 3 ways how we tell when a tag ends:
    # 1. If the tag contains `/` at the end, it's a self-closing tag (like `<div />`),
    #    and it doesn't have an end tag. In this case we strip the trailing slash.
    #
    # Otherwise, depending on the end_tag, the tag may be:
    # 2. Block tag - With corresponding end tag, e.g. `{% slot %}...{% endslot %}`
    # 3. Inlined tag - Without the end tag, e.g. `{% html_attrs ... %}`
    is_inline = isinstance(parsed_tag_info, GenericTag) and parsed_tag_info.is_self_closing

    tag_config = tag_parser_config.get_tag(tag)
    tag_allowed_flags = (tag_config and tag_config.get_flags()) or set()
    attrs = parsed_tag_info.attrs if isinstance(parsed_tag_info, GenericTag) else ()
    remaining_attrs, flags = _extract_flags(attrs, tag_allowed_flags)

    def _parse_tag_body(parser: Parser, end_tag: str, inline: bool) -> tuple[NodeList, str | None]:
        if inline:
            body = NodeList()
            contents: str | None = None
        else:
            contents = _extract_contents_until(parser, [end_tag])
            body = parser.parse(parse_until=[end_tag])
            parser.delete_first_token()
        return body, contents

    return ParsedTag(
        params=remaining_attrs,
        start_tag_source=start_tag_source,
        flags=flags,
        # NOTE: We defer parsing of the body, so we have the chance to call the tracing
        # loggers before the parsing. This is because, if the body contains any other
        # tags, it will trigger their tag handlers. So the code called AFTER
        # `parse_body()` is already after all the nested tags were processed.
        parse_body=lambda: _parse_tag_body(django_parser, end_tag, is_inline) if end_tag else (NodeList(), None),
    )


# Similar to `parser.parse(parse_until=[end_tag])`, except:
# 1. Does not remove the token it goes over (unlike `parser.parse()`, which mutates the parser state)
# 2. Returns a string, instead of a NodeList
#
# This is used so we can access the contents of the tag body as strings, for example
# to be used for caching slots.
#
# See https://github.com/django/django/blob/1fb3f57e81239a75eb8f873b392e11534c041fdc/django/template/base.py#L471
def _extract_contents_until(parser: Parser, until_blocks: list[str]) -> str:
    contents: list[str] = []
    for token in reversed(parser.tokens):
        # Use the raw values here for TokenType.* for a tiny performance boost.
        token_type = token.token_type.value
        if token_type == 0:  # TokenType.TEXT
            contents.append(token.contents)
        elif token_type == 1:  # TokenType.VAR
            contents.append("{{ " + token.contents + " }}")
        elif token_type == 2:  # TokenType.BLOCK
            try:
                command = token.contents.split()[0]
            except IndexError:
                # NOTE: Django's `Parser.parse()` raises a `TemplateSyntaxError` when there
                # was an empty block tag, e.g. `{% %}`.
                # We skip raising an error here and let `Parser.parse()` raise it.
                contents.append("{% " + token.contents + " %}")
            else:
                if command in until_blocks:
                    return "".join(contents)
                contents.append("{% " + token.contents + " %}")
        elif token_type == 3:  # TokenType.COMMENT
            contents.append("{# " + token.contents + " #}")
        else:
            raise ValueError(f"Unknown token type {token_type}")

    # NOTE: If we got here, then we've reached the end of the tag body without
    # encountering any of the `until_blocks`.
    # Django's `Parser.parse()` raises a `TemplateSyntaxError` in such case.
    #
    # Currently `_extract_contents_until()` runs right before `parser.parse()`,
    # so we skip raising an error here.
    return "".join(contents)


def _extract_flags(
    attrs: Iterable[TagAttr],
    allowed_flags: set[str],
) -> tuple[list[TagAttr], dict[str, bool]]:
    found_flags: set[str] = set()
    remaining_attrs: list[TagAttr] = []
    for attr in attrs:
        if not attr.is_flag:
            remaining_attrs.append(attr)
            continue

        # NOTE: Duplication check is done in Rust's `parse_tag()`
        # NOTE 2: If a flag is used as a spread (e.g. `...flag`), then we treat it as a regular value.
        value = attr.value.token.content
        found_flags.add(value)

    # Construct a dictionary of flags, e.g. `{"required": True, "disabled": False}`
    flags_dict: dict[str, bool] = {flag: flag in found_flags for flag in (allowed_flags or [])}

    return remaining_attrs, flags_dict


def resolve_template_string(
    context: Mapping[str, Any],
    _source: str,
    _token: tuple[int, int],
    filters: Mapping[str, Callable],
    tags: Mapping[str, Callable],
    expr: str,
) -> Any:
    return TemplateExpression(
        expr_str=expr,
        filters=filters,
        tags=tags,
    ).resolve(context)


def resolve_filter(
    _context: Mapping[str, Any],
    _source: str,
    _token: tuple[int, int],
    filters: Mapping[str, Callable],
    _tags: Mapping[str, Callable],
    name: str,
    value: Any,
    arg: Any,
) -> Any:
    if name not in filters:
        raise TemplateSyntaxError(f"Invalid filter: '{name}'")

    filter_func = filters[name]
    if arg is None:
        return filter_func(value)
    else:
        return filter_func(value, arg)


# TODO - Cache?
def resolve_variable(
    context: Mapping[str, Any],
    _source: str,
    _token: tuple[int, int],
    _filters: Mapping[str, Callable],
    _tags: Mapping[str, Callable],
    var: str,
) -> Any:
    try:
        return Variable(var).resolve(context)
    except VariableDoesNotExist:
        return ""


# TODO - Cache?
def resolve_translation(
    context: Mapping[str, Any],
    _source: str,
    _token: tuple[int, int],
    _filters: Mapping[str, Callable],
    _tags: Mapping[str, Callable],
    text: str,
) -> Any:
    # The compiler gives us the variable stripped of `_(")` and `"),
    # so we put it back for Django's Variable class to interpret it as a translation.
    translation_var = "_('" + text + "')"
    return Variable(translation_var).resolve(context)


python_expression_cache: dict[str, Callable[[Mapping[str, Any]], Any]] = {}


def resolve_python_expression(
    context: Mapping[str, Any],
    _source: str,
    _token: tuple[int, int],
    _filters: Mapping[str, Callable],
    _tags: Mapping[str, Callable],
    code: str,
) -> Any:
    if code not in python_expression_cache:
        python_expression_cache[code] = safe_eval(code)

    expr_resolver = python_expression_cache[code]
    return expr_resolver(context)


class CompiledTagFn(Protocol):
    def __call__(self, context: Mapping[str, Any]) -> tuple[list[Any], list[tuple[str, Any]]]: ...


def compile_tag_params_resolver(
    tag_name: str,
    params: list[TagAttr],
    source: str,
    filters: dict[str, Callable],
    tags: dict[str, Callable],
) -> CompiledTagFn:
    compiled_tag = compile_tag(
        tag_or_attrs=params,
        source=source,
        filters=filters,
        tags=tags,
        template_string=resolve_template_string,
        expr=resolve_python_expression,
        variable=resolve_variable,
        translation=resolve_translation,
        filter=resolve_filter,
    )

    def resolver(context: Mapping[str, Any]) -> tuple[list[Any], list[tuple[str, Any]]]:
        args, kwargs = compiled_tag(context)

        # TODO - Move these to extensions?
        if tag_name == "html_attrs":
            args, kwargs = merge_repeated_kwargs(args, kwargs)
        args, kwargs = process_aggregate_kwargs(args, kwargs)

        return args, kwargs

    return resolver


# TODO_REMOVE_IN_V1 - Disallow specifying the same key multiple times once in v1.
def merge_repeated_kwargs(args: list[Any], kwargs: list[tuple[str, Any]]) -> tuple[list[Any], list[tuple[str, Any]]]:
    resolved_kwargs: list[tuple[str, Any]] = []
    # Used for detecting duplicate kwargs
    kwargs_by_key: dict[str, tuple[str, Any]] = {}
    # Keep track of the index of the first occurence of a kwarg
    kwarg_indices_by_key: dict[str, int] = {}
    # Duplicate kwargs whose values are to be merged
    # For 'class' and 'style', we collect values into a list for proper normalization
    # For other attributes, we concatenate as strings
    duplicate_kwargs: dict[str, list[Any]] = defaultdict(list)

    for index, kwarg in enumerate(kwargs):
        key, value = kwarg

        # Case: First time we see a kwarg
        if key not in kwargs_by_key:
            kwargs_by_key[key] = kwarg
            kwarg_indices_by_key[key] = index
            resolved_kwargs.append(kwarg)
        # Case: A kwarg is repeated - we merge the values into a single string, with a space in between.
        else:
            duplicate_kwargs[key].append(value)

    # Once we've gone over all kwargs, check which duplicates we have, and merge them
    for key, values in duplicate_kwargs.items():
        _, orig_kwarg_value = kwargs_by_key[key]
        orig_kwarg_index = kwarg_indices_by_key[key]

        # For 'class' and 'style', collect values into a list so merge_attributes
        # can properly normalize them (handling dicts, lists, etc.)
        if key in ("class", "style"):
            merged_value: list | str = [orig_kwarg_value, *values]
        else:
            # For other attributes, concatenate as strings with spaces
            merged_value = str(orig_kwarg_value) + " " + " ".join(str(v) for v in values)

        resolved_kwargs[orig_kwarg_index] = (key, merged_value)

    return args, resolved_kwargs


# TODO - Move this out into a plugin?
def process_aggregate_kwargs(
    args: list[Any],
    kwargs: list[tuple[str, Any]],
) -> tuple[list[Any], list[tuple[str, Any]]]:
    """
    This function aggregates "prefixed" kwargs into dicts. "Prefixed" kwargs
    start with some prefix delimited with `:` (e.g. `attrs:`).

    Example:
    ```py
    process_aggregate_kwargs([], [("abc:one", 1), ("abc:two", 2), ("def:three", 3), ("four", 4)])
    # ([], [("abc", {"one": 1, "two": 2}), ("def", {"three": 3}), ("four", 4)])
    ```

    ---

    We want to support a use case similar to Vue's fallthrough attributes.
    In other words, where a component author can designate a prop (input)
    which is a dict and which will be rendered as HTML attributes.

    This is useful for allowing component users to tweak styling or add
    event handling to the underlying HTML. E.g.:

    `class="pa-4 d-flex text-black"` or `@click.stop="alert('clicked!')"`

    So if the prop is `attrs`, and the component is called like so:
    ```django
    {% component "my_comp" attrs=attrs %}
    ```

    then, if `attrs` is:
    ```py
    {"class": "text-red pa-4", "@click": "dispatch('my_event', 123)"}
    ```

    and the component template is:
    ```django
    <div {% html_attrs attrs add:class="extra-class" %}></div>
    ```

    Then this renders:
    ```html
    <div class="text-red pa-4 extra-class" @click="dispatch('my_event', 123)" ></div>
    ```

    However, this way it is difficult for the component user to define the `attrs`
    variable, especially if they want to combine static and dynamic values. Because
    they will need to pre-process the `attrs` dict.

    So, instead, we allow to "aggregate" props into a dict. So all props that start
    with `attrs:`, like `attrs:class="text-red"`, will be collected into a dict
    at key `attrs`.

    This provides sufficient flexiblity to make it easy for component users to provide
    "fallthrough attributes", and sufficiently easy for component authors to process
    that input while still being able to provide their own keys.

    """
    _check_kwargs_for_agg_conflict(kwargs)

    processed_kwargs = []
    seen_keys = set()
    nested_kwargs: dict[str, dict[str, Any]] = {}
    for key, value in kwargs:
        # Regular kwargs without `:` prefix
        if not is_aggregate_key(key):
            outer_key = key
            inner_key = None
            seen_keys.add(outer_key)
            processed_kwargs.append((key, value))
            continue

        # NOTE: Trim off the outer_key from keys
        outer_key, inner_key = key.split(":", 1)
        if outer_key not in nested_kwargs:
            nested_kwargs[outer_key] = {}
        nested_kwargs[outer_key][inner_key] = value

    # Assign aggregated values into normal input
    for outer_key, nested_dict in nested_kwargs.items():
        if outer_key in seen_keys:
            raise TemplateSyntaxError(
                f"Received argument '{outer_key}' both as a regular input ({outer_key}=...)"
                f" and as an aggregate dict ('{outer_key}:key=...'). Must be only one of the two",
            )
        processed_kwargs.append((outer_key, nested_dict))

    return args, processed_kwargs


def _check_kwargs_for_agg_conflict(kwargs: list[tuple[str, Any]]) -> None:
    seen_regular_kwargs = set()
    seen_agg_kwargs = set()

    for key, _value in kwargs:
        is_agg_kwarg = is_aggregate_key(key)
        if (
            (is_agg_kwarg and (key in seen_regular_kwargs))
            or (not is_agg_kwarg and (key in seen_agg_kwargs))
        ):  # fmt: skip
            raise TemplateSyntaxError(
                f"Received argument '{key}' both as a regular input ({key}=...)"
                f" and as an aggregate dict ('{key}:key=...'). Must be only one of the two",
            )

        if is_agg_kwarg:
            seen_agg_kwargs.add(key)
        else:
            seen_regular_kwargs.add(key)


def is_aggregate_key(key: str) -> bool:
    key = key.strip()
    # NOTE: If we get a key that starts with `:`, like `:class`, we do not split it.
    # This syntax is used by Vue and AlpineJS.
    return (
        ":" in key
        # `:` or `:class` is NOT ok
        and not key.startswith(":")
        # `attrs:class` is OK, but `attrs:` is NOT ok
        and bool(key.split(":", maxsplit=1)[1])
    )


# Since we support literal lists and dicts inside our template tags,
# we can't simply use Django's `token.split_contents()` to split the content
# of the tag into "bits".
# Unfortunately, we NEED to prepare the "bits" because that's currently the interface
# for the TagFormatters.
# Situation would've been easier if we didn't have to use Django's template parser,
# or if we had made TagFormatters internal (or accept the AST?)
#
# Nevertheless, this function prepares the "bits" from a Tag object, so we can use them
# in component_registry.py, to be able to dynamically switch between the different tag formats.
#
# NOTE: Another reason we want to avoid using Django's `token.split_contents()`
# is because it incorrectly handles when a translation has a filter,
# and there's no space between them, e.g. `_("Hello")|upper`.
def bits_from_tag(tag: TagUnion) -> list[str]:
    bits = [tag.meta.name.content]
    attrs = tag.attrs if isinstance(tag, GenericTag) else ()
    is_self_closing = isinstance(tag, GenericTag) and tag.is_self_closing

    for attr in attrs:
        attr_bit = attr.token.content
        bits.append(attr_bit)
    if is_self_closing:
        bits.append("/")
    return bits
