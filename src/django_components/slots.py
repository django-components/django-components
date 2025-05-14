import difflib
import re
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from django.template import Context, Template
from django.template.base import NodeList, TextNode
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import ContextBehavior, app_settings
from django_components.context import _COMPONENT_CONTEXT_KEY, _INJECT_CONTEXT_KEY_PREFIX
from django_components.node import BaseNode
from django_components.perfutil.component import component_context_cache
from django_components.util.component_highlight import apply_component_highlight
from django_components.util.exception import add_slot_to_error_message
from django_components.util.logger import trace_component_msg
from django_components.util.misc import get_index, get_last_index, is_identifier

if TYPE_CHECKING:
    from django_components.component import ComponentContext, ComponentNode

TSlotData = TypeVar("TSlotData", bound=Mapping, contravariant=True)

DEFAULT_SLOT_KEY = "default"
FILL_GEN_CONTEXT_KEY = "_DJANGO_COMPONENTS_GEN_FILL"
SLOT_NAME_KWARG = "name"
SLOT_REQUIRED_FLAG = "required"
SLOT_DEFAULT_FLAG = "default"
FILL_DATA_KWARG = "data"
FILL_FALLBACK_KWARG = "fallback"


# Public types
SlotResult = Union[str, SafeString]


@runtime_checkable
class SlotFunc(Protocol, Generic[TSlotData]):
    def __call__(self, ctx: Context, slot_data: TSlotData, slot_ref: "SlotFallback") -> SlotResult: ...  # noqa E704


@dataclass
class Slot(Generic[TSlotData]):
    """This class holds the slot content function along with related metadata."""

    contents: Any
    """
    The original value that was passed to the `Slot` constructor.

    If the slot was defined with `{% fill %}` tag, this will be the raw string contents of the slot.
    """
    content_func: SlotFunc[TSlotData] = cast(SlotFunc[TSlotData], None)
    escaped: bool = False
    """Whether the slot content has been escaped."""

    # Following fields are only for debugging
    component_name: Optional[str] = None
    """Name of the component that originally defined or accepted this slot fill."""
    slot_name: Optional[str] = None
    """Name of the slot that originally defined or accepted this slot fill."""
    nodelist: Optional[NodeList] = None
    """If the slot was defined with `{% fill %} tag, this will be the Nodelist of the slot content."""

    def __post_init__(self) -> None:
        # Since the `Slot` instance is treated as a function, it may be passed as `contents`
        # to the `Slot()` constructor. In that case we need to unwrap to the original value
        # if `Slot()` constructor got another Slot instance.
        # NOTE: If `Slot` was passed as `contents`, we do NOT take the metadata from the inner Slot instance.
        #       Instead we treat is simply as a function.
        # NOTE: Try to avoid infinite loop if `Slot.contents` points to itself.
        seen_contents = set()
        while isinstance(self.contents, Slot) and self.contents not in seen_contents:
            seen_contents.add(id(self.contents))
            self.contents = self.contents.contents
        if id(self.contents) in seen_contents:
            raise ValueError("Detected infinite loop in `Slot.contents` pointing to itself")

        if self.content_func is None:
            self.contents, new_nodelist, self.content_func = self._resolve_contents(self.contents)
            if self.nodelist is None:
                self.nodelist = new_nodelist

        if not callable(self.content_func):
            raise ValueError(f"Slot content must be a callable, got: {self.content_func}")

    # Allow to treat the instances as functions
    def __call__(self, ctx: Context, slot_data: TSlotData, slot_ref: "SlotFallback") -> SlotResult:
        return self.content_func(ctx, slot_data, slot_ref)

    # Make Django pass the instances of this class within the templates without calling
    # the instances as a function.
    @property
    def do_not_call_in_templates(self) -> bool:
        return True

    def __repr__(self) -> str:
        comp_name = f"'{self.component_name}'" if self.component_name else None
        slot_name = f"'{self.slot_name}'" if self.slot_name else None
        return f"<{self.__class__.__name__} component_name={comp_name} slot_name={slot_name}>"

    def _resolve_contents(self, contents: Any) -> Tuple[Any, NodeList, SlotFunc[TSlotData]]:
        # Case: Content is a string / scalar, so we can use `TextNode` to render it.
        if not callable(contents):
            slot = _nodelist_to_slot(
                component_name=self.component_name or "<Slot._resolve_contents>",
                slot_name=self.slot_name,
                nodelist=NodeList([TextNode(contents)]),
                contents=contents,
                data_var=None,
                fallback_var=None,
            )
            return slot.contents, slot.nodelist, slot.content_func

        # Otherwise, we're dealing with a function.
        return contents, None, contents


# NOTE: This must be defined here, so we don't have any forward references
# otherwise Pydantic has problem resolving the types.
SlotInput = Union[SlotResult, SlotFunc[TSlotData], Slot[TSlotData]]
"""
When rendering a component with [`Component.render()`](../api#django_components.Component.render)
or [`Component.render_to_response()`](../api#django_components.Component.render_to_response),
the slots may be given a strings, functions, or [`Slot`](../api#django_components.Slot) instances.
This type describes that union.

Use this type when typing the slots in your component.

`SlotInput` accepts an optional type parameter to specify the data dictionary that will be passed to the
slot content function.

**Example:**

```python
from typing import NamedTuple
from typing_extensions import TypedDict
from django_components import Component, SlotInput

class TableFooterSlotData(TypedDict):
    page_number: int

class Table(Component):
    class Slots(NamedTuple):
        header: SlotInput
        footer: SlotInput[TableFooterSlotData]

    template = "<div>{% slot 'footer' %}</div>"
```
"""
# TODO_V1 - REMOVE, superseded by SlotInput
SlotContent = SlotInput[TSlotData]
"""
DEPRECATED: Use [`SlotInput`](../api#django_components.SlotInput) instead. Will be removed in v1.
"""


