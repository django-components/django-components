import difflib
import re
from dataclasses import dataclass, field
from dataclasses import replace as dataclass_replace
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
from django.utils.html import conditional_escape
from django.utils.safestring import SafeString, mark_safe

from django_components.app_settings import ContextBehavior
from django_components.context import _COMPONENT_CONTEXT_KEY, _INJECT_CONTEXT_KEY_PREFIX
from django_components.extension import OnSlotRenderedContext, extensions
from django_components.node import BaseNode
from django_components.perfutil.component import component_context_cache
from django_components.util.exception import add_slot_to_error_message
from django_components.util.logger import trace_component_msg
from django_components.util.misc import default, get_index, get_last_index, is_identifier

if TYPE_CHECKING:
    from django_components.component import Component, ComponentNode

TSlotData = TypeVar("TSlotData", bound=Mapping)

DEFAULT_SLOT_KEY = "default"
FILL_GEN_CONTEXT_KEY = "_DJANGO_COMPONENTS_GEN_FILL"
SLOT_NAME_KWARG = "name"
SLOT_REQUIRED_FLAG = "required"
SLOT_DEFAULT_FLAG = "default"
FILL_DATA_KWARG = "data"
FILL_FALLBACK_KWARG = "fallback"
FILL_BODY_KWARG = "body"


# Public types
SlotResult = Union[str, SafeString]
"""
Type representing the result of a slot render function.

**Example:**

```python
from django_components import SlotContext, SlotResult

def my_slot_fn(ctx: SlotContext) -> SlotResult:
    return "Hello, world!"

my_slot = Slot(my_slot_fn)
html = my_slot()  # Output: Hello, world!
```

Read more about [Slot functions](../../concepts/fundamentals/slots#slot-functions).
"""


@dataclass(frozen=True)
class SlotContext(Generic[TSlotData]):
    """
    Metadata available inside slot functions.

    Read more about [Slot functions](../../concepts/fundamentals/slots#slot-class).

    **Example:**

    ```python
    from django_components import SlotContext, SlotResult

    def my_slot(ctx: SlotContext) -> SlotResult:
        return f"Hello, {ctx.data['name']}!"
    ```

    You can pass a type parameter to the `SlotContext` to specify the type of the data passed to the slot:

    ```python
    class MySlotData(TypedDict):
        name: str

    def my_slot(ctx: SlotContext[MySlotData]):
        return f"Hello, {ctx.data['name']}!"
    ```
    """

    data: TSlotData
    """
    Data passed to the slot.

    Read more about [Slot data](../../concepts/fundamentals/slots#slot-data).

    **Example:**

    ```python
    def my_slot(ctx: SlotContext):
        return f"Hello, {ctx.data['name']}!"
    ```
    """
    fallback: Optional[Union[str, "SlotFallback"]] = None
    """
    Slot's fallback content. Lazily-rendered - coerce this value to string to force it to render.

    Read more about [Slot fallback](../../concepts/fundamentals/slots#slot-fallback).

    **Example:**

    ```python
    def my_slot(ctx: SlotContext):
        return f"Hello, {ctx.fallback}!"
    ```

    May be `None` if you call the slot fill directly, without using [`{% slot %}`](../template_tags#slot) tags.
    """
    context: Optional[Context] = None
    """
    Django template [`Context`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context)
    available inside the [`{% fill %}`](../template_tags#fill) tag.

    May be `None` if you call the slot fill directly, without using [`{% slot %}`](../template_tags#slot) tags.
    """


