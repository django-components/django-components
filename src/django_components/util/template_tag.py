"""
This file is for logic that focuses on transforming the AST of template tags
(as parsed from tag_parser) into a form that can be used by the Nodes.
"""

import inspect
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    Tuple,
)

from django.template import NodeList, Variable, VariableDoesNotExist
from django.template.base import Parser, Token
from django.template.exceptions import TemplateSyntaxError
from djc_core.safe_eval import safe_eval
from djc_core.template_parser import GenericTag, ParserConfig, TagAttr, compile_tag, parse_tag
from djc_core.template_parser.parse import TagUnion

from django_components.expression import DynamicFilterExpression


# Data obj to give meaning to the parsed tag fields
class ParsedTag(NamedTuple):
    start_tag_source: str
    flags: Dict[str, bool]
    params: List[TagAttr]
    parse_body: Callable[[], Tuple[NodeList, Optional[str]]]


def parse_template_tag(
    tag: str,
    end_tag: Optional[str],
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

    def _parse_tag_body(parser: Parser, end_tag: str, inline: bool) -> Tuple[NodeList, Optional[str]]:
        if inline:
            body = NodeList()
            contents: Optional[str] = None
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
def _extract_contents_until(parser: Parser, until_blocks: List[str]) -> str:
    contents: List[str] = []
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
    allowed_flags: Set[str],
) -> Tuple[List[TagAttr], Dict[str, bool]]:
    found_flags: Set[str] = set()
    remaining_attrs: List[TagAttr] = []
    for attr in attrs:
        if not attr.is_flag:
            remaining_attrs.append(attr)
            continue

        # NOTE: Duplication check is done in Rust's `parse_tag()`
        # NOTE 2: If a flag is used as a spread (e.g. `...flag`), then we treat it as a regular value.
        value = attr.value.token.content
        found_flags.add(value)

    # Construct a dictionary of flags, e.g. `{"required": True, "disabled": False}`
    flags_dict: Dict[str, bool] = {flag: flag in found_flags for flag in (allowed_flags or [])}

    return remaining_attrs, flags_dict


def resolve_template_string(
    context: Mapping[str, Any],
    _source: str,
    _token: Tuple[int, int],
    filters: Mapping[str, Callable],
    tags: Mapping[str, Callable],
    expr: str,
) -> Any:
    return DynamicFilterExpression(
        expr_str=expr,
        filters=filters,
        tags=tags,
    ).resolve(context)


def resolve_filter(
    _context: Mapping[str, Any],
    _source: str,
    _token: Tuple[int, int],
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
    _token: Tuple[int, int],
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
    _token: Tuple[int, int],
    _filters: Mapping[str, Callable],
    _tags: Mapping[str, Callable],
    text: str,
) -> Any:
    # The compiler gives us the variable stripped of `_(")` and `"),
    # so we put it back for Django's Variable class to interpret it as a translation.
    translation_var = "_('" + text + "')"
    return Variable(translation_var).resolve(context)


python_expression_cache: Dict[str, Callable[[Mapping[str, Any]], Any]] = {}


def resolve_python_expression(
    context: Mapping[str, Any],
    _source: str,
    _token: Tuple[int, int],
    _filters: Mapping[str, Callable],
    _tags: Mapping[str, Callable],
    code: str,
) -> Any:
    if code not in python_expression_cache:
        python_expression_cache[code] = safe_eval(code)

    expr_resolver = python_expression_cache[code]
    return expr_resolver(context)


class CompiledTagFn(Protocol):
    def __call__(self, context: Mapping[str, Any]) -> Tuple[List[Any], List[Tuple[str, Any]]]: ...