# Internal type aliases
SlotName = str


@dataclass(frozen=True)
class SlotFill(Generic[TSlotData]):
    """
    SlotFill describes what WILL be rendered.

    The fill may be provided by the user from the outside (`is_filled=True`),
    or it may be the default content of the slot (`is_filled=False`).
    """

    name: str
    """Name of the slot."""
    is_filled: bool
    slot: Slot[TSlotData]


class SlotFallback:
    """
    SlotFallback allows to treat a slot fallback as a variable. The slot is rendered only once
    the instance is coerced to string.

    This is used to access slots as variables inside the templates. When a `SlotFallback`
    is rendered in the template with `{{ my_lazy_slot }}`, it will output the contents
    of the slot.

    Usage in slot functions:

    ```py
    def slot_function(self, ctx: Context, slot_data: TSlotData, fallback: SlotFallback):
        return f"Hello, {fallback}!"
    ```
    """

    def __init__(self, slot: "SlotNode", context: Context):
        self._slot = slot
        self._context = context

    # Render the slot when the template coerces SlotFallback to string
    def __str__(self) -> str:
        return mark_safe(self._slot.nodelist.render(self._context))


# TODO_v1 - REMOVE - superseded by SlotFallback
SlotRef = SlotFallback


class SlotIsFilled(dict):
    """
    Dictionary that returns `True` if the slot is filled (key is found), `False` otherwise.
    """

    def __init__(self, fills: Dict, *args: Any, **kwargs: Any) -> None:
        escaped_fill_names = {_escape_slot_name(fill_name): True for fill_name in fills.keys()}
        super().__init__(escaped_fill_names, *args, **kwargs)

    def __missing__(self, key: Any) -> bool:
        return False


