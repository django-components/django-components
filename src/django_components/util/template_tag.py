"""
This file is for logic that focuses on transforming the AST of template tags
(as parsed from tag_parser) into a form that can be used by the Nodes.
"""

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping
from functools import partial
from inspect import unwrap
from types import FunctionType, WrapperDescriptorType
from typing import (
    Any,
    NamedTuple,
    Protocol,
)

from django.template import NodeList, Variable, VariableDoesNotExist
from django.template.base import Parser, Token
from django.template.exceptions import TemplateSyntaxError
from django.utils.functional import Promise, lazystr
from django.utils.html import format_html, format_html_join
from django.utils.text import format_lazy
from djc_core.safe_eval import SecurityError, safe_eval
from djc_core.safe_eval.sandbox import is_safe_callable
from djc_core.template_parser import GenericTag, ParserConfig, TagAttr, compile_tag, parse_tag
from djc_core.template_parser.parse import TagUnion

from django_components.expression import TemplateExpression
from django_components.util.misc import TrustedAttrName, is_script_capable_attr_name


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
    # During rendering, `context.template` is the host template (set via `Context.bind_template`).
    # Pass its origin so nested expression nodes can be annotated against the correct source file
    # when an error is raised. Guarded with `getattr` so a plain-dict context (no `.template`)
    # degrades gracefully to `None`.
    origin = getattr(getattr(context, "template", None), "origin", None)
    return TemplateExpression(
        expr_str=expr,
        filters=filters,
        tags=tags,
        origin=origin,
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


# Django functions that follow the attribute and item paths written in the text they receive, such
# as `{0.__class__}`, with the real `getattr`. `safe_eval` never sees those reads. They are compared
# by identity and by code rather than looked up in a set, because a callable that a template can
# reach may not be hashable.
DJANGO_FORMAT_FUNCTIONS = (format_html, format_html_join, format_lazy)

# Each Django formatter with the name to show in messages and the code that does the formatting.
# A copy of a function made from that code does the same thing, so it is refused too. `unwrap()`
# is needed for `format_lazy`, which is a `lazy()` wrapper whose own code every `lazy()` result
# shares, and whose `__name__` is that of the private function it wraps.
DJANGO_FORMATTERS = tuple(
    (name, formatter, unwrap(formatter).__code__)
    for name, formatter in zip(
        ("format_html", "format_html_join", "format_lazy"), DJANGO_FORMAT_FUNCTIONS, strict=True
    )
)

# Each method that a lazy string takes from its result class, such as `upper`, is a copy of one
# function that Django's `lazy()` builds in a loop, so all the copies share one code object. That
# function takes a keyword argument that picks the real method to run, so any copy can run
# `format`. Comparing the code also catches a copy taken from the class, which is not bound to a
# lazy string.
LAZY_STRING_METHOD_CODE = type(lazystr("")).upper.__code__

# How many functions behind the called one the callable check follows before it refuses the call.
# Real wrappers such as `lazy()`, `keep_lazy()`, `lru_cache()` or a `functools.partial` add one or
# two steps. A callable object counts its class `__call__` as a step too.
MAX_WRAPPED_FUNCTIONS = 32

LAZY_OBJECT_REASON = (
    "because each of its methods can run any method of the real value, such as format(). "
    "A Django lazy string is the result of _(), gettext_lazy() and similar. "
    'Turn it into plain text with an f-string first, such as f"{text}".upper().'
)


def check_expression_attribute(obj: Any, attr: str) -> bool:
    """
    Refuse reading any attribute of a Django lazy object, or of its class, in a Python expression.

    A lazy object is a `Promise`, such as a lazy string from `gettext_lazy()` or `_("...")` in a
    template. `safe_eval` refuses `format` and `format_map` on `str` and `UserString`, but a lazy
    string is neither of those: it forwards each method call to the real string.

    The whole object is refused, not only those two names. A forwarding method accepts a keyword
    argument that picks the method to run, so any of them can run `format`, and `safe_eval` does
    not show keyword arguments to its hooks.

    Raises `SecurityError` with a message that says what to do instead. Returns `True` otherwise,
    which tells `safe_eval` to go on with its own checks.
    """
    if _is_lazy_object_or_class(obj):
        raise SecurityError(
            f"Expressions can't read '{attr}' on a Django lazy object, such as a lazy string, {LAZY_OBJECT_REASON}"
        )
    return True


def check_expression_callable(func: Callable) -> bool:
    """
    Refuse calling a method of a Django lazy object or a Django formatting function in a Python expression.

    This covers what `check_expression_attribute` cannot see: a function that the app placed in the
    context. The check follows what the function passes the call on to: the function inside a
    `functools.partial`, the function of a bound method (`__func__`), the function that
    `functools.wraps` names (`__wrapped__`), the object that a `__call__` method belongs to, and the
    `__call__` of an object's class. Django's `lazy()` and `keep_lazy()` and Python's `lru_cache()`
    hide the function they call this way. At each step it refuses:

    - a lazy class, a method bound to a lazy object, or a copy of the lazy string method taken from
      its class;
    - a function in `DJANGO_FORMAT_FUNCTIONS`, or a copy of one, which follow paths written in the
      text they format;
    - anything that the `safe_eval` check itself refuses, such as `str.format`.

    Raises `SecurityError` with a message that says what to do instead, and also when `func` wraps
    more than `MAX_WRAPPED_FUNCTIONS` functions. Returns `True` otherwise, which tells `safe_eval`
    to go on with its own checks of `func`.
    """
    # Keyed by `id()`, and holding each object so that its id cannot be reused by another object
    # that a `__wrapped__` lookup creates while this check runs.
    seen: dict[int, Any] = {}
    pending = [func]
    while pending:
        step = pending.pop()
        # A function that wraps itself, directly or further down, adds nothing new to check.
        if id(step) in seen:
            continue
        seen[id(step)] = step
        # Refuse rather than stop looking, so a long chain cannot hide a refused function. `seen`
        # holds `func` itself as well as the functions it wraps.
        if len(seen) > MAX_WRAPPED_FUNCTIONS + 1:
            raise SecurityError(
                f"Expressions can't call this function, because it wraps more than {MAX_WRAPPED_FUNCTIONS} "
                "other functions, too many to check. Call it in get_template_data() instead."
            )

        _check_one_callable(step, is_wrapped=step is not func)

        # Look at every way `step` can pass the call on, because an object may have more than one.
        if isinstance(step, partial):
            pending.append(step.func)
        for name in ("__func__", "__wrapped__"):
            inner = getattr(step, name, None)
            if inner is not None:
                pending.append(inner)
        # `function.__call__` belongs to `function` and calls it, but has neither of the names above.
        if getattr(step, "__name__", None) == "__call__":
            owner = getattr(step, "__self__", None)
            if owner is not None:
                pending.append(owner)
        # Calling an instance runs the `__call__` that Python finds on its class and binds to the
        # instance, which may be a formatter itself, such as `__call__ = staticmethod(format_html)`.
        # A built-in type's own `__call__` is a C-level wrapper (`WrapperDescriptorType`) that only
        # calls the object, so it adds nothing to check.
        class_call = _find_on_type(step, "__call__")
        if class_call is not None and not isinstance(class_call, WrapperDescriptorType):
            pending.append(class_call)
            # Binding can give another object, as with `functools.partialmethod` or a property. A
            # plain function only becomes a bound method of itself, so it is not bound here.
            bind = _find_on_type(class_call, "__get__")
            if bind is not None and not isinstance(class_call, FunctionType):
                pending.append(bind(class_call, step, type(step)))
    return True


def _check_one_callable(step: Any, *, is_wrapped: bool) -> None:
    # `step` is the function the expression calls, or, when `is_wrapped`, one that it wraps.
    # Calling a lazy class builds a lazy object from the arguments, such as the text and values of
    # `format_lazy()`, and the object formats that text when it is shown.
    is_lazy_class = isinstance(step, type) and issubclass(step, Promise)
    if (
        is_lazy_class
        or _is_lazy_object_or_class(getattr(step, "__self__", None))
        or getattr(step, "__code__", None) is LAZY_STRING_METHOD_CODE
    ):
        raise SecurityError(
            "Expressions can't call a Django lazy object's class or methods, such as those of a lazy string, "
            f"{LAZY_OBJECT_REASON}"
        )

    code = getattr(step, "__code__", None)
    for name, formatter, formatter_code in DJANGO_FORMATTERS:
        if step is formatter or code is formatter_code:
            called = f"{name}()"
            refused = f"this function, because it calls {called}, which" if is_wrapped else f"{called}, because it"
            raise SecurityError(
                f"Expressions can't call {refused} follows attribute paths written in the text. "
                f"Call {called} in get_template_data() and pass the result to the template."
            )

    # `safe_eval` checks the called function itself after this hook, with its own message, so
    # only the functions that it wraps are checked here.
    if is_wrapped:
        # djc-core 1.3.1 looks the function up in its own tables, which fails with `TypeError` for
        # an object that can't be hashed. That version can't check such an object, so refuse it
        # plainly. Later versions check it themselves: it can't be a listed function, and what it
        # passes the call on to is still checked, so they never raise here.
        try:
            is_safe, replacement = is_safe_callable(step)
        except TypeError:
            raise SecurityError(
                "Expressions can't call this function, because it wraps an object that can't be checked. "
                "Call it in get_template_data() instead."
            ) from None
        if not is_safe:
            message = f"Expressions can't call this function, because it calls {_describe_callable(step)}"
            raise SecurityError(f"{message}. {replacement}" if replacement else f"{message}.")


# The descriptors that `type` itself uses for `__mro__` and `__dict__`, so that a metaclass can't
# change what `_find_on_type` reads.
_TYPE_MRO = type.__dict__["__mro__"]
_TYPE_DICT = type.__dict__["__dict__"]


def _find_on_type(obj: Any, name: str) -> Any:
    # Look `name` up the way Python does when it runs a special method such as `__call__` or
    # `__get__` on `obj`: in the `__dict__` of each class in the method resolution order of
    # `type(obj)`. Reading `type(obj).__call__` instead would go through the metaclass and the
    # descriptor, which can return a different object.
    for klass in _TYPE_MRO.__get__(type(obj)):
        namespace = _TYPE_DICT.__get__(klass)
        if name in namespace:
            return namespace[name]
    return None


def _is_lazy_object_or_class(obj: Any) -> bool:
    # `isinstance` looks at `__class__`, so a `SimpleLazyObject` around a lazy object matches too.
    # The class counts as well, because its methods take the lazy object as their first argument.
    return issubclass(obj, Promise) if isinstance(obj, type) else isinstance(obj, Promise)


def _describe_callable(obj: Any) -> str:
    # A short name for messages, without `repr()`, which can print a long text.
    name = getattr(obj, "__qualname__", None)
    if not isinstance(name, str):
        name = type(obj).__qualname__
    return f"'{name}'"


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
        python_expression_cache[code] = safe_eval(
            code,
            validate_attribute=check_expression_attribute,
            validate_callable=check_expression_callable,
        )

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

    # The names the tag itself spells, such as `onclick="..."` or `attrs:onclick="..."`, were
    # written by the template author. Only the parsed tag can tell them from `...spread` keys,
    # which can come from data. Almost no tag has one, so most renders skip this step.
    written_keys = Counter(
        attr.key.content for attr in params if attr.key is not None and _names_script_capable_attr(attr.key.content)
    )

    has_spread = any(attr.value.spread for attr in params)

    def resolver(context: Mapping[str, Any]) -> tuple[list[Any], list[tuple[str, Any]]]:
        args, kwargs = compiled_tag(context)

        if written_keys:
            kwargs = _mark_written_keys(kwargs, written_keys)
        if has_spread:
            kwargs = _unmark_keys_shared_with_data(kwargs)

        # TODO - Move these to extensions?
        if tag_name == "html_attrs":
            args, kwargs = merge_repeated_kwargs(args, kwargs)
        args, kwargs = process_aggregate_kwargs(args, kwargs)

        return args, kwargs

    return resolver


def _names_script_capable_attr(key: str) -> bool:
    # A key may hold the name directly, or after its prefix, as in `attrs:onclick`.
    return is_script_capable_attr_name(key) or (
        is_aggregate_key(key) and is_script_capable_attr_name(key.split(":", 1)[1])
    )


def _mark_written_keys(kwargs: list[tuple[str, Any]], written_keys: Counter[str]) -> list[tuple[str, Any]]:
    """
    Mark the names written in the tag as trusted, so `format_attributes()` and friends accept them.

    A name written in the tag is always emitted, so one more of it means that a `...spread`
    mapping supplied the same name. The values would then be merged into one attribute, so
    none of them is marked and the name is refused, as for any other name from data.
    """
    # A key that a spread brings with its mark is not from data, so it does not count here.
    found = Counter(key for key, _ in kwargs if key in written_keys and not isinstance(key, TrustedAttrName))
    return [
        (TrustedAttrName(key) if key in written_keys and found[key] == written_keys[key] else key, value)
        for key, value in kwargs
    ]


def _unmark_keys_shared_with_data(kwargs: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    """
    Remove the mark from a key that is repeated by a key without one.

    Repeated keys end up as one entry, and which key object survives depends on the order.
    A value from a `...spread` could otherwise reach the page under a name that only another
    source was trusted to set, so the name is refused like any other name from data.
    """
    plain_keys = {key for key, _ in kwargs if not isinstance(key, TrustedAttrName)}
    return [
        (str.__str__(key) if isinstance(key, TrustedAttrName) and key in plain_keys else key, value)
        for key, value in kwargs
    ]


# TODO_REMOVE_IN_V2 - Disallow specifying the same key multiple times once in 2.0.
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

    Examples:
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
        # `split()` returns a plain string, so a name written in the tag has to be marked again.
        if isinstance(key, TrustedAttrName):
            inner_key = TrustedAttrName(inner_key)
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
