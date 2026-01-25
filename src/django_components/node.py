import functools
import inspect
import re
import traceback
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast

from django.template import Context, Library
from django.template.base import Node, NodeList, Parser, Token
from djc_core.template_parser import ParserConfig, TagAttr, TagConfig, TagSpec, TemplateVersion

from django_components.util.logger import trace_node_msg
from django_components.util.misc import gen_id
from django_components.util.template_tag import (
    CompiledTagFn,
    compile_tag_params_resolver,
    parse_template_tag,
)

if TYPE_CHECKING:
    from django_components.component import Component


T = TypeVar("T", bound=Callable)


parser_config = ParserConfig(version=TemplateVersion.v1)


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
        bases: tuple[type, ...],
        attrs: dict[str, Any],
    ) -> type["BaseNode"]:
        cls = cast("type[BaseNode]", super().__new__(mcs, name, bases, attrs))

        # Ignore the `BaseNode` class itself
        if attrs.get("__module__") == "django_components.node":
            return cls

        if not hasattr(cls, "tag") or not cls.tag:
            raise ValueError(f"Node {name} must have a 'tag' attribute")

        tag_name = cls.tag

        # Remember the flags set for this tag, so that when we get to parsing templates,
        # we'll be able to pass this metadata to the parser.
        allowed_flags = attrs.get("allowed_flags")
        if allowed_flags:
            if tag_name in allowed_flags:
                raise ValueError(
                    f"Node {name}'s `tag` attribute ('{tag_name}') cannot be the same as one of its `allowed_flags`."
                )

            tag_config = TagConfig(tag=TagSpec(tag_name, set(allowed_flags)), sections=[])
            parser_config.set_tag(tag_config)

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

        # This runs when the node's template tag is being rendered.
        @functools.wraps(orig_render)
        def wrapper_render(self: "BaseNode", context: Context) -> str:
            trace_node_msg("RENDER", self.tag, self.node_id)

            if self._params_resolver is None:
                self._params_resolver = compile_tag_params_resolver(
                    tag_name=self.tag,
                    params=self.params,
                    source=self.start_tag_source or "",
                    filters=self.filters,
                    tags=self.tags,
                )

            args, kwargs = self._params_resolver(context)
            kwargs_dict = dict(kwargs)
            try:
                output = orig_render(self, context, *args, **kwargs_dict)
            except TypeError as e:
                # Modify error messages to omit the `context` argument
                # Only modify if the error occurred in the direct call to `orig_render`,
                # not in nested function calls.
                current_file = str(Path(__file__).resolve())
                _modify_typeerror_message(e, current_file)
                # Modify the error message to include the position within the template
                # if the Node was created from a template.
                if self.start_tag_source:
                    _format_error_with_template_position(
                        error=e,
                        # NOTE: Because we're using Django's `Parser` class, we don't have
                        # access to the WHOLE template, only the part that we've saved - the start tag.
                        # So we print at least that.
                        # Ideally, the `BaseNode` instance would have metadata about the original
                        # template (as a raw string), and the start/end indices of this Node.
                        source=self.start_tag_source,
                        start_index=0,
                        end_index=len(self.start_tag_source),
                        tag_name=self.tag,
                    )
                raise

            trace_node_msg("RENDER", self.tag, self.node_id, msg="...Done!")
            return output

        # Wrap cls.render() so we resolve the args and kwargs and pass them to the
        # actual render method.
        cls.render = wrapper_render  # type: ignore[assignment]
        cls.render._djc_wrapped = True  # type: ignore[attr-defined]

        return cls