class SlotNode(BaseNode):
    """
    Slot tag marks a place inside a component where content can be inserted
    from outside.

    [Learn more](../../concepts/fundamentals/slots) about using slots.

    This is similar to slots as seen in
    [Web components](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/slot),
    [Vue](https://vuejs.org/guide/components/slots.html)
    or [React's `children`](https://react.dev/learn/passing-props-to-a-component#passing-jsx-as-children).

    **Args:**

    - `name` (str, required): Registered name of the component to render
    - `default`: Optional flag. If there is a default slot, you can pass the component slot content
        without using the [`{% fill %}`](#fill) tag. See
        [Default slot](../../concepts/fundamentals/slots#default-slot)
    - `required`: Optional flag. Will raise an error if a slot is required but not given.
    - `**kwargs`: Any extra kwargs will be passed as the slot data.

    **Example:**

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            {% slot "content" default %}
              This is shown if not overriden!
            {% endslot %}
          </div>
          <aside>
            {% slot "sidebar" required / %}
          </aside>
        \"\"\"
    ```

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          <div>
            {% component "child" %}
              {% fill "content" %}
                🗞️📰
              {% endfill %}

              {% fill "sidebar" %}
                🍷🧉🍾
              {% endfill %}
            {% endcomponent %}
          </div>
        \"\"\"
    ```

    ### Passing data to slots

    Any extra kwargs will be considered as slot data, and will be accessible in the [`{% fill %}`](#fill)
    tag via fill's `data` kwarg:

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            {# Passing data to the slot #}
            {% slot "content" user=user %}
              This is shown if not overriden!
            {% endslot %}
          </div>
        \"\"\"
    ```

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          {# Parent can access the slot data #}
          {% component "child" %}
            {% fill "content" data="data" %}
              <div class="wrapper-class">
                {{ data.user }}
              </div>
            {% endfill %}
          {% endcomponent %}
        \"\"\"
    ```

    ### Accessing fallback slot content

    The content between the `{% slot %}..{% endslot %}` tags is the fallback content that
    will be rendered if no fill is given for the slot.

    This fallback content can then be accessed from within the [`{% fill %}`](#fill) tag using
    the fill's `fallback` kwarg.
    This is useful if you need to wrap / prepend / append the original slot's content.

    ```python
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            {% slot "content" %}
              This is fallback content!
            {% endslot %}
          </div>
        \"\"\"
    ```

    ```python
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          {# Parent can access the slot's fallback content #}
          {% component "child" %}
            {% fill "content" fallback="fallback" %}
              {{ fallback }}
            {% endfill %}
          {% endcomponent %}
        \"\"\"
    ```
    """

    tag = "slot"
    end_tag = "endslot"
    allowed_flags = [SLOT_DEFAULT_FLAG, SLOT_REQUIRED_FLAG]

    # NOTE:
    # In the current implementation, the slots are resolved only at the render time.
    # So when we are rendering Django's Nodes, and we come across a SlotNode, only
    # at that point we check if we have the fill for it.
    #
    # That means that we can use variables, and we can place slots in loops.
    #
    # However, because the slot names are dynamic, we cannot know all the slot names
    # that will be rendered ahead of the time.
    #
    # Moreover, user may define a `{% slot %}` whose default content has more nested
    # `{% slot %}` tags inside of it.
    #
    # Previously, there was an error raised if there were unfilled slots or extra fills,
    # or if there was an extra fill for a default slot.
    #
    # But we don't raise those anymore, because:
    # 1. We don't know about ALL slots, just about the rendered ones, so we CANNOT check
    #    for unfilled slots (rendered slots WILL raise an error if the fill is missing).
    # 2. User may provide extra fills, but these may belong to slots we haven't
    #    encountered in this render run. So we CANNOT say which ones are extra.
    def render(self, context: Context, name: str, **kwargs: Any) -> SafeString:
        # Do not render `{% slot %}` tags within the `{% component %} .. {% endcomponent %}` tags
        # at the fill discovery stage (when we render the component's body to determine if the body
        # is a default slot, or contains named slots).
        if _is_extracting_fill(context):
            return ""

        if _COMPONENT_CONTEXT_KEY not in context or not context[_COMPONENT_CONTEXT_KEY]:
            raise TemplateSyntaxError(
                "Encountered a SlotNode outside of a Component context. "
                "Make sure that all {% slot %} tags are nested within {% component %} tags.\n"
                f"SlotNode: {self.__repr__()}"
            )

        component_id: str = context[_COMPONENT_CONTEXT_KEY]
        component_ctx = component_context_cache[component_id]
        component_name = component_ctx.component_name
        component_path = component_ctx.component_path
        slot_fills = component_ctx.fills
        slot_name = name
        is_default = self.flags[SLOT_DEFAULT_FLAG]
        is_required = self.flags[SLOT_REQUIRED_FLAG]

        trace_component_msg(
            "RENDER_SLOT_START",
            component_name=component_name,
            component_id=component_id,
            slot_name=slot_name,
            component_path=component_path,
            slot_fills=slot_fills,
            extra=f"Available fills: {slot_fills}",
        )

        # Check for errors
        if is_default and not component_ctx.is_dynamic_component:
            # Allow one slot to be marked as 'default', or multiple slots but with
            # the same name. If there is multiple 'default' slots with different names, raise.
            default_slot_name = component_ctx.default_slot
            if default_slot_name is not None and slot_name != default_slot_name:
                raise TemplateSyntaxError(
                    "Only one component slot may be marked as 'default', "
                    f"found '{default_slot_name}' and '{slot_name}'. "
                    f"To fix, check template '{component_ctx.template_name}' "
                    f"of component '{component_name}'."
                )

            if default_slot_name is None:
                component_ctx.default_slot = slot_name

            # If the slot is marked as 'default', check if user didn't double-fill it
            # by specifying the fill both by explicit slot name and implicitly as 'default'.
            if (
                slot_name != DEFAULT_SLOT_KEY
                and slot_fills.get(slot_name, False)
                and slot_fills.get(DEFAULT_SLOT_KEY, False)
            ):
                raise TemplateSyntaxError(
                    f"Slot '{slot_name}' of component '{component_name}' was filled twice: "
                    "once explicitly and once implicitly as 'default'."
                )

        # If slot is marked as 'default', we use the name 'default' for the fill,
        # IF SUCH FILL EXISTS. Otherwise, we use the slot's name.
        if is_default and DEFAULT_SLOT_KEY in slot_fills:
            fill_name = DEFAULT_SLOT_KEY
        else:
            fill_name = slot_name

        # NOTE: TBH not sure why this happens. But there's an edge case when:
        # 1. Using the "django" context behavior
        # 2. AND the slot fill is defined in the root template
        #
        # Then `ctx_with_fills.fills` does NOT contain any fills (`{% fill %}`). So in this case,
        # we need to use a different strategy to find the fills Context layer that contains the fills.
        #
        # ------------------------------------------------------------------------------------------
        #
        # Context:
        # When we render slot fills, we want to use the context as was OUTSIDE of the component.
        # E.g. In this example, we want to render `{{ item.name }}` inside the `{% fill %}` tag:
        #
        # ```django
        # {% for item in items %}
        #   {% component "my_component" %}
        #     {% fill "my_slot" %}
        #       {{ item.name }}
        #     {% endfill %}
        #   {% endcomponent %}
        # {% endfor %}
        # ```
        #
        # In this case, we need to find the context that was used to render the component,
        # and use the fills from that context.
        if (
            component_ctx.registry.settings.context_behavior == ContextBehavior.DJANGO
            and component_ctx.outer_context is None
            and (slot_name not in component_ctx.fills)
        ):
            # When we have nested components with fills, the context layers are added in
            # the following order:
            # Page -> SubComponent -> NestedComponent -> ChildComponent
            #
            # Then, if ChildComponent defines a `{% slot %}` tag, its `{% fill %}` will be defined
            # within the context of its parent, NestedComponent. The context is updated as follows:
            # Page -> SubComponent -> NestedComponent -> ChildComponent -> NestedComponent
            #
            # And if, WITHIN THAT `{% fill %}`, there is another `{% slot %}` tag, its `{% fill %}`
            # will be defined within the context of its parent, SubComponent. The context becomes:
            # Page -> SubComponent -> NestedComponent -> ChildComponent -> NestedComponent -> SubComponent
            #
            # If that top-level `{% fill %}` defines a `{% component %}`, and the component accepts a `{% fill %}`,
            # we'd go one down inside the component, and then one up outside of it inside the `{% fill %}`.
            # Page -> SubComponent -> NestedComponent -> ChildComponent -> NestedComponent -> SubComponent ->
            # -> CompA -> SubComponent
            #
            # So, given a context of nested components like this, we need to find which component was parent
            # of the current component, and use the fills from that component.
            #
            # In the Context, the components are identified by their ID, NOT by their name, as in the example above.
            # So the path is more like this:
            # a1b2c3 -> ax3c89 -> hui3q2 -> kok92a -> a1b2c3 -> kok92a -> hui3q2 -> d4e5f6 -> hui3q2
            #
            # We're at the right-most `hui3q2` (index 8), and we want to find `ax3c89` (index 1).
            # To achieve that, we first find the left-most `hui3q2` (index 2), and then find the `ax3c89`
            # in the list of dicts before it (index 1).
            curr_index = get_index(
                context.dicts, lambda d: _COMPONENT_CONTEXT_KEY in d and d[_COMPONENT_CONTEXT_KEY] == component_id
            )
            parent_index = get_last_index(context.dicts[:curr_index], lambda d: _COMPONENT_CONTEXT_KEY in d)

            # NOTE: There's an edge case when our component `hui3q2` appears at the start of the stack:
            # hui3q2 -> ax3c89 -> ... -> hui3q2
            #
            # Looking left finds nothing. In this case, look for the first component layer to the right.
            if parent_index is None and curr_index + 1 < len(context.dicts):
                parent_index = get_index(
                    context.dicts[curr_index + 1 :], lambda d: _COMPONENT_CONTEXT_KEY in d  # noqa: E203
                )
                if parent_index is not None:
                    parent_index = parent_index + curr_index + 1

            trace_component_msg(
                "SLOT_PARENT_INDEX",
                component_name=component_ctx.component_name,
                component_id=component_ctx.component_id,
                slot_name=name,
                component_path=component_ctx.component_path,
                extra=(
                    f"Parent index: {parent_index}, Current index: {curr_index}, "
                    f"Context stack: {[d.get(_COMPONENT_CONTEXT_KEY) for d in context.dicts]}"
                ),
            )
            if parent_index is not None:
                ctx_id_with_fills = context.dicts[parent_index][_COMPONENT_CONTEXT_KEY]
                ctx_with_fills = component_context_cache[ctx_id_with_fills]
                slot_fills = ctx_with_fills.fills

                # Add trace message when slot_fills are overwritten
                trace_component_msg(
                    "SLOT_FILLS_OVERWRITTEN",
                    component_name=component_name,
                    component_id=component_id,
                    slot_name=slot_name,
                    component_path=component_path,
                    extra=f"Slot fills overwritten in django mode. New fills: {slot_fills}",
                )

        if fill_name in slot_fills:
            slot_fill_fn = slot_fills[fill_name]
            slot_fill = SlotFill(
                name=slot_name,
                is_filled=True,
                slot=slot_fill_fn,
            )
        else:
            # No fill was supplied, render the slot's fallback content
            slot_fill = SlotFill(
                name=slot_name,
                is_filled=False,
                slot=_nodelist_to_slot(
                    component_name=component_name,
                    slot_name=slot_name,
                    nodelist=self.nodelist,
                    contents=self.contents,
                    data_var=None,
                    fallback_var=None,
                    # Escaped because this was defined in the template
                    escaped=True,
                ),
            )

        # Check: If a slot is marked as 'required', it must be filled.
        #
        # To help with easy-to-overlook typos, we fuzzy match unresolvable fills to
        # those slots for which no matching fill was encountered. In the event of
        # a close match, we include the name of the matched unfilled slot as a
        # hint in the error message.
        #
        # Note: Finding a good `cutoff` value may require further trial-and-error.
        # Higher values make matching stricter. This is probably preferable, as it
        # reduces false positives.
        if is_required and not slot_fill.is_filled and not component_ctx.is_dynamic_component:
            msg = (
                f"Slot '{slot_name}' is marked as 'required' (i.e. non-optional), "
                f"yet no fill is provided. Check template.'"
            )
            fill_names = list(slot_fills.keys())
            if fill_names:
                fuzzy_fill_name_matches = difflib.get_close_matches(fill_name, fill_names, n=1, cutoff=0.7)
                if fuzzy_fill_name_matches:
                    msg += f"\nDid you mean '{fuzzy_fill_name_matches[0]}'?"
            raise TemplateSyntaxError(msg)

        extra_context: Dict[str, Any] = {}

        # NOTE: If a user defines a `{% slot %}` tag inside a `{% fill %}` tag, two things
        # may happen based on the context mode:
        # 1. In the "isolated" mode, the context inside the fill is the same as outside of the component
        #    so any slots fill be filled with that same (parent) context.
        # 2. In the "django" mode, the context inside the fill is the same as the one inside the component,
        #
        # The "django" mode is problematic, because if we define a fill with the same name as the slot,
        # then we will enter an endless loop. E.g.:
        # ```django
        # {% component "mycomponent" %}
        #   {% slot "content" %}    <--,
        #     {% fill "content" %}  ---'
        #       ...
        #     {% endfill %}
        #   {% endslot %}
        # {% endcomponent %}
        # ```
        #
        # Hence, even in the "django" mode, we MUST use slots of the context of the parent component.
        if (
            component_ctx.registry.settings.context_behavior == ContextBehavior.DJANGO
            and component_ctx.outer_context is not None
            and _COMPONENT_CONTEXT_KEY in component_ctx.outer_context
        ):
            extra_context[_COMPONENT_CONTEXT_KEY] = component_ctx.outer_context[_COMPONENT_CONTEXT_KEY]
            # This ensures that `component_vars.is_filled`is accessible in the fill
            extra_context["component_vars"] = component_ctx.outer_context["component_vars"]

        # Irrespective of which context we use ("root" context or the one passed to this
        # render function), pass down the keys used by inject/provide feature. This makes it
        # possible to pass the provided values down through slots, e.g.:
        # {% provide "abc" val=123 %}
        #   {% slot "content" %}{% endslot %}
        # {% endprovide %}
        for key, value in context.flatten().items():
            if key.startswith(_INJECT_CONTEXT_KEY_PREFIX):
                extra_context[key] = value

        slot_ref = SlotFallback(self, context)

        # For the user-provided slot fill, we want to use the context of where the slot
        # came from (or current context if configured so)
        used_ctx = self._resolve_slot_context(context, slot_fill, component_ctx)
        with used_ctx.update(extra_context):
            # Required for compatibility with Django's {% extends %} tag
            # This makes sure that the render context used outside of a component
            # is the same as the one used inside the slot.
            # See https://github.com/django-components/django-components/pull/859
            if len(used_ctx.render_context.dicts) > 1 and "block_context" in used_ctx.render_context.dicts[-2]:
                render_ctx_layer = used_ctx.render_context.dicts[-2]
            else:
                # Otherwise we simply re-use the last layer, so that following logic uses `with` in either case
                render_ctx_layer = used_ctx.render_context.dicts[-1]

            with used_ctx.render_context.push(render_ctx_layer):
                with add_slot_to_error_message(component_name, slot_name):
                    # Render slot as a function
                    # NOTE: While `{% fill %}` tag has to opt in for the `fallback` and `data` variables,
                    #       the render function ALWAYS receives them.
                    output = slot_fill.slot(used_ctx, kwargs, slot_ref)

        if app_settings.DEBUG_HIGHLIGHT_SLOTS:
            output = apply_component_highlight("slot", output, f"{component_name} - {slot_name}")

        trace_component_msg(
            "RENDER_SLOT_END",
            component_name=component_name,
            component_id=component_id,
            slot_name=slot_name,
            component_path=component_path,
            slot_fills=slot_fills,
        )

        return output

    def _resolve_slot_context(
        self,
        context: Context,
        slot_fill: "SlotFill",
        component_ctx: "ComponentContext",
    ) -> Context:
        """Prepare the context used in a slot fill based on the settings."""
        # If slot is NOT filled, we use the slot's fallback AKA content between
        # the `{% slot %}` tags. These should be evaluated as if the `{% slot %}`
        # tags weren't even there, which means that we use the current context.
        if not slot_fill.is_filled:
            return context

        registry_settings = component_ctx.registry.settings
        if registry_settings.context_behavior == ContextBehavior.DJANGO:
            return context
        elif registry_settings.context_behavior == ContextBehavior.ISOLATED:
            outer_context = component_ctx.outer_context
            return outer_context if outer_context is not None else Context()
        else:
            raise ValueError(f"Unknown value for context_behavior: '{registry_settings.context_behavior}'")