def compile_tag_params_resolver(
    tag_name: str,
    params: List[TagAttr],
    source: str,
    filters: Dict[str, Callable],
    tags: Dict[str, Callable],
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

    def resolver(context: Mapping[str, Any]) -> Tuple[List[Any], List[Tuple[str, Any]]]:
        args, kwargs = compiled_tag(context)

        # TODO - Move these to extensions?
        if tag_name == "html_attrs":
            args, kwargs = merge_repeated_kwargs(args, kwargs)
        args, kwargs = process_aggregate_kwargs(args, kwargs)

        return args, kwargs

    return resolver


# TODO_REMOVE_IN_V1 - Disallow specifying the same key multiple times once in v1.
def merge_repeated_kwargs(args: List[Any], kwargs: List[Tuple[str, Any]]) -> Tuple[List[Any], List[Tuple[str, Any]]]:
    resolved_kwargs: List[Tuple[str, Any]] = []
    # Used for detecting duplicate kwargs
    kwargs_by_key: Dict[str, Tuple[str, Any]] = {}
    # Keep track of the index of the first occurence of a kwarg
    kwarg_indices_by_key: Dict[str, int] = {}
    # Duplicate kwargs whose values are to be merged into a single string
    duplicate_kwargs: Dict[str, List[str]] = defaultdict(list)

    for index, kwarg in enumerate(kwargs):
        key, value = kwarg

        # Case: First time we see a kwarg
        if key not in kwargs_by_key:
            kwargs_by_key[key] = kwarg
            kwarg_indices_by_key[key] = index
            resolved_kwargs.append(kwarg)
        # Case: A kwarg is repeated - we merge the values into a single string, with a space in between.
        else:
            duplicate_kwargs[key].append(str(value))

    # Once we've gone over all kwargs, check which duplicates we have, and append the values
    # of duplicates to the first instances of those kwargs.
    for key, values in duplicate_kwargs.items():
        _, orig_kwarg_value = kwargs_by_key[key]
        orig_kwarg_index = kwarg_indices_by_key[key]
        merged_value = str(orig_kwarg_value) + " " + " ".join(values)
        resolved_kwargs[orig_kwarg_index] = (key, merged_value)

    return args, resolved_kwargs


# TODO - Move this out into a plugin?
def process_aggregate_kwargs(
    args: List[Any],
    kwargs: List[Tuple[str, Any]],
) -> Tuple[List[Any], List[Tuple[str, Any]]]:
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
    nested_kwargs: Dict[str, Dict[str, Any]] = {}
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


def _check_kwargs_for_agg_conflict(kwargs: List[Tuple[str, Any]]) -> None:
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


# For details see https://github.com/django-components/django-components/pull/902#discussion_r1913611633
# and following comments
def validate_params(
    func: Callable[..., Any],
    validation_signature: inspect.Signature,
    tag: str,
    args: List[Any],
    kwargs: List[Tuple[str, Any]],
    extra_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Validates a template tag's inputs against this tag's function signature.

    Raises `TypeError` if the parameters don't match tfuncsignature.

    We have to have a custom validation, because if we simply spread all args and kwargs,
    into `BaseNode.render()`, then we won't be able to detect duplicate kwargs or other
    errors.
    """
    supports_code_objects = func is not None and hasattr(func, "__code__") and hasattr(func.__code__, "co_varnames")
    try:
        if supports_code_objects:
            _validate_params_with_code(func, args, kwargs, extra_kwargs)
        else:
            _validate_params_with_signature(validation_signature, args, kwargs, extra_kwargs)
    except TypeError as e:
        err_msg = str(e)
        raise TypeError(f"Invalid parameters for tag '{tag}': {err_msg}") from None


def _validate_params_with_signature(
    signature: inspect.Signature,
    args: List[Any],
    kwargs: List[Tuple[str, Any]],
    extra_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Apply template tag's inputs to another function, keeping the order of the params as they
    appeared in the template.

    If a template tag was called like this:

    ```django
    {% component key1=value1 arg1 arg2 key2=value2 key3=value3 %}
    ```

    Then it will be as if the given function was called like this:

    ```python
    fn(key1=value1, arg1, arg2, key2=value2, key3=value3)
    ```

    This function validates that the template tag's parameters match the function's signature
    and follow Python's function calling conventions. It will raise appropriate TypeError exceptions
    for invalid parameter combinations, such as:
    - Too few/many arguments (for non-variadic functions)
    - Duplicate keyword arguments
    - Mixed positional/keyword argument errors

    Returns the result of calling fn with the validated parameters
    """
    # Track state as we process parameters
    used_param_names = set()  # To detect duplicate kwargs

    # Get list of valid parameter names and analyze signature
    params_by_name = signature.parameters
    valid_params = list(params_by_name.keys())

    # Check if function accepts variable arguments (*args, **kwargs)
    has_var_positional = any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in params_by_name.values())
    has_var_keyword = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params_by_name.values())

    # Find the last positional parameter index (excluding *args)
    max_positional_index = 0
    for i, signature_param in enumerate(params_by_name.values()):
        if signature_param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            max_positional_index = i + 1
        elif signature_param.kind == inspect.Parameter.VAR_POSITIONAL:
            # Don't count *args in max_positional_index
            break
        # Parameter.KEYWORD_ONLY
        # Parameter.VAR_KEYWORD
        else:
            break

    # Process parameters in their original order
    # NOTE: Any possibility that an arg was given AFTER kwarg (which is error in Python)
    #       was already checked by djc_core.template_parser. So we KNOW these args come before kwargs.
    # This is a positional argument
    for arg_index, _arg in enumerate(args):
        # Only check position limit for non-variadic functions
        if not has_var_positional and arg_index >= max_positional_index:
            if max_positional_index == 0:
                raise TypeError(f"takes 0 positional arguments but {arg_index + 1} was given")
            raise TypeError(f"takes {max_positional_index} positional argument(s) but more were given")

        # For non-variadic arguments, get the parameter name this maps to
        if arg_index < max_positional_index:
            param_name = valid_params[arg_index]
            # Check if this parameter was already provided as a kwarg
            if param_name in used_param_names:
                raise TypeError(f"got multiple values for argument '{param_name}'")
            used_param_names.add(param_name)

    for kwarg_key, _kwarg_value in kwargs:
        # Check for duplicate kwargs
        if kwarg_key in used_param_names:
            raise TypeError(f"got multiple values for argument '{kwarg_key}'")

        # Validate kwarg names if the function doesn't accept **kwargs
        if not has_var_keyword and kwarg_key not in valid_params:
            raise TypeError(f"got an unexpected keyword argument '{kwarg_key}'")

        used_param_names.add(kwarg_key)

    # Add any extra kwargs - These are allowed only if the function accepts **kwargs
    if extra_kwargs and not has_var_keyword:
        first_key = next(iter(extra_kwargs))
        raise TypeError(f"got an unexpected keyword argument '{first_key}'")

    # Check for missing required arguments and apply defaults
    for param_name, signature_param in params_by_name.items():
        if param_name in used_param_names:
            continue

        if (
            signature_param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.KEYWORD_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            and signature_param.default == inspect.Parameter.empty
        ):
            raise TypeError(f"missing a required argument: '{param_name}'")