class BaseNode(Node, metaclass=NodeMeta):
    """
    Node class for all django-components custom template tags.

    This class has a dual role:

    1. It declares how a particular template tag should be parsed - By setting the
       [`tag`](api.md#django_components.BaseNode.tag),
       [`end_tag`](api.md#django_components.BaseNode.end_tag),
       and [`allowed_flags`](api.md#django_components.BaseNode.allowed_flags) attributes:

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

    2. The [`render`](api.md#django_components.BaseNode.render) method is
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
    [`render`](api.md#django_components.BaseNode.render) method's signature.

    For more info, see [`BaseNode.render()`](api.md#django_components.BaseNode.render).
    """

    # #####################################
    # PUBLIC API (Configurable by users)
    # #####################################

    tag: ClassVar[str]
    """
    The tag name.

    E.g. `"component"` or `"slot"` will make this class match
    template tags `{% component %}` or `{% slot %}`.

    ```python
    class SlotNode(BaseNode):
        tag = "slot"
        end_tag = "endslot"
    ```

    This will allow the template tag `{% slot %}` to be used like this:

    ```django
    {% slot %} ... {% endslot %}
    ```
    """

    end_tag: ClassVar[str | None] = None
    """
    The end tag name.

    E.g. `"endcomponent"` or `"endslot"` will make this class match
    template tags `{% endcomponent %}` or `{% endslot %}`.

    ```python
    class SlotNode(BaseNode):
        tag = "slot"
        end_tag = "endslot"
    ```

    This will allow the template tag `{% slot %}` to be used like this:

    ```django
    {% slot %} ... {% endslot %}
    ```

    If not set, then this template tag has no end tag.

    So instead of `{% component %} ... {% endcomponent %}`, you'd use only
    `{% component %}`.

    ```python
    class MyNode(BaseNode):
        tag = "mytag"
        end_tag = None
    ```
    """

    allowed_flags: ClassVar[Iterable[str] | None] = None
    """
    The list of all *possible* flags for this tag.

    E.g. `["required"]` will allow this tag to be used like `{% slot required %}`.

    ```python
    class SlotNode(BaseNode):
        tag = "slot"
        end_tag = "endslot"
        allowed_flags = ["required", "default"]
    ```

    This will allow the template tag `{% slot %}` to be used like this:

    ```django
    {% slot required %} ... {% endslot %}
    {% slot default %} ... {% endslot %}
    {% slot required default %} ... {% endslot %}
    ```
    """

    def render(self, context: Context, *_args: Any, **_kwargs: Any) -> str:
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
    # Attributes
    # #####################################

    params: list[TagAttr]
    """
    The parameters to the tag in the template.

    A single param represents an arg or kwarg of the template tag.

    E.g. the following tag:

    ```django
    {% component "my_comp" key=val key2='val2 two' %}
    ```

    Has 3 params:

    - Posiitonal arg `"my_comp"`
    - Keyword arg `key=val`
    - Keyword arg `key2='val2 two'`
    """

    start_tag_source: str | None
    """
    The source code of the start tag with parameters as a string.

    E.g. the following tag:

    ```django
    {% slot "content" default required %}
      <div>
        ...
      </div>
    {% endslot %}
    ```

    The `start_tag_source` will be `"{% slot "content" default required %}"`.

    May be `None` if the `Node` instance was created manually.
    """

    flags: dict[str, bool]
    """
    Dictionary of all [`allowed_flags`](api.md#django_components.BaseNode.allowed_flags)
    that were set on the tag.

    Flags that were set are `True`, and the rest are `False`.

    E.g. the following tag:

    ```python
    class SlotNode(BaseNode):
        tag = "slot"
        end_tag = "endslot"
        allowed_flags = ["default", "required"]
    ```

    ```django
    {% slot "content" default %}
    ```

    Has 2 flags, `default` and `required`, but only `default` was set.

    The `flags` dictionary will be:

    ```python
    {
        "default": True,
        "required": False,
    }
    ```

    You can check if a flag is set by doing:

    ```python
    if node.flags["default"]:
        ...
    ```
    """

    filters: dict[str, Callable]
    """
    The filters available to the tag.

    This will be the same as the global Django filters.
    """

    tags: dict[str, Callable]
    """
    The tags available to the tag.

    This will be the same as the global Django tags.
    """

    nodelist: NodeList
    """
    The nodelist of the tag.

    This is the text between the opening and closing tags, e.g.

    ```django
    {% slot "content" default required %}
      <div>
        ...
      </div>
    {% endslot %}
    ```

    The `nodelist` will contain the `<div> ... </div>` part.

    Unlike [`contents`](api.md#django_components.BaseNode.contents),
    the `nodelist` contains the actual Nodes, not just the text.
    """

    contents: str | None
    """
    The body of the tag as a string.

    This is the text between the opening and closing tags, e.g.

    ```django
    {% slot "content" default required %}
      <div>
        ...
      </div>
    {% endslot %}
    ```

    The `contents` will be `"<div> ... </div>"`.
    """

    node_id: str
    """
    The unique ID of the node.

    Extensions can use this ID to store additional information.
    """

    template_name: str | None
    """
    The name of the [`Template`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template)
    that contains this node.

    The template name is set by Django's
    [template loaders](https://docs.djangoproject.com/en/5.2/topics/templates/#loaders).

    For example, the filesystem template loader will set this to the absolute path of the template file.

    ```
    "/home/user/project/templates/my_template.html"
    ```
    """

    template_component: type["Component"] | None
    """
    If the template that contains this node belongs to a [`Component`](api.md#django_components.Component),
    then this will be the [`Component`](api.md#django_components.Component) class.
    """

    # #####################################
    # MISC
    # #####################################

    def __init__(
        self,
        params: list[TagAttr],
        filters: dict[str, Callable[[Any, Any], Any]],
        tags: dict[str, Callable[[Any, Any], Any]],
        flags: dict[str, bool] | None = None,
        nodelist: NodeList | None = None,
        node_id: str | None = None,
        contents: str | None = None,
        template_name: str | None = None,
        template_component: type["Component"] | None = None,
        start_tag_source: str | None = None,
    ) -> None:
        self.params = params
        self._params_resolver: CompiledTagFn | None = None
        self.filters = filters
        self.tags = tags
        self.flags = flags or {flag: False for flag in self.allowed_flags or []}
        self.nodelist = nodelist or NodeList()
        self.node_id = node_id or gen_id()
        self.contents = contents
        self.template_name = template_name
        self.template_component = template_component
        self.start_tag_source = start_tag_source

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.node_id}. Contents: {self.contents}. Flags: {self.active_flags}>"

    @property
    def active_flags(self) -> list[str]:
        """
        Flags that were set for this specific instance as a list of strings.

        E.g. the following tag:

        ```django
        {% slot "content" default required / %}
        ```

        Will have the following flags:

        ```python
        ["default", "required"]
        ```
        """
        flags = []
        for flag, value in self.flags.items():
            if value:
                flags.append(flag)
        return flags

    @classmethod
    def parse(cls, parser: Parser, token: Token, **kwargs: Any) -> "BaseNode":
        """
        This function is what is passed to Django's `Library.tag()` when
        [registering the tag](https://docs.djangoproject.com/en/5.2/howto/custom-template-tags/#registering-the-tag).

        In other words, this method is called by Django's template parser when we encounter
        a tag that matches this node's tag, e.g. `{% component %}` or `{% slot %}`.

        To register the tag, you can use [`BaseNode.register()`](api.md#django_components.BaseNode.register).
        """
        # NOTE: Avoids circular import
        from django_components.template import get_component_from_origin  # noqa: PLC0415

        tag_id = gen_id()
        tag = parse_template_tag(cls.tag, cls.end_tag, parser_config, parser, token)

        trace_node_msg("PARSE", cls.tag, tag_id)

        body, contents = tag.parse_body()
        node = cls(
            nodelist=body,
            node_id=tag_id,
            params=tag.params,
            start_tag_source=tag.start_tag_source,
            filters=parser.filters,
            tags=parser.tags,
            flags=tag.flags,
            contents=contents,
            template_name=parser.origin.name if parser.origin else None,
            template_component=get_component_from_origin(parser.origin) if parser.origin else None,
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
    end_tag: str | None = None,
    allowed_flags: Iterable[str] | None = None,
) -> Callable[[Callable], Callable]:
    """
    A simplified version of creating a template tag based on [`BaseNode`](api.md#django_components.BaseNode).

    Instead of defining the whole class, you can just define the
    [`render()`](api.md#django_components.BaseNode.render) method.

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

    The given function will be wrapped in a class that inherits from [`BaseNode`](api.md#django_components.BaseNode).

    And this class will be registered with the given library.

    The function MUST accept at least two positional arguments: `node` and `context`

    - `node` is the [`BaseNode`](api.md#django_components.BaseNode) instance.
    - `context` is the [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
        of the template.

    Any extra parameters defined on this function will be part of the tag's input parameters.

    For more info, see [`BaseNode.render()`](api.md#django_components.BaseNode.render).
    """

    def decorator(fn: Callable) -> Callable:
        subcls_name = fn.__name__.title().replace("_", "").replace("-", "") + "Node"

        try:
            subcls: type[BaseNode] = type(
                subcls_name,
                (BaseNode,),
                {
                    "tag": tag,
                    "end_tag": end_tag,
                    "allowed_flags": allowed_flags or (),
                    "render": fn,
                },
            )
        except Exception as e:
            raise e.__class__(f"Failed to create node class in 'template_tag()' for '{fn.__name__}': {e}") from e

        subcls.register(library)

        # Allow to access the node class
        fn._node = subcls  # type: ignore[attr-defined]

        return fn

    return decorator