class FillNode(BaseNode):
    """
    Use this tag to insert content into component's slots.

    `{% fill %}` tag may be used only within a `{% component %}..{% endcomponent %}` block.
    Runtime checks should prohibit other usages.

    **Args:**

    - `name` (str, required): Name of the slot to insert this content into. Use `"default"` for
        the default slot.
    - `fallback` (str, optional): This argument allows you to access the original content of the slot
        under the specified variable name. See [Slot fallback](../../concepts/fundamentals/slots#slot-fallback).
    - `data` (str, optional): This argument allows you to access the data passed to the slot
        under the specified variable name. See [Slot data](../../concepts/fundamentals/slots#slot-data).

    **Examples:**

    Basic usage:
    ```django
    {% component "my_table" %}
      {% fill "pagination" %}
        < 1 | 2 | 3 >
      {% endfill %}
    {% endcomponent %}
    ```

    ### Accessing slot's fallback content with the `fallback` kwarg

    ```django
    {# my_table.html #}
    <table>
      ...
      {% slot "pagination" %}
        < 1 | 2 | 3 >
      {% endslot %}
    </table>
    ```

    ```django
    {% component "my_table" %}
      {% fill "pagination" fallback="fallback" %}
        <div class="my-class">
          {{ fallback }}
        </div>
      {% endfill %}
    {% endcomponent %}
    ```

    ### Accessing slot's data with the `data` kwarg

    ```django
    {# my_table.html #}
    <table>
      ...
      {% slot "pagination" pages=pages %}
        < 1 | 2 | 3 >
      {% endslot %}
    </table>
    ```

    ```django
    {% component "my_table" %}
      {% fill "pagination" data="slot_data" %}
        {% for page in slot_data.pages %}
            <a href="{{ page.link }}">
              {{ page.index }}
            </a>
        {% endfor %}
      {% endfill %}
    {% endcomponent %}
    ```

    ### Accessing slot data and fallback content on the default slot

    To access slot data and the fallback slot content on the default slot,
    use `{% fill %}` with `name` set to `"default"`:

    ```django
    {% component "button" %}
      {% fill name="default" data="slot_data" fallback="slot_fallback" %}
        You clicked me {{ slot_data.count }} times!
        {{ slot_fallback }}
      {% endfill %}
    {% endcomponent %}
    ```
    """

    tag = "fill"
    end_tag = "endfill"
    allowed_flags = []

    def render(
        self,
        context: Context,
        name: str,
        *,
        data: Optional[str] = None,
        fallback: Optional[str] = None,
        # TODO_V1: Use `fallback` kwarg instead of `default`
        default: Optional[str] = None,
    ) -> str:
        # TODO_V1: Use `fallback` kwarg instead of `default`
        if fallback is not None and default is not None:
            raise TemplateSyntaxError(
                f"Fill tag received both 'default' and '{FILL_FALLBACK_KWARG}' kwargs. "
                f"Use '{FILL_FALLBACK_KWARG}' instead."
            )
        elif fallback is None and default is not None:
            fallback = default

        if not _is_extracting_fill(context):
            raise TemplateSyntaxError(
                "FillNode.render() (AKA {% fill ... %} block) cannot be rendered outside of a Component context. "
                "Make sure that the {% fill %} tags are nested within {% component %} tags."
            )

        # Validate inputs
        if not isinstance(name, str):
            raise TemplateSyntaxError(f"Fill tag '{SLOT_NAME_KWARG}' kwarg must resolve to a string, got {name}")

        if data is not None:
            if not isinstance(data, str):
                raise TemplateSyntaxError(f"Fill tag '{FILL_DATA_KWARG}' kwarg must resolve to a string, got {data}")
            if not is_identifier(data):
                raise RuntimeError(
                    f"Fill tag kwarg '{FILL_DATA_KWARG}' does not resolve to a valid Python identifier, got '{data}'"
                )

        if fallback is not None:
            if not isinstance(fallback, str):
                raise TemplateSyntaxError(
                    f"Fill tag '{FILL_FALLBACK_KWARG}' kwarg must resolve to a string, got {fallback}"
                )
            if not is_identifier(fallback):
                raise RuntimeError(
                    f"Fill tag kwarg '{FILL_FALLBACK_KWARG}' does not resolve to a valid Python identifier,"
                    f" got '{fallback}'"
                )

        # data and fallback cannot be bound to the same variable
        if data and fallback and data == fallback:
            raise RuntimeError(
                f"Fill '{name}' received the same string for slot fallback ({FILL_FALLBACK_KWARG}=...)"
                f" and slot data ({FILL_DATA_KWARG}=...)"
            )

        fill_data = FillWithData(
            fill=self,
            name=name,
            fallback_var=fallback,
            data_var=data,
            extra_context={},
        )

        self._extract_fill(context, fill_data)

        return ""

    def _extract_fill(self, context: Context, data: "FillWithData") -> None:
        # `FILL_GEN_CONTEXT_KEY` is only ever set when we are rendering content between the
        # `{% component %}...{% endcomponent %}` tags. This is done in order to collect all fill tags.
        # E.g.
        #   {% for slot_name in exposed_slots %}
        #     {% fill name=slot_name %}
        #       ...
        #     {% endfill %}
        #   {% endfor %}
        collected_fills: List[FillWithData] = context.get(FILL_GEN_CONTEXT_KEY, None)

        if collected_fills is None:
            return

        # To allow using variables which were defined within the template and to which
        # the `{% fill %}` tag has access, we need to capture those variables too.
        #
        # E.g.
        # ```django
        # {% component "three_slots" %}
        #     {% with slot_name="header" %}
        #         {% fill name=slot_name %}
        #             OVERRIDEN: {{ slot_name }}
        #         {% endfill %}
        #     {% endwith %}
        # {% endcomponent %}
        # ```
        #
        # NOTE: We want to capture only variables that were defined WITHIN
        # `{% component %} ... {% endcomponent %}`. Hence we search for the last
        # index of `FILL_GEN_CONTEXT_KEY`.
        index_of_new_layers = get_last_index(context.dicts, lambda d: FILL_GEN_CONTEXT_KEY in d)
        for dict_layer in context.dicts[index_of_new_layers:]:
            for key, value in dict_layer.items():
                if not key.startswith("_"):
                    data.extra_context[key] = value

        # To allow using the variables from the forloops inside the fill tags, we need to
        # capture those variables too.
        #
        # E.g.
        # {% component "three_slots" %}
        #     {% for outer in outer_loop %}
        #         {% for slot_name in the_slots %}
        #             {% fill name=slot_name|add:outer %}
        #                 OVERRIDEN: {{ slot_name }} - {{ outer }}
        #             {% endfill %}
        #         {% endfor %}
        #     {% endfor %}
        # {% endcomponent %}
        #
        # When we get to {% fill %} tag, the {% for %} tags have added extra info to the context.
        # This loop info can be identified by having key `forloop` in it.
        # There will be as many "forloop" dicts as there are for-loops.
        #
        # So `Context.dicts` may look like this:
        # [
        #   {'True': True, 'False': False, 'None': None},  # Default context
        #   {'forloop': {'parentloop': {...}, 'counter0': 2, 'counter': 3, ... }, 'outer': 2},
        #   {'forloop': {'parentloop': {...}, 'counter0': 1, 'counter': 2, ... }, 'slot_name': 'slot2'}
        # ]
        for layer in context.dicts:
            if "forloop" in layer:
                layer = layer.copy()
                layer["forloop"] = layer["forloop"].copy()
                data.extra_context.update(layer)

        collected_fills.append(data)


