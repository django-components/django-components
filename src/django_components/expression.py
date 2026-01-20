from typing import Any, Callable, Mapping

from django.template import Context, Node, NodeList
from django.template.base import Parser, VariableNode

from django_components.util.template_parser import parse_template


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

    def __init__(
        self,
        expr_str: str,
        *,
        filters: Mapping[str, Callable[[Any, Any], Any]],
        tags: Mapping[str, Callable[[Any, Any], Any]],
    ) -> None:
        # NOTE: The logic of what is or is NOT a dynamic expression is defined
        # by the djc_core.template_parser. So we can blindly accept the string that
        # it returns, and not worry about it.
        self.expr = expr_str

        # Copy the minimum data required to parse the expression.
        # We pass through the tags and filters available in the current context.
        # Thus, if user calls `{% load %}` inside the expression, it won't spill outside.
        tokens = parse_template(self.expr)
        expr_parser = Parser(tokens=tokens)
        expr_parser.filters = {**filters}
        expr_parser.tags = {**tags}

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