@runtime_checkable
class SlotFunc(Protocol, Generic[TSlotData]):
    """
    When rendering components with
    [`Component.render()`](../api#django_components.Component.render)
    or
    [`Component.render_to_response()`](../api#django_components.Component.render_to_response),
    the slots can be given either as strings or as functions.

    If a slot is given as a function, it will have the signature of `SlotFunc`.

    Read more about [Slot functions](../../concepts/fundamentals/slots#slot-functions).

    Args:
        ctx (SlotContext): Single named tuple that holds the slot data and metadata.

    Returns:
        (str | SafeString): The rendered slot content.

    **Example:**

    ```python
    from django_components import SlotContext, SlotResult

    def header(ctx: SlotContext) -> SlotResult:
        if ctx.data.get("name"):
            return f"Hello, {ctx.data['name']}!"
        else:
            return ctx.fallback

    html = MyTable.render(
        slots={
            "header": header,
        },
    )
    ```
    """

    def __call__(self, ctx: SlotContext[TSlotData]) -> SlotResult: ...  # noqa E704


@dataclass
class Slot(Generic[TSlotData]):
    """
    This class is the main way for defining and handling slots.

    It holds the slot content function along with related metadata.

    Read more about [Slot class](../../concepts/fundamentals/slots#slot-class).

    **Example:**

    Passing slots to components:

    ```python
    from django_components import Slot

    slot = Slot(lambda ctx: f"Hello, {ctx.data['name']}!")

    MyComponent.render(
        slots={
            "my_slot": slot,
        },
    )
    ```

    Accessing slots inside the components:

    ```python
    from django_components import Component

    class MyComponent(Component):
        def get_template_data(self, args, kwargs, slots, context):
            my_slot = slots["my_slot"]
            return {
                "my_slot": my_slot,
            }
    ```

    Rendering slots:

    ```python
    from django_components import Slot

    slot = Slot(lambda ctx: f"Hello, {ctx.data['name']}!")
    html = slot({"name": "John"})  # Output: Hello, John!
    ```
    """

    contents: Any
    """
    The original value that was passed to the `Slot` constructor.

    - If Slot was created from [`{% fill %}`](../template_tags#fill) tag, `Slot.contents` will contain
      the body (string) of that `{% fill %}` tag.
    - If Slot was created from string as `Slot("...")`, `Slot.contents` will contain that string.
    - If Slot was created from a function, `Slot.contents` will contain that function.

    Read more about [Slot contents](../../concepts/fundamentals/slots#slot-contents).
    """
    content_func: SlotFunc[TSlotData] = cast(SlotFunc[TSlotData], None)
    """
    The actual slot function.

    Do NOT call this function directly, instead call the `Slot` instance as a function.

    Read more about [Rendering slot functions](../../concepts/fundamentals/slots#rendering-slots).
    """

    # Following fields are only for debugging
    component_name: Optional[str] = None
    """
    Name of the component that originally received this slot fill.

    See [Slot metadata](../../concepts/fundamentals/slots#slot-metadata).
    """
    slot_name: Optional[str] = None
    """
    Slot name to which this Slot was initially assigned.

    See [Slot metadata](../../concepts/fundamentals/slots#slot-metadata).
    """
    nodelist: Optional[NodeList] = None
    """
    If the slot was defined with [`{% fill %}`](../template_tags#fill) tag,
    this will be the Nodelist of the fill's content.

    See [Slot metadata](../../concepts/fundamentals/slots#slot-metadata).
    """
    fill_node: Optional[Union["FillNode", "ComponentNode"]] = None
    """
    If the slot was created from a [`{% fill %}`](../template_tags#fill) tag,
    this will be the [`FillNode`](../api/#django_components.FillNode) instance.

    If the slot was a default slot created from a [`{% component %}`](../template_tags#component) tag,
    this will be the [`ComponentNode`](../api/#django_components.ComponentNode) instance.

    Otherwise, this will be `None`.

    Extensions can use this info to handle slots differently based on their source.

    See [Slot metadata](../../concepts/fundamentals/slots#slot-metadata).

    **Example:**

    You can use this to find the [`Component`](../api/#django_components.Component) in whose
    template the [`{% fill %}`](../template_tags#fill) tag was defined:

    ```python
    class MyTable(Component):
        def get_template_data(self, args, kwargs, slots, context):
            footer_slot = slots.get("footer")
            if footer_slot is not None and footer_slot.fill_node is not None:
                owner_component = footer_slot.fill_node.template_component
                # ...
    ```
    """
    extra: Dict[str, Any] = field(default_factory=dict)
    """
    Dictionary that can be used to store arbitrary metadata about the slot.

    See [Slot metadata](../../concepts/fundamentals/slots#slot-metadata).

    See [Pass slot metadata](../../concepts/advanced/extensions#pass-slot-metadata)
    for usage for extensions.

    **Example:**

    ```python
    # Either at slot creation
    slot = Slot(lambda ctx: "Hello, world!", extra={"foo": "bar"})

    # Or later
    slot.extra["baz"] = "qux"
    ```
    """

    def __post_init__(self) -> None:
        # Raise if Slot received another Slot instance as `contents`,
        # because this leads to ambiguity about how to handle the metadata.
        if isinstance(self.contents, Slot):
            raise ValueError("Slot received another Slot instance as `contents`")

        if self.content_func is None:
            self.contents, new_nodelist, self.content_func = self._resolve_contents(self.contents)
            if self.nodelist is None:
                self.nodelist = new_nodelist

        if not callable(self.content_func):
            raise ValueError(f"Slot 'content_func' must be a callable, got: {self.content_func}")

    # Allow to treat the instances as functions
    def __call__(
        self,
        data: Optional[TSlotData] = None,
        fallback: Optional[Union[str, "SlotFallback"]] = None,
        context: Optional[Context] = None,
    ) -> SlotResult:
        slot_ctx: SlotContext = SlotContext(context=context, data=data or {}, fallback=fallback)
        result = self.content_func(slot_ctx)
        return conditional_escape(result)

    # Make Django pass the instances of this class within the templates without calling
    # the instances as a function.
    @property
    def do_not_call_in_templates(self) -> bool:
        """
        Django special property to prevent calling the instance as a function
        inside Django templates.
        """
        return True

    def __repr__(self) -> str:
        comp_name = f"'{self.component_name}'" if self.component_name else None
        slot_name = f"'{self.slot_name}'" if self.slot_name else None
        return f"<{self.__class__.__name__} component_name={comp_name} slot_name={slot_name}>"

    def _resolve_contents(self, contents: Any) -> Tuple[Any, NodeList, SlotFunc[TSlotData]]:
        # Case: Content is a string / scalar, so we can use `TextNode` to render it.
        if not callable(contents):
            contents = str(contents) if not isinstance(contents, (str, SafeString)) else contents
            contents = conditional_escape(contents)
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
Type representing all forms in which slot content can be passed to a component.

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

