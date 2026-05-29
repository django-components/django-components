from collections.abc import Callable, Mapping
from typing import Any

from django.template import Context, Node, NodeList
from django.template.base import Origin, Parser, VariableNode

from django_components.util.template_parser import parse_template


class TemplateExpression:
    """
    To make working with Django templates easier, we allow to use (nested) template tags `{% %}`
    inside of strings that are passed to our template tags, e.g.:

    ```django
    {% component "my_comp" value_from_tag="{% gen_dict %}" %}
    ```

    We call this the "template expression".

    A string is marked as a template expression only if it contains any one
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
        origin: "Origin | None" = None,
    ) -> None:
        # NOTE: The logic of what is or is NOT a dynamic expression is defined
        # by the djc_core.template_parser. So we can blindly accept the string that
        # it returns, and not worry about it.
        self.expr = expr_str

        # Copy the minimum data required to parse the expression.
        # We pass through the tags and filters available in the current context.
        # Thus, if user calls `{% load %}` inside the expression, it won't spill outside.
        #
        # We also thread through the host template's `origin`. Django's `Parser.extend_nodelist`
        # stamps `node.origin` onto every parsed node, and Django's debug-mode traceback
        # annotator reads `node.origin` / `node.token` to point at the failing source line.
        # Without a real origin here, errors raised inside multi-node expressions could not be
        # annotated (and previously crashed the annotator itself; see #1597).
        tokens = parse_template(self.expr)
        expr_parser = Parser(tokens=tokens, origin=origin)
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
        # `token` and `origin` are read by Django's debug-mode traceback annotator
        # (`Node.render_annotated`) to point the error at the failing source line.
        # `Parser.extend_nodelist` stamps both onto every parsed node, so they are always
        # present here (though `origin` may be `None` if the expression was parsed without
        # a host template origin).
        self.token = getattr(wrapped_node, "token", None)
        self.origin = getattr(wrapped_node, "origin", None)

    def render(self, context: Context) -> str:
        # Fallback for when the wrapped node has no origin, which happens when the expression
        # was parsed without a host origin. A `StringifiedNode` is created for multi-node
        # expressions, e.g. `{% component "c" x="{{ a }}{{ b }}" %}` (two `VariableNode`s) or
        # `{% component "c" x="prefix {{ a }}" %}` (a `TextNode` plus a `VariableNode`). Such an
        # expression carries no origin if it was built directly in code rather than through
        # `resolve_template_string()`, for example a test rendering the node via
        # `nodelist.render(context)` instead of `Template.render()`. As long as the surrounding
        # `Context` was bound through `Template.render()`, `render_context.template` is set, so we
        # borrow that template's origin to give the annotator a real source to compare against.
        #
        # We check `is None` rather than `hasattr`, since the attribute is always set; a
        # `hasattr` guard would shadow this branch and make it dead code.
        if self.origin is None and context.render_context.template is not None:
            self.origin = context.render_context.template.origin
        result = self.wrapped_node.render(context)
        return str(result)