############################
# Helper functions
############################


# Modify TypeError messages to omit the `context` argument by reducing argument counts by 1.
#
# Only modifies errors that occurred in the direct function call (`orig_render`),
# not errors from nested function calls inside `orig_render`.
#
# ---
#
# We do this because when the user calls a component / node from within a template:
#
# ```django
# {% component "my_comp" name="John" age=20 %}
# ```
#
# Then we call the `render()` method of the `BaseNode` class, which is the actual implementation of the template tag.
#
# But we hide from the user the fact that we pass `context` as the first argument to the `render()` method.
#
# Note: Python doesn't count `self` in error messages (it's passed automatically), so we only need
# to subtract 1 for `context`, not 2 for `self` and `context`.
def _modify_typeerror_message(error: TypeError, current_file: str) -> None:
    """Modify TypeError messages in place to omit the `context` argument."""
    error_msg = str(error)

    # Try to figure out if the error occurred when calling the `BaseNode.render()` method
    # (the one to which we supplied the `self` and `context`), or in a nested function,
    # by inspecting the traceback.
    # If error occured in a nested function, we do NOT modify this error message.
    tb = error.__traceback__
    should_modify = True
    if tb is not None:
        frames = traceback.extract_tb(tb)
        if frames:
            # Check if the error occurred in the wrapper function (where we call orig_render)
            # The last frame is where the error actually occurred
            last_frame = frames[-1]

            # If the error occurred in a different file, it's definitely nested
            # Normalize paths for cross-platform compatibility (Windows uses different separators/casing)
            current_file_normalized = str(Path(current_file).resolve())
            last_frame_filename_normalized = str(Path(last_frame.filename).resolve())
            if last_frame_filename_normalized != current_file_normalized:
                should_modify = False

            # Additional check: if there are more than 2 frames, it's likely nested
            # (1 for the wrapper, 1+ for nested calls)
            # We use a threshold of 2 to be conservative
            elif len(frames) > 2:
                # Error likely occurred in a nested function call, don't modify
                should_modify = False

    if not should_modify:
        return

    # Pattern 1: "takes from X to Y positional arguments but Z were given"
    # In this case Python includes also our `self` argument, so we subtract 2.
    pattern1 = r"takes from (\d+) to (\d+) positional arguments? but (\d+) (?:were|was) given"
    match = re.search(pattern1, error_msg)
    if match:
        min_expected = max(0, int(match.group(1)) - 2)
        max_expected = max(0, int(match.group(2)) - 2)
        got = max(0, int(match.group(3)) - 2)
        got_verb = "were" if got != 1 else "was"
        if min_expected == max_expected:
            plural = "s" if min_expected != 1 else ""
            replacement = f"takes {min_expected} positional argument{plural} but {got} {got_verb} given"
        else:
            replacement = (
                f"takes from {min_expected} to {max_expected} positional arguments but {got} {got_verb} given"
            )
        error_msg = re.sub(pattern1, replacement, error_msg)
        error.args = (error_msg,)
        return

    # Pattern 2: "takes X positional argument(s) but Y were given"
    # In this case Python includes also our `self` argument, so we subtract 2.
    pattern2 = r"takes (\d+) positional argument(?:s)? but (\d+) (?:were|was) given"
    match = re.search(pattern2, error_msg)
    if match:
        expected = max(0, int(match.group(1)) - 2)
        got = max(0, int(match.group(2)) - 2)
        expected_plural = "s" if expected != 1 else ""
        got_verb = "were" if got != 1 else "was"
        replacement = f"takes {expected} positional argument{expected_plural} but {got} {got_verb} given"
        error_msg = re.sub(pattern2, replacement, error_msg)
        error.args = (error_msg,)
        return

    # NOTE: We don't have to modify following patterns:
    # - "missing X required keyword-only argument(s): 'argname'"
    #   -> Because we do NOT supply kwargs, so all missing kwargs are user-defined
    # - "missing X required positional argument(s): 'argname'"
    #   -> Because we supply the FIRST pos arg, so all remaining missing pos args are user-defined
    return


