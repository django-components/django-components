import functools
import inspect
import keyword
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, cast

from django.template import Context, Library
from django.template.base import Node, NodeList, Parser, Token

from django_components.util.logger import trace_node_msg
from django_components.util.misc import gen_id
from django_components.util.template_tag import (
    TagAttr,
    parse_template_tag,
    resolve_params,
    validate_params,
)


# Normally, when `Node.render()` is called, it receives only a single argument `context`.
#
# ```python
# def render(self, context: Context) -> str:
#     return self.nodelist.render(context)
# ```
#
# In django-components, the input to template tags is treated as function inputs, e.g.
#
# `{% component name="John" age=20 %}`
#
# And, for convenience, we want to allow the `render()` method to accept these extra parameters.
# That way, user can define just the `render()` method and have access to all the information:
#
# ```python
# def render(self, context: Context, name: str, **kwargs: Any) -> str:
#     return f"Hello, {name}!"
# ```
#
# So we need to wrap the `render()` method, and for that we need the metaclass.
#
# The outer `render()` (our wrapper) will match the `Node.render()` signature (accepting only `context`),
# while the inner `render()` (the actual implementation) will match the user-defined `render()` method's signature
# (accepting all the parameters).
class NodeMeta(type):
    def __new__(
        mcs,
        name: str,
        bases: Tuple[Type, ...],
        attrs: Dict[str, Any],
    ) -> Type["BaseNode"]:
        cls = cast(Type["BaseNode"], super().__new__(mcs, name, bases, attrs))

        # Ignore the `BaseNode` class itself
        if attrs.get("__module__", None) == "django_components.node":
            return cls

        if not hasattr(cls, "tag"):
            raise ValueError(f"Node {name} must have a 'tag' attribute")

        # Skip if already wrapped
        orig_render = cls.render
        if getattr(orig_render, "_djc_wrapped", False):
            return cls

        signature = inspect.signature(orig_render)

        # A full signature of `BaseNode.render()` may look like this:
        #
        # `def render(self, context: Context, name: str, **kwargs) -> str:`
        #
        # We need to remove the first two parameters from the signature.
        # So we end up only with
        #
        # `def render(name: str, **kwargs) -> str:`
        #
        # And this becomes the signature that defines what params the template tag accepts, e.g.
        #
        # `{% component name="John" age=20 %}`
        if len(signature.parameters) < 2:
            raise TypeError(f"`render()` method of {name} must have at least two parameters")

        validation_params = list(signature.parameters.values())
        validation_params = validation_params[2:]
        validation_signature = signature.replace(parameters=validation_params)

        # NOTE: This is used for creating docs by `_format_tag_signature()` in `docs/scripts/reference.py`
        cls._signature = validation_signature

        @functools.wraps(orig_render)
        def wrapper_render(self: "BaseNode", context: Context) -> str:
            trace_node_msg("RENDER", self.tag, self.node_id)

            resolved_params = resolve_params(self.tag, self.params, context)

            # Template tags may accept kwargs that are not valid Python identifiers, e.g.
            # `{% component data-id="John" class="pt-4" :href="myVar" %}`
            #
            # Passing them in is still useful, as user may want to pass in arbitrary data
            # to their `{% component %}` tags as HTML attributes. E.g. example below passes
            # `data-id`, `class` and `:href` as HTML attributes to the `<div>` element:
            #
            # ```py
            # class MyComponent(Component):
            #     def get_template_data(self, args, kwargs, slots, context) -> str:
            #         return {
            #             "name": kwargs.pop("name"),
            #             "attrs": kwargs,
            #         }
            #     template = """
            #         <div {% html_attrs attrs %}>
            #             {{ name }}
            #         </div>
            #     """
            # ```
            #
            # HOWEVER, these kwargs like `data-id`, `class` and `:href` may not be valid Python identifiers,
            # or like in case of `class`, may be a reserved keyword. Thus, we cannot pass them in to the `render()`
            # method as regular kwargs, because that will raise Python's native errors like
            # `SyntaxError: invalid syntax`. E.g.
            #
            # ```python
            # def render(self, context: Context, data-id: str, class: str, :href: str) -> str:
            # ```
            #
            # So instead, we filter out any invalid kwargs, and pass those in through a dictionary spread.
            # We can do so, because following is allowed in Python:
            #
            # ```python
            # def x(**kwargs):
            #     print(kwargs)
            #
            # d = {"data-id": 1}
            # x(**d)
            # # {'data-id': 1}
            # ```
            #
            # See https://github.com/django-components/django-components/discussions/900#discussioncomment-11859970
            resolved_params_without_invalid_kwargs = []
            invalid_kwargs = {}
            did_see_special_kwarg = False
            for resolved_param in resolved_params:
                key = resolved_param.key
                if key is not None:
                    # Case: Special kwargs
                    if not key.isidentifier() or keyword.iskeyword(key):
                        # NOTE: Since these keys are not part of signature validation,
                        # we have to check ourselves if any args follow them.
                        invalid_kwargs[key] = resolved_param.value
                        did_see_special_kwarg = True
                    else:
                        # Case: Regular kwargs
                        resolved_params_without_invalid_kwargs.append(resolved_param)
                else:
                    # Case: Regular positional args
                    if did_see_special_kwarg:
                        raise SyntaxError("positional argument follows keyword argument")
                    resolved_params_without_invalid_kwargs.append(resolved_param)

            # Validate the params against the signature
            #
            # This uses a signature that has been stripped of the `self` and `context` parameters. E.g.
            #
            # `def render(name: str, **kwargs: Any) -> None`
            #
            # If there are any errors in the input, this will trigger Python's
            # native error handling (e.g. `TypeError: render() got multiple values for argument 'context'`)
            #
            # But because we stripped the two parameters, then these errors will correctly
            # point to the actual error in the template tag.
            #
            # E.g. if we supplied one too many positional args,
            # `{% mytag "John" 20 %}`
            #
            # Then without stripping the two parameters, then the error could be:
            # `render() takes from 3 positional arguments but 4 were given`
            #
            # Which is confusing, because we supplied only two positional args.
            #
            # But cause we stripped the two parameters, then the error will be:
            # `render() takes from 1 positional arguments but 2 were given`
            args, kwargs = validate_params(
                orig_render,
                validation_signature,
                self.tag,
                resolved_params_without_invalid_kwargs,
                invalid_kwargs,
            )

            output = orig_render(self, context, *args, **kwargs)

            trace_node_msg("RENDER", self.tag, self.node_id, msg="...Done!")
            return output

        # Wrap cls.render() so we resolve the args and kwargs and pass them to the
        # actual render method.
        cls.render = wrapper_render  # type: ignore
        cls.render._djc_wrapped = True  # type: ignore

        return cls