#######################################
# EXTRACTING {% fill %} FROM TEMPLATES
#######################################


class FillWithData(NamedTuple):
    fill: FillNode
    name: str
    fallback_var: Optional[str]
    data_var: Optional[str]
    extra_context: Dict[str, Any]


def resolve_fills(
    context: Context,
    component_node: "ComponentNode",
    component_name: str,
) -> Dict[SlotName, Slot]:
    """
    Given a component body (`django.template.NodeList`), find all slot fills,
    whether defined explicitly with `{% fill %}` or implicitly.

    So if we have a component body:
    ```django
    {% component "mycomponent" %}
        {% fill "first_fill" %}
            Hello!
        {% endfill %}
        {% fill "second_fill" %}
            Hello too!
        {% endfill %}
    {% endcomponent %}
    ```

    Then this function finds 2 fill nodes: "first_fill" and "second_fill",
    and formats them as slot functions, returning:

    ```python
    {
        "first_fill": SlotFunc(...),
        "second_fill": SlotFunc(...),
    }
    ```

    If no fill nodes are found, then the content is treated as default slot content.

    ```python
    {
        DEFAULT_SLOT_KEY: SlotFunc(...),
    }
    ```

    This function also handles for-loops, if/else statements, or include tags to generate fill tags:

    ```django
    {% component "mycomponent" %}
        {% for slot_name in slots %}
            {% fill name=slot_name %}
                {% slot name=slot_name / %}
            {% endfill %}
        {% endfor %}
    {% endcomponent %}
    ```
    """
    slots: Dict[SlotName, Slot] = {}

    nodelist = component_node.nodelist
    contents = component_node.contents

    if not nodelist:
        return slots

    maybe_fills = _extract_fill_content(nodelist, context, component_name)

    # The content has no fills, so treat it as default slot, e.g.:
    # {% component "mycomponent" %}
    #   Hello!
    #   {% if True %} 123 {% endif %}
    # {% endcomponent %}
    if maybe_fills is False:
        # Ignore empty content between `{% component %} ... {% endcomponent %}` tags
        nodelist_is_empty = not len(nodelist) or all(
            isinstance(node, TextNode) and not node.s.strip() for node in nodelist
        )

        if not nodelist_is_empty:
            slots[DEFAULT_SLOT_KEY] = _nodelist_to_slot(
                component_name=component_name,
                slot_name=None,  # Will be populated later
                nodelist=nodelist,
                contents=contents,
                data_var=None,
                fallback_var=None,
                # Escaped because this was defined in the template
                escaped=True,
            )

    # The content has fills
    else:
        # NOTE: If slot fills are explicitly defined, we use them even if they are empty (or only whitespace).
        #       This is different from the default slot, where we ignore empty content.
        for fill in maybe_fills:
            slots[fill.name] = _nodelist_to_slot(
                component_name=component_name,
                slot_name=fill.name,
                nodelist=fill.fill.nodelist,
                contents=fill.fill.contents,
                data_var=fill.data_var,
                fallback_var=fill.fallback_var,
                extra_context=fill.extra_context,
                # Escaped because this was defined in the template
                escaped=True,
            )

    return slots