def _format_error_with_template_position(
    error: Exception,
    source: str,
    start_index: int,
    end_index: int,
    tag_name: str,
) -> None:
    """
    Format an error with underlined source code context.

    Modifies the exception's message to include:
    - Up to 2 preceding lines
    - The lines containing the error (start_index to end_index)
    - Up to 2 following lines
    - Underlined code with ^^^ characters

    **Example:**

    ```
    TypeError: Error in mytag3: missing 1 required keyword-only argument: 'msg' and 'mode'

        1 | {% mytag3 'John' %}
            ^^^^^^^^^^^^^^^^^^^
    ```
    """
    # Convert source to lines with line numbers
    lines = source.split("\n")

    # Find which lines contain the error
    line_starts = [0]  # Cumulative character count at start of each line
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)  # +1 for newline

    # Find start and end line numbers (0-indexed)
    start_line = 0
    for i, line_start in enumerate(line_starts):
        if line_start > start_index:
            start_line = max(0, i - 1)
            break
    else:
        start_line = len(lines) - 1

    end_line = start_line
    for i, line_start in enumerate(line_starts):
        if line_start > end_index:
            end_line = max(0, i - 1)
            break
    else:
        end_line = len(lines) - 1

    # Calculate column positions within each line
    def get_column(line_num: int, char_index: int) -> int:
        """Get column number (0-indexed) for a character index in a specific line."""
        if line_num >= len(line_starts):
            return 0
        line_start = line_starts[line_num]
        return max(0, char_index - line_start)

    start_col = get_column(start_line, start_index)
    end_col = get_column(end_line, end_index)

    # Collect lines to show (up to 2 before and 2 after)
    show_start = max(0, start_line - 2)
    show_end = min(len(lines), end_line + 3)  # +3 because end is inclusive

    # Format the error like:
    # ```
    # TypeError: Error in mytag3: missing 1 required keyword-only argument: 'msg' and 'mode'
    #
    #      1 | {% mytag3 'John' %}
    #          ^^^^^^^^^^^^^^^^^^^
    # ```
    error_lines = []
    error_lines.append(f"Error in {tag_name}: {error}")
    error_lines.append("")

    # Add source lines with line numbers
    for line_num in range(show_start, show_end):
        line_content = lines[line_num]
        line_display_num = line_num + 1  # 1-indexed for display

        # Calculate underline range for this line
        underline_start = 0
        underline_end = len(line_content)

        if line_num == start_line == end_line:
            # Error spans single line
            underline_start = start_col
            underline_end = min(len(line_content), end_col)
        elif line_num == start_line:
            # Error starts on this line
            underline_start = start_col
            underline_end = len(line_content)
        elif line_num == end_line:
            # Error ends on this line
            underline_start = 0
            underline_end = min(len(line_content), end_col)
        elif start_line < line_num < end_line:
            # Error spans this entire line
            underline_start = 0
            underline_end = len(line_content)
        else:
            # No error on this line, don't underline
            underline_start = -1
            underline_end = -1

        # Add line with number
        line_prefix = f"  {line_display_num:4d} | "
        error_lines.append(line_prefix + line_content)

        # Add underline if error is on this line
        if underline_start >= 0:
            # Create underline: prefix spaces + spaces to column + ^ characters
            prefix_len = len(line_prefix)  # "    4 | " = 9 characters
            underline = " " * (prefix_len + underline_start) + "^" * max(1, underline_end - underline_start)
            error_lines.append(underline)

    # Update exception message
    error.args = ("\n".join(error_lines),)
    # Mark that this error has been processed by error_context
    error._error_processed = True  # type: ignore[attr-defined]