class BaseNode(Node, metaclass=NodeMeta):
    """
    Node class for all django-components custom template tags.

    This class has a dual role:

    1. It declares how a particular template tag should be parsed - By setting the
       [`tag`](../api#django_components.BaseNode.tag),
       [`end_tag`](../api#django_components.BaseNode.end_tag),
       and [`allowed_flags`](../api#django_components.BaseNode.allowed_flags)
       attributes:

        ```python
        class SlotNode(BaseNode):
            tag = "slot"
            end_tag = "endslot"
            allowed_flags = ["required"]
        ```

        This will allow the template tag `{% slot %}` to be used like this:

        ```django
        {% slot required %} ... {% endslot %}
        ```

    2. The [`render`](../api#django_components.BaseNode.render) method is
        the actual implementation of the template tag.

        This is where the tag's logic is implemented:

        ```python
        class MyNode(BaseNode):
            tag = "mynode"

            def render(self, context: Context, name: str, **kwargs: Any) -> str:
                return f"Hello, {name}!"
        ```

        This will allow the template tag `{% mynode %}` to be used like this:

        ```django
        {% mynode name="John" %}
        ```

    The template tag accepts parameters as defined on the
    [`render`](../api#django_components.BaseNode.render) method's signature.

    For more info, see [`BaseNode.render()`](../api#django_components.BaseNode.render).
    """

    # #####################################
    # PUBLIC API (Configurable by users)
    # #####################################

    tag: str
    """
    The tag name.

    E.g. `"component"` or `"slot"` will make this class match
    template tags `{% component %}` or `{% slot %}`.
    """

    end_tag: Optional[str] = None
    """
    The end tag name.

    E.g. `"endcomponent"` or `"endslot"` will make this class match
    template tags `{% endcomponent %}` or `{% endslot %}`.

    If not set, then this template tag has no end tag.

    So instead of `{% component %} ... {% endcomponent %}`, you'd use only
    `{% component %}`.
    """

    allowed_flags: Optional[List[str]] = None
    """
    The allowed flags for this tag.

    E.g. `["required"]` will allow this tag to be used like `{% slot required %}`.
    """

    def render(self, context: Context, *args: Any, **kwargs: Any) -> str:
        """
        Render the node. This method is meant to be overridden by subclasses.

        The signature of this function decides what input the template tag accepts.

        The `render()` method MUST accept a `context` argument. Any arguments after that
        will be part of the tag's input parameters.

        So if you define a `render` method like this:

        ```python
        def render(self, context: Context, name: str, **kwargs: Any) -> str:
        ```

        Then the tag will require the `name` parameter, and accept any extra keyword arguments:

        ```django
        {% component name="John" age=20 %}
        ```
        """
        return self.nodelist.render(context)

    # #####################################
    # MISC
    # #####################################

    def __init__(
        self,
        params: List[TagAttr],
        flags: Optional[Dict[str, bool]] = None,
        nodelist: Optional[NodeList] = None,
        node_id: Optional[str] = None,
        contents: Optional[str] = None,
    ):
        self.params = params
        self.flags = flags or {flag: False for flag in self.allowed_flags or []}
        self.nodelist = nodelist or NodeList()
        self.node_id = node_id or gen_id()
        self.contents = contents

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: {self.node_id}. Contents: {repr(self.nodelist)}."
            f" Flags: {self.active_flags}>"
        )

    @property
    def active_flags(self) -> List[str]:
        """Flags that were set for this specific instance."""
        flags = []
        for flag, value in self.flags.items():
            if value:
                flags.append(flag)
        return flags

    @classmethod
    def parse(cls, parser: Parser, token: Token, **kwargs: Any) -> "BaseNode":
        """
        This function is what is passed to Django's `Library.tag()` when
        [registering the tag](https://docs.djangoproject.com/en/5.1/howto/custom-template-tags/#registering-the-tag).

        In other words, this method is called by Django's template parser when we encounter
        a tag that matches this node's tag, e.g. `{% component %}` or `{% slot %}`.

        To register the tag, you can use [`BaseNode.register()`](../api#django_components.BaseNode.register).
        """
        tag_id = gen_id()
        tag = parse_template_tag(cls.tag, cls.end_tag, cls.allowed_flags, parser, token)

        trace_node_msg("PARSE", cls.tag, tag_id)

        body, contents = tag.parse_body()
        node = cls(
            nodelist=body,
            node_id=tag_id,
            params=tag.params,
            flags=tag.flags,
            contents=contents,
            **kwargs,
        )

        trace_node_msg("PARSE", cls.tag, tag_id, "...Done!")
        return node

    @classmethod
    def register(cls, library: Library) -> None:
        """
        A convenience method for registering the tag with the given library.

        ```python
        class MyNode(BaseNode):
            tag = "mynode"

        MyNode.register(library)
        ```

        Allows you to then use the node in templates like so:

        ```django
        {% load mylibrary %}
        {% mynode %}
        ```
        """
        library.tag(cls.tag, cls.parse)

    @classmethod
    def unregister(cls, library: Library) -> None:
        """Unregisters the node from the given library."""
        library.tags.pop(cls.tag, None)


