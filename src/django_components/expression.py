import re
from typing import TYPE_CHECKING, Any, Dict, List

from django.template import Context, Node, NodeList, TemplateSyntaxError
from django.template.base import Parser, VariableNode

from django_components.util.template_parser import parse_template

if TYPE_CHECKING:
    from django_components.util.template_tag import TagParam


class DynamicFilterExpression:
    """
    To make working with Django templates easier, we allow to use (nested) template tags `{% %}`
    inside of strings that are passed to our template tags, e.g.:

    ```django
    {% component "my_comp" value_from_tag="{% gen_dict %}" %}
    ```

    We call this the "dynamic" or "nested" expression.

    A string is marked as a dynamic expression only if it contains any one
    of `{{ }}`, `{% %}`, or `{# #}`.

    If the expression consists of a single tag, with no extra text, we return the tag's
    value directly. E.g.:

    ```django
    {% component "my_comp" value_from_tag="{% gen_dict %}" %}
    ```

    will pass a dictionary to the component input `value_from_tag`.

    But if the text already contains spaces or more tags, e.g.

    `{% component "my_comp" value_from_tag=" {% gen_dict %} " %}`

    Then we treat it as a regular template and pass it as string.
    """

    def __init__(self, parser: Parser, expr_str: str) -> None:
        if not is_dynamic_expression(expr_str):
            raise TemplateSyntaxError(f"Not a valid dynamic expression: '{expr_str}'")

        # Drop the leading and trailing quote
        self.expr = expr_str[1:-1]

        # Copy the Parser, and pass through the tags and filters available
        # in the current context. Thus, if user calls `{% load %}` inside
        # the expression, it won't spill outside.
        tokens = parse_template(self.expr)
        expr_parser = Parser(tokens=tokens)
        expr_parser.tags = {**parser.tags}
        expr_parser.filters = {**parser.filters}

        self.nodelist = expr_parser.parse()

    def resolve(self, context: Context) -> Any:
        # If the expression consists of a single node, we return the node's value
        # directly, skipping stringification that would occur by rendering the node
        # via nodelist.
        #
        # This make is possible to pass values from the nested tag expressions
        # and use them as component inputs.
        # E.g. below, the value of `value_from_tag` kwarg would be a dictionary,
        # not a string.
        #
        # `{% component "my_comp" value_from_tag="{% gen_dict %}" %}`
        #
        # But if it already container spaces, e.g.
        #
        # `{% component "my_comp" value_from_tag=" {% gen_dict %} " %}`
        #
        # Then we'd treat it as a regular template and pass it as string.
        if len(self.nodelist) == 1:
            node = self.nodelist[0]

            # Handle `{{ }}` tags, where we need to access the expression directly
            # to avoid it being stringified
            if isinstance(node, VariableNode):
                return node.filter_expression.resolve(context)

            # For any other tags `{% %}`, we're at a mercy of the authors, and
            # we don't know if the result comes out stringified or not.
            return node.render(context)

        # Lastly, if there's multiple nodes, we render it to a string
        #
        # NOTE: When rendering a NodeList, it expects that each node is a string.
        # However, we want to support tags that return non-string results, so we can pass
        # them as inputs to components. So we wrap the nodes in `StringifiedNode`
        nodelist = NodeList(StringifiedNode(node) for node in self.nodelist)
        return nodelist.render(context)


class StringifiedNode(Node):
    def __init__(self, wrapped_node: Node) -> None:
        super().__init__()
        self.wrapped_node = wrapped_node

    def render(self, context: Context) -> str:
        result = self.wrapped_node.render(context)
        return str(result)


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


# A string that must start and end with quotes, and somewhere inside includes
# at least one tag. Tag may be variable (`{{ }}`), block (`{% %}`), or comment (`{# #}`).
DYNAMIC_EXPR_RE = re.compile(
    r"^{start_quote}.*?(?:{var_tag}|{block_tag}|{comment_tag}).*?{end_quote}$".format(
        var_tag=r"(?:\{\{.*?\}\})",
        block_tag=r"(?:\{%.*?%\})",
        comment_tag=r"(?:\{#.*?#\})",
        start_quote=r"(?P<quote>['\"])",  # NOTE: Capture group so we check for the same quote at the end
        end_quote=r"(?P=quote)",
    ),
)


def is_dynamic_expression(value: Any) -> bool:
    # NOTE: Currently dynamic expression need at least 6 characters
    # for the opening and closing tags, and quotes, e.g. `"`, `{%`, `%}` in `" some text {% ... %}"`
    MIN_EXPR_LEN = 6  # noqa: N806

    if not isinstance(value, str) or not value or len(value) < MIN_EXPR_LEN:
        return False

    # Is not wrapped in quotes, or does not contain any tags
    return bool(DYNAMIC_EXPR_RE.match(value))


# TODO - Move this out into a plugin?
def process_aggregate_kwargs(params: List["TagParam"]) -> List["TagParam"]:
    """
    This function aggregates "prefixed" kwargs into dicts. "Prefixed" kwargs
    start with some prefix delimited with `:` (e.g. `attrs:`).

    Example:
    ```py
    process_component_kwargs({"abc:one": 1, "abc:two": 2, "def:three": 3, "four": 4})
    # {"abc": {"one": 1, "two": 2}, "def": {"three": 3}, "four": 4}
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
    from django_components.util.template_tag import TagParam  # noqa: PLC0415

    _check_kwargs_for_agg_conflict(params)

    processed_params = []
    seen_keys = set()
    nested_kwargs: Dict[str, Dict[str, Any]] = {}
    for param in params:
        # Positional args
        if param.key is None:
            processed_params.append(param)
            continue

        # Regular kwargs without `:` prefix
        if not is_aggregate_key(param.key):
            outer_key = param.key
            inner_key = None
            seen_keys.add(outer_key)
            processed_params.append(param)
            continue

        # NOTE: Trim off the outer_key from keys
        outer_key, inner_key = param.key.split(":", 1)
        if outer_key not in nested_kwargs:
            nested_kwargs[outer_key] = {}
        nested_kwargs[outer_key][inner_key] = param.value

    # Assign aggregated values into normal input
    for key, val in nested_kwargs.items():
        if key in seen_keys:
            raise TemplateSyntaxError(
                f"Received argument '{key}' both as a regular input ({key}=...)"
                f" and as an aggregate dict ('{key}:key=...'). Must be only one of the two",
            )
        processed_params.append(TagParam(key=key, value=val))

    return processed_params


def _check_kwargs_for_agg_conflict(params: List["TagParam"]) -> None:
    seen_regular_kwargs = set()
    seen_agg_kwargs = set()

    for param in params:
        # Ignore positional args
        if param.key is None:
            continue

        is_agg_kwarg = is_aggregate_key(param.key)
        if (
            (is_agg_kwarg and (param.key in seen_regular_kwargs))
            or (not is_agg_kwarg and (param.key in seen_agg_kwargs))
        ):  # fmt: skip
            raise TemplateSyntaxError(
                f"Received argument '{param.key}' both as a regular input ({param.key}=...)"
                f" and as an aggregate dict ('{param.key}:key=...'). Must be only one of the two",
            )

        if is_agg_kwarg:
            seen_agg_kwargs.add(param.key)
        else:
            seen_regular_kwargs.add(param.key)