def _extract_fill_content(
    nodes: NodeList,
    context: Context,
    component_name: str,
) -> Union[List[FillWithData], Literal[False]]:
    # When, during rendering of this tree, we encounter a {% fill %} node, instead of rendering content,
    # it will add itself into captured_fills, because `FILL_GEN_CONTEXT_KEY` is defined.
    captured_fills: List[FillWithData] = []
    with context.update({FILL_GEN_CONTEXT_KEY: captured_fills}):
        content = mark_safe(nodes.render(context).strip())

    # If we did not encounter any fills (not accounting for those nested in other
    # {% componenet %} tags), then we treat the content as default slot.
    if not captured_fills:
        return False

    elif content:
        raise TemplateSyntaxError(
            f"Illegal content passed to component '{component_name}'. "
            "Explicit 'fill' tags cannot occur alongside other text. "
            "The component body rendered content: {content}"
        )

    # Check for any duplicates
    seen_names: Set[str] = set()
    for fill in captured_fills:
        if fill.name in seen_names:
            raise TemplateSyntaxError(
                f"Multiple fill tags cannot target the same slot name in component '{component_name}': "
                f"Detected duplicate fill tag name '{fill.name}'."
            )
        seen_names.add(fill.name)

    return captured_fills


#######################################
# MISC
#######################################