def template_tag(
    library: Library,
    tag: str,
    end_tag: Optional[str] = None,
    allowed_flags: Optional[List[str]] = None,
) -> Callable[[Callable], Callable]:
    """
    A simplified version of creating a template tag based on [`BaseNode`](../api#django_components.BaseNode).

    Instead of defining the whole class, you can just define the
    [`render()`](../api#django_components.BaseNode.render) method.

    ```python
    from django.template import Context, Library
    from django_components import BaseNode, template_tag

    library = Library()

    @template_tag(
        library,
        tag="mytag",
        end_tag="endmytag",
        allowed_flags=["required"],
    )
    def mytag(node: BaseNode, context: Context, name: str, **kwargs: Any) -> str:
        return f"Hello, {name}!"
    ```

    This will allow the template tag `{% mytag %}` to be used like this:

    ```django
    {% mytag name="John" %}
    {% mytag name="John" required %} ... {% endmytag %}
    ```

    The given function will be wrapped in a class that inherits from [`BaseNode`](../api#django_components.BaseNode).

    And this class will be registered with the given library.

    The function MUST accept at least two positional arguments: `node` and `context`

    - `node` is the [`BaseNode`](../api#django_components.BaseNode) instance.
    - `context` is the [`Context`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context)
        of the template.

    Any extra parameters defined on this function will be part of the tag's input parameters.

    For more info, see [`BaseNode.render()`](../api#django_components.BaseNode.render).
    """

    def decorator(fn: Callable) -> Callable:
        subcls_name = fn.__name__.title().replace("_", "").replace("-", "") + "Node"

        try:
            subcls: Type[BaseNode] = type(
                subcls_name,
                (BaseNode,),
                {
                    "tag": tag,
                    "end_tag": end_tag,
                    "allowed_flags": allowed_flags or [],
                    "render": fn,
                },
            )
        except Exception as e:
            raise e.__class__(f"Failed to create node class in 'template_tag()' for '{fn.__name__}'") from e

        subcls.register(library)

        # Allow to access the node class
        fn._node = subcls  # type: ignore[attr-defined]

        return fn

    return decorator