def _validate_params_with_code(
    fn: Callable[..., Any],
    args: List[Any],
    kwargs: List[Tuple[str, Any]],
    extra_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Validate and process function parameters using `__code__` attributes for better performance.
    This is the preferred implementation when the necessary attributes are available.

    This implementation is about 3x faster than signature-based validation.
    For context, see https://github.com/django-components/django-components/issues/935
    """
    code = fn.__code__
    defaults = fn.__defaults__ or ()
    kwdefaults = getattr(fn, "__kwdefaults__", None) or {}

    # Get parameter information from code object
    param_names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
    positional_count = code.co_argcount
    kwonly_count = code.co_kwonlyargcount
    has_var_positional = bool(code.co_flags & 0x04)  # CO_VARARGS
    has_var_keyword = bool(code.co_flags & 0x08)  # CO_VARKEYWORDS

    # Skip `self` and `context` parameters
    skip_params = 2
    param_names = param_names[skip_params:]
    positional_count = max(0, positional_count - skip_params)

    # Calculate required counts
    num_defaults = len(defaults)
    required_positional = positional_count - num_defaults

    # Track state
    used_param_names = set()

    # Process parameters in order
    # NOTE: Any possibility that an arg was given AFTER kwarg (which is error in Python)
    #       was already checked by djc_core.template_parser. So we KNOW these args come before kwargs.
    for arg_index, _arg in enumerate(args):
        # Check position limit for non-variadic functions
        if not has_var_positional and arg_index >= positional_count:
            if positional_count == 0:
                raise TypeError("takes 0 positional arguments but 1 was given")
            raise TypeError(f"takes {positional_count} positional argument(s) but more were given")

        # For non-variadic arguments, get parameter name
        if arg_index < positional_count:
            param_name = param_names[arg_index]
            if param_name in used_param_names:
                raise TypeError(f"got multiple values for argument '{param_name}'")
            used_param_names.add(param_name)

    for kwarg_key, _kwarg_value in kwargs:
        # Check for duplicate kwargs
        if kwarg_key in used_param_names:
            raise TypeError(f"got multiple values for argument '{kwarg_key}'")

        # Validate kwarg names
        is_valid_kwarg = kwarg_key in param_names[: positional_count + kwonly_count] or (  # Regular param
            has_var_keyword and kwarg_key not in param_names
        )  # **kwargs param
        if not is_valid_kwarg:
            raise TypeError(f"got an unexpected keyword argument '{kwarg_key}'")

        used_param_names.add(kwarg_key)

    # Add any extra kwargs
    if extra_kwargs and not has_var_keyword:
        first_key = next(iter(extra_kwargs))
        raise TypeError(f"got an unexpected keyword argument '{first_key}'")

    # Check for missing required arguments and apply defaults
    for i, param_name in enumerate(param_names):
        if param_name in used_param_names:
            continue

        if i < positional_count:  # Positional parameter
            if i < required_positional:
                raise TypeError(f"missing a required argument: '{param_name}'")
            if len(args) <= i:
                default_index = i - required_positional
                if default_index > len(defaults):
                    raise TypeError(f"missing a required argument: '{param_name}'")
        elif i < positional_count + kwonly_count:  # Keyword-only parameter
            if param_name not in kwdefaults:
                raise TypeError(f"missing a required argument: '{param_name}'")


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
def bits_from_tag(tag: TagUnion) -> List[str]:
    bits = [tag.meta.name.content]
    attrs = tag.attrs if isinstance(tag, GenericTag) else ()
    is_self_closing = isinstance(tag, GenericTag) and tag.is_self_closing

    for attr in attrs:
        attr_bit = attr.token.content
        bits.append(attr_bit)
    if is_self_closing:
        bits.append("/")
    return bits