name_escape_re = re.compile(r"[^\w]")


def _escape_slot_name(name: str) -> str:
    """
    Users may define slots with names which are invalid identifiers like 'my slot'.
    But these cannot be used as keys in the template context, e.g. `{{ component_vars.is_filled.'my slot' }}`.
    So as workaround, we instead use these escaped names which are valid identifiers.

    So e.g. `my slot` should be escaped as `my_slot`.
    """
    # NOTE: Do a simple substitution where we replace all non-identifier characters with `_`.
    # Identifiers consist of alphanum (a-zA-Z0-9) and underscores.
    # We don't check if these escaped names conflict with other existing slots in the template,
    # we leave this obligation to the user.
    escaped_name = name_escape_re.sub("_", name)
    return escaped_name


def _nodelist_to_slot(
    component_name: str,
    slot_name: Optional[str],
    nodelist: NodeList,
    contents: Optional[str] = None,
    data_var: Optional[str] = None,
    fallback_var: Optional[str] = None,
    escaped: bool = False,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Slot:
    if data_var:
        if not data_var.isidentifier():
            raise TemplateSyntaxError(
                f"Slot data alias in fill '{slot_name}' must be a valid identifier. Got '{data_var}'"
            )

    if fallback_var:
        if not fallback_var.isidentifier():
            raise TemplateSyntaxError(
                f"Slot fallback alias in fill '{slot_name}' must be a valid identifier. Got '{fallback_var}'"
            )

    # We use Template.render() to render the nodelist, so that Django correctly sets up
    # and binds the context.
    template = Template("")
    template.nodelist = nodelist
    # This allows the template to access current RenderContext layer.
    template._djc_is_component_nested = True

    def render_func(ctx: Context, slot_data: Dict[str, Any], slot_ref: SlotFallback) -> SlotResult:
        # Expose the kwargs that were passed to the `{% slot %}` tag. These kwargs
        # are made available through a variable name that was set on the `{% fill %}`
        # tag.
        if data_var:
            ctx[data_var] = slot_data

        # If slot fill is using `{% fill "myslot" fallback="abc" %}`, then set the "abc" to
        # the context, so users can refer to the fallback slot from within the fill content.
        if fallback_var:
            ctx[fallback_var] = slot_ref

        # NOTE: If a `{% fill %}` tag inside a `{% component %}` tag is inside a forloop,
        # the `extra_context` contains the forloop variables. We want to make these available
        # to the slot fill content.
        #
        # However, we cannot simply append the `extra_context` to the Context as the latest stack layer
        # because then the forloop variables override the slot fill variables. Instead, we have to put
        # the `extra_context` into the correct layer.
        #
        # Currently the `extra_context` is set only in `FillNode._extract_fill()` method
        # that is run when we render a `{% component %}` tag inside a template, and we need
        # to extract the fills from the tag's body.
        #
        # Thus, when we get here and `extra_context` is not None, it means that the component
        # is being rendered from within the template. And so we know that we're inside `Component._render()`.
        # And that means that the context MUST contain our internal context keys like `_COMPONENT_CONTEXT_KEY`.
        #
        # And so we want to put the `extra_context` into the same layer that contains `_COMPONENT_CONTEXT_KEY`.
        #
        # HOWEVER, the layer with `_COMPONENT_CONTEXT_KEY` also contains user-defined data from `get_template_data()`.
        # Data from `get_template_data()` should take precedence over `extra_context`. So we have to insert
        # the forloop variables BEFORE that.
        index_of_last_component_layer = get_last_index(ctx.dicts, lambda d: _COMPONENT_CONTEXT_KEY in d)
        if index_of_last_component_layer is None:
            index_of_last_component_layer = 0

        # TODO: Currently there's one more layer before the `_COMPONENT_CONTEXT_KEY` layer, which is
        #       pushed in `_prepare_template()` in `component.py`.
        #       That layer should be removed when `Component.get_template()` is removed, after which
        #       the following line can be removed.
        index_of_last_component_layer -= 1

        # Insert the `extra_context` layer BEFORE the layer that defines the variables from get_template_data.
        # Thus, get_template_data will overshadow these on conflict.
        ctx.dicts.insert(index_of_last_component_layer, extra_context or {})

        trace_component_msg("RENDER_NODELIST", component_name, component_id=None, slot_name=slot_name)

        # We wrap the slot nodelist in Template. However, we also override Django's `Template.render()`
        # to call `render_dependencies()` on the results. So we need to set the strategy to `ignore`
        # so that the dependencies are processed only once the whole component tree is rendered.
        with ctx.push({"DJC_DEPS_STRATEGY": "ignore"}):
            rendered = template.render(ctx)

        # After the rendering is done, remove the `extra_context` from the context stack
        ctx.dicts.pop(index_of_last_component_layer)

        return rendered

    return Slot(
        content_func=cast(SlotFunc, render_func),
        component_name=component_name,
        slot_name=slot_name,
        escaped=escaped,
        nodelist=nodelist,
        # The `contents` param passed to this function may be `None`, because it's taken from
        # `BaseNode.contents` which is `None` for self-closing tags like `{% fill "footer" / %}`.
        # But `Slot(contents=None)` would result in `Slot.contents` being the render function.
        # So we need to special-case this.
        contents=contents if contents is not None else "",
    )


def _is_extracting_fill(context: Context) -> bool:
    return context.get(FILL_GEN_CONTEXT_KEY, None) is not None