html = Table.render(
    slots={
        # As a string
        "header": "Hello, World!",

        # Safe string
        "header": mark_safe("<i><am><safe>"),

        # Function
        "footer": lambda ctx: f"Page: {ctx.data['page_number']}!",

        # Slot instance
        "footer": Slot(lambda ctx: f"Page: {ctx.data['page_number']}!"),

        # None (Same as no slot)
        "header": None,
    },
)
```
"""
# TODO_V1 - REMOVE, superseded by SlotInput
SlotContent = SlotInput[TSlotData]
"""
DEPRECATED: Use [`SlotInput`](../api#django_components.SlotInput) instead. Will be removed in v1.
"""


# Internal type aliases
SlotName = str


class SlotFallback:
    """
    The content between the `{% slot %}..{% endslot %}` tags is the *fallback* content that
    will be rendered if no fill is given for the slot.

    ```django
    {% slot "name" %}
        Hello, my name is {{ name }}  <!-- Fallback content -->
    {% endslot %}
    ```

    Because the fallback is defined as a piece of the template
    ([`NodeList`](https://github.com/django/django/blob/ddb85294159185c5bd5cae34c9ef735ff8409bfe/django/template/base.py#L1017)),
    we want to lazily render it only when needed.

    `SlotFallback` type allows to pass around the slot fallback as a variable.

    To force the fallback to render, coerce it to string to trigger the `__str__()` method.

    **Example:**

    ```py
    def slot_function(self, ctx: SlotContext):
        return f"Hello, {ctx.fallback}!"
    ```
    """  # noqa: E501

    def __init__(self, slot: "SlotNode", context: Context):
        self._slot = slot
        self._context = context

    # Render the slot when the template coerces SlotFallback to string
    def __str__(self) -> str:
        return mark_safe(self._slot.nodelist.render(self._context))


# TODO_v1 - REMOVE - superseded by SlotFallback
SlotRef = SlotFallback
"""
DEPRECATED: Use [`SlotFallback`](../api#django_components.SlotFallback) instead. Will be removed in v1.
"""


name_escape_re = re.compile(r"[^\w]")


# TODO_v1 - Remove, superseded by `Component.slots` and `component_vars.slots`
class SlotIsFilled(dict):
    """
    Dictionary that returns `True` if the slot is filled (key is found), `False` otherwise.
    """

    def __init__(self, fills: Dict, *args: Any, **kwargs: Any) -> None:
        escaped_fill_names = {self._escape_slot_name(fill_name): True for fill_name in fills.keys()}
        super().__init__(escaped_fill_names, *args, **kwargs)

    def __missing__(self, key: Any) -> bool:
        return False

    def _escape_slot_name(self, name: str) -> str:
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


class SlotNode(BaseNode):
    """
    [`{% slot %}`](../template_tags#slot) tag marks a place inside a component where content can be inserted
    from outside.

    [Learn more](../../concepts/fundamentals/slots) about using slots.

    This is similar to slots as seen in
    [Web components](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/slot),
    [Vue](https://vuejs.org/guide/components/slots.html)
    or [React's `children`](https://react.dev/learn/passing-props-to-a-component#passing-jsx-as-children).

    **Args:**

    - `name` (str, required): Registered name of the component to render
    - `default`: Optional flag. If there is a default slot, you can pass the component slot content
        without using the [`{% fill %}`](../template_tags#fill) tag. See
        [Default slot](../../concepts/fundamentals/slots#default-slot)
    - `required`: Optional flag. Will raise an error if a slot is required but not given.
    - `**kwargs`: Any extra kwargs will be passed as the slot data.

    **Example:**

    ```djc_py
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

    ```djc_py
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

    ### Slot data

    Any extra kwargs will be considered as slot data, and will be accessible
    in the [`{% fill %}`](../template_tags#fill) tag via fill's `data` kwarg:

    Read more about [Slot data](../../concepts/fundamentals/slots#slot-data).

    ```djc_py
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

    ```djc_py
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

    ### Slot fallback

    The content between the `{% slot %}..{% endslot %}` tags is the fallback content that
    will be rendered if no fill is given for the slot.

    This fallback content can then be accessed from within the [`{% fill %}`](../template_tags#fill) tag
    using the fill's `fallback` kwarg.
    This is useful if you need to wrap / prepend / append the original slot's content.

    ```djc_py
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

    ```djc_py
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

        # Component info
        component_id: str = context[_COMPONENT_CONTEXT_KEY]
        component_ctx = component_context_cache[component_id]
        component = component_ctx.component
        component_name = component.name
        component_path = component_ctx.component_path
        is_dynamic_component = getattr(component, "_is_dynamic_component", False)
        # NOTE: Use `ComponentContext.outer_context`, and NOT `Component.outer_context`.
        #       The first is a SNAPSHOT of the outer context.
        outer_context = component_ctx.outer_context

        # Slot info
        slot_fills = component.raw_slots
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
        if is_default and not is_dynamic_component:
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
        # Then `ctx_with_fills.component.raw_slots` does NOT contain any fills (`{% fill %}`). So in this case,
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
            component.registry.settings.context_behavior == ContextBehavior.DJANGO
            and outer_context is None
            and (slot_name not in slot_fills)
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
                component_name=component_name,
                component_id=component_id,
                slot_name=name,
                component_path=component_path,
                extra=(
                    f"Parent index: {parent_index}, Current index: {curr_index}, "
                    f"Context stack: {[d.get(_COMPONENT_CONTEXT_KEY) for d in context.dicts]}"
                ),
            )
            if parent_index is not None:
                ctx_id_with_fills = context.dicts[parent_index][_COMPONENT_CONTEXT_KEY]
                ctx_with_fills = component_context_cache[ctx_id_with_fills]
                slot_fills = ctx_with_fills.component.raw_slots

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
            slot_is_filled = True
            slot = slot_fills[fill_name]
        else:
            # No fill was supplied, render the slot's fallback content
            slot_is_filled = False
            slot = _nodelist_to_slot(
                component_name=component_name,
                slot_name=slot_name,
                nodelist=self.nodelist,
                contents=self.contents,
                data_var=None,
                fallback_var=None,
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
        if is_required and not slot_is_filled and not is_dynamic_component:
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
            component.registry.settings.context_behavior == ContextBehavior.DJANGO
            and outer_context is not None
            and _COMPONENT_CONTEXT_KEY in outer_context
        ):
            extra_context[_COMPONENT_CONTEXT_KEY] = outer_context[_COMPONENT_CONTEXT_KEY]
            # This ensures that the ComponentVars API (e.g. `{{ component_vars.is_filled }}`) is accessible in the fill
            extra_context["component_vars"] = outer_context["component_vars"]

        # Irrespective of which context we use ("root" context or the one passed to this
        # render function), pass down the keys used by inject/provide feature. This makes it
        # possible to pass the provided values down through slots, e.g.:
        # {% provide "abc" val=123 %}
        #   {% slot "content" %}{% endslot %}
        # {% endprovide %}
        for key, value in context.flatten().items():
            if key.startswith(_INJECT_CONTEXT_KEY_PREFIX):
                extra_context[key] = value

        fallback = SlotFallback(self, context)

        # For the user-provided slot fill, we want to use the context of where the slot
        # came from (or current context if configured so)
        used_ctx = self._resolve_slot_context(context, slot_is_filled, component, outer_context)
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
                    output = slot(data=kwargs, fallback=fallback, context=used_ctx)

        # Allow plugins to post-process the slot's rendered output
        output = extensions.on_slot_rendered(
            OnSlotRenderedContext(
                component=component,
                component_cls=component.__class__,
                component_id=component_id,
                slot=slot,
                slot_name=slot_name,
                slot_node=self,
                slot_is_required=is_required,
                slot_is_default=is_default,
                result=output,
            ),
        )

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
        slot_is_filled: bool,
        component: "Component",
        outer_context: Optional[Context],
    ) -> Context:
        """Prepare the context used in a slot fill based on the settings."""
        # If slot is NOT filled, we use the slot's fallback AKA content between
        # the `{% slot %}` tags. These should be evaluated as if the `{% slot %}`
        # tags weren't even there, which means that we use the current context.
        if not slot_is_filled:
            return context

        registry_settings = component.registry.settings
        if registry_settings.context_behavior == ContextBehavior.DJANGO:
            return context
        elif registry_settings.context_behavior == ContextBehavior.ISOLATED:
            return outer_context if outer_context is not None else Context()
        else:
            raise ValueError(f"Unknown value for context_behavior: '{registry_settings.context_behavior}'")


class FillNode(BaseNode):
    """
    Use [`{% fill %}`](../template_tags#fill) tag to insert content into component's
    [slots](../../concepts/fundamentals/slots).

    [`{% fill %}`](../template_tags#fill) tag may be used only within a `{% component %}..{% endcomponent %}` block,
    and raises a `TemplateSyntaxError` if used outside of a component.

    **Args:**

    - `name` (str, required): Name of the slot to insert this content into. Use `"default"` for
        the [default slot](../../concepts/fundamentals/slots#default-slot).
    - `data` (str, optional): This argument allows you to access the data passed to the slot
        under the specified variable name. See [Slot data](../../concepts/fundamentals/slots#slot-data).
    - `fallback` (str, optional): This argument allows you to access the original content of the slot
        under the specified variable name. See [Slot fallback](../../concepts/fundamentals/slots#slot-fallback).

    **Example:**

    ```django
    {% component "my_table" %}
      {% fill "pagination" %}
        < 1 | 2 | 3 >
      {% endfill %}
    {% endcomponent %}
    ```

    ### Access slot fallback

    Use the `fallback` kwarg to access the original content of the slot.

    The `fallback` kwarg defines the name of the variable that will contain the slot's fallback content.

    Read more about [Slot fallback](../../concepts/fundamentals/slots#slot-fallback).

    Component template:

    ```django
    {# my_table.html #}
    <table>
      ...
      {% slot "pagination" %}
        < 1 | 2 | 3 >
      {% endslot %}
    </table>
    ```

    Fill:

    ```django
    {% component "my_table" %}
      {% fill "pagination" fallback="fallback" %}
        <div class="my-class">
          {{ fallback }}
        </div>
      {% endfill %}
    {% endcomponent %}
    ```

    ### Access slot data

    Use the `data` kwarg to access the data passed to the slot.

    The `data` kwarg defines the name of the variable that will contain the slot's data.

    Read more about [Slot data](../../concepts/fundamentals/slots#slot-data).

    Component template:

    ```django
    {# my_table.html #}
    <table>
      ...
      {% slot "pagination" pages=pages %}
        < 1 | 2 | 3 >
      {% endslot %}
    </table>
    ```

    Fill:

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

    ### Using default slot

    To access slot data and the fallback slot content on the default slot,
    use [`{% fill %}`](../template_tags#fill) with `name` set to `"default"`:

    ```django
    {% component "button" %}
      {% fill name="default" data="slot_data" fallback="slot_fallback" %}
        You clicked me {{ slot_data.count }} times!
        {{ slot_fallback }}
      {% endfill %}
    {% endcomponent %}
    ```

    ### Slot fills from Python

    You can pass a slot fill from Python to a component by setting the `body` kwarg
    on the [`{% fill %}`](../template_tags#fill) tag.

    First pass a [`Slot`](../api#django_components.Slot) instance to the template
    with the [`get_template_data()`](../api#django_components.Component.get_template_data)
    method:

    ```python
    from django_components import component, Slot

    class Table(Component):
      def get_template_data(self, args, kwargs, slots, context):
        return {
            "my_slot": Slot(lambda ctx: "Hello, world!"),
        }
    ```

    Then pass the slot to the [`{% fill %}`](../template_tags#fill) tag:

    ```django
    {% component "table" %}
      {% fill "pagination" body=my_slot / %}
    {% endcomponent %}
    ```

    !!! warning

        If you define both the `body` kwarg and the [`{% fill %}`](../template_tags#fill) tag's body,
        an error will be raised.

        ```django
        {% component "table" %}
          {% fill "pagination" body=my_slot %}
            ...
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
        body: Optional[SlotInput] = None,
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

        if body is not None and self.contents:
            raise TemplateSyntaxError(
                f"Fill '{name}' received content both through '{FILL_BODY_KWARG}' kwarg and '{{% fill %}}' body. "
                f"Use only one method."
            )

        fill_data = FillWithData(
            fill=self,
            name=name,
            fallback_var=fallback,
            data_var=data,
            extra_context={},
            body=body,
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
        captured_fills: Optional[List[FillWithData]] = context.get(FILL_GEN_CONTEXT_KEY, None)

        if captured_fills is None:
            raise RuntimeError(
                "FillNode.render() (AKA {% fill ... %} block) cannot be rendered outside of a Component context. "
                "Make sure that the {% fill %} tags are nested within {% component %} tags."
            )

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
        context_dicts: List[Dict[str, Any]] = context.dicts
        for dict_layer in context_dicts[index_of_new_layers:]:
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

        captured_fills.append(data)


#######################################
# EXTRACTING {% fill %} FROM TEMPLATES
# (internal)
#######################################


class FillWithData(NamedTuple):
    fill: FillNode
    name: str
    """Name of the slot to be filled, as set on the `{% fill %}` tag."""
    body: Optional[SlotInput]
    """
    Slot fill as set by the `body` kwarg on the `{% fill %}` tag.

    E.g.
    ```django
    {% component "mycomponent" %}
        {% fill "footer" body=my_slot / %}
    {% endcomponent %}
    ```
    """
    fallback_var: Optional[str]
    """Name of the FALLBACK variable, as set on the `{% fill %}` tag."""
    data_var: Optional[str]
    """Name of the DATA variable, as set on the `{% fill %}` tag."""
    extra_context: Dict[str, Any]
    """
    Extra context variables that will be available inside the `{% fill %}` tag.

    For example, if the `{% fill %}` tags are nested within `{% with %}` or `{% for %}` tags,
    then the variables defined within those tags will be available inside the `{% fill %}` tags:

    ```django
    {% component "mycomponent" %}
        {% with extra_var="extra_value" %}
            {% fill "my_fill" %}
                {{ extra_var }}
            {% endfill %}
        {% endwith %}
        {% for item in items %}
            {% fill "my_fill" %}
                {{ item }}
            {% endfill %}
        {% endfor %}
    {% endcomponent %}
    ```
    """


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
                fill_node=component_node,
            )

    # The content has fills
    else:
        # NOTE: If slot fills are explicitly defined, we use them even if they are empty (or only whitespace).
        #       This is different from the default slot, where we ignore empty content.
        for fill in maybe_fills:
            # Case: Slot fill was explicitly defined as `{% fill body=... / %}`
            if fill.body is not None:
                # Set `Slot.fill_node` so the slot fill behaves the same as if it was defined inside
                # a `{% fill %}` tag.
                # This for example allows CSS scoping to work even on slots that are defined
                # as `{% fill ... body=... / %}`
                if isinstance(fill.body, Slot):
                    # Make a copy of the Slot instance and set its `fill_node`.
                    slot_fill = dataclass_replace(fill.body, fill_node=fill.fill)
                else:
                    slot_fill = Slot(fill.body, fill_node=fill.fill)
            # Case: Slot fill was defined as the body of `{% fill / %}...{% endfill %}`
            else:
                slot_fill = _nodelist_to_slot(
                    component_name=component_name,
                    slot_name=fill.name,
                    nodelist=fill.fill.nodelist,
                    contents=fill.fill.contents,
                    data_var=fill.data_var,
                    fallback_var=fill.fallback_var,
                    extra_context=fill.extra_context,
                    fill_node=fill.fill,
                )
            slots[fill.name] = slot_fill

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


def normalize_slot_fills(
    fills: Mapping[SlotName, SlotInput],
    component_name: Optional[str] = None,
) -> Dict[SlotName, Slot]:
    norm_fills = {}

    # NOTE: `copy_slot` is defined as a separate function, instead of being inlined within
    #       the forloop, because the value the forloop variable points to changes with each loop iteration.
    def copy_slot(content: Union[SlotFunc, Slot], slot_name: str) -> Slot:
        # Case: Already Slot and names assigned, so nothing to do.
        if isinstance(content, Slot) and content.slot_name and content.component_name:
            return content

        # Otherwise, we create a new instance of Slot, whether we've been given Slot or not,
        # so we can assign metadata to our internal copies without affecting the original.
        if not isinstance(content, Slot):
            content_func = content
        else:
            content_func = content.content_func

        # Populate potentially missing fields so we can trace the component and slot
        if isinstance(content, Slot):
            used_component_name = content.component_name or component_name
            used_slot_name = content.slot_name or slot_name
            used_nodelist = content.nodelist
            used_contents = content.contents if content.contents is not None else content_func
            used_fill_node = content.fill_node
            used_extra = content.extra.copy()
        else:
            used_component_name = component_name
            used_slot_name = slot_name
            used_nodelist = None
            used_contents = content_func
            used_fill_node = None
            used_extra = {}

        slot = Slot(
            contents=used_contents,
            content_func=content_func,
            component_name=used_component_name,
            slot_name=used_slot_name,
            nodelist=used_nodelist,
            fill_node=used_fill_node,
            extra=used_extra,
        )

        return slot

    for slot_name, content in fills.items():
        # Case: No content, so nothing to do.
        if content is None:
            continue
        # Case: Content is a string / non-slot / non-callable
        elif not callable(content):
            # NOTE: `Slot.content_func` and `Slot.nodelist` will be set in `Slot.__init__()`
            slot: Slot = Slot(contents=content, component_name=component_name, slot_name=slot_name)
        # Case: Content is a callable, so either a plain function or a `Slot` instance.
        else:
            slot = copy_slot(content, slot_name)

        norm_fills[slot_name] = slot

    return norm_fills


def _nodelist_to_slot(
    component_name: str,
    slot_name: Optional[str],
    nodelist: NodeList,
    contents: Optional[str] = None,
    data_var: Optional[str] = None,
    fallback_var: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
    fill_node: Optional[Union[FillNode, "ComponentNode"]] = None,
    extra: Optional[Dict[str, Any]] = None,
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

    def render_func(ctx: SlotContext) -> SlotResult:
        context = ctx.context or Context()

        # Expose the kwargs that were passed to the `{% slot %}` tag. These kwargs
        # are made available through a variable name that was set on the `{% fill %}`
        # tag.
        if data_var:
            context[data_var] = ctx.data

        # If slot fill is using `{% fill "myslot" fallback="abc" %}`, then set the "abc" to
        # the context, so users can refer to the fallback slot from within the fill content.
        if fallback_var:
            context[fallback_var] = ctx.fallback

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
        index_of_last_component_layer = get_last_index(context.dicts, lambda d: _COMPONENT_CONTEXT_KEY in d)
        if index_of_last_component_layer is None:
            index_of_last_component_layer = 0

        # TODO_V1: Currently there's one more layer before the `_COMPONENT_CONTEXT_KEY` layer, which is
        #       pushed in `_prepare_template()` in `component.py`.
        #       That layer should be removed when `Component.get_template()` is removed, after which
        #       the following line can be removed.
        index_of_last_component_layer -= 1

        # Insert the `extra_context` layer BEFORE the layer that defines the variables from get_template_data.
        # Thus, get_template_data will overshadow these on conflict.
        context.dicts.insert(index_of_last_component_layer, extra_context or {})

        trace_component_msg("RENDER_NODELIST", component_name, component_id=None, slot_name=slot_name)

        # We wrap the slot nodelist in Template. However, we also override Django's `Template.render()`
        # to call `render_dependencies()` on the results. So we need to set the strategy to `ignore`
        # so that the dependencies are processed only once the whole component tree is rendered.
        with context.push({"DJC_DEPS_STRATEGY": "ignore"}):
            rendered = template.render(context)

        # After the rendering is done, remove the `extra_context` from the context stack
        context.dicts.pop(index_of_last_component_layer)

        return rendered

    return Slot(
        content_func=cast(SlotFunc, render_func),
        component_name=component_name,
        slot_name=slot_name,
        nodelist=nodelist,
        # The `contents` param passed to this function may be `None`, because it's taken from
        # `BaseNode.contents` which is `None` for self-closing tags like `{% fill "footer" / %}`.
        # But `Slot(contents=None)` would result in `Slot.contents` being the render function.
        # So we need to special-case this.
        contents=default(contents, ""),
        fill_node=default(fill_node, None),
        extra=default(extra, {}),
    )


def _is_extracting_fill(context: Context) -> bool:
    return context.get(FILL_GEN_CONTEXT_KEY, None) is not None
