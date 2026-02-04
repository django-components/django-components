import re
from collections import deque
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TypeAlias, cast
from weakref import ReferenceType, WeakKeyDictionary, ref

from django.http import HttpRequest
from django.template import Context, RequestContext, Template
from django.template.loader_tags import BLOCK_CONTEXT_KEY, BlockContext
from django.test.signals import template_rendered
from django.utils.safestring import mark_safe

from django_components.constants import COMP_ID_LENGTH
from django_components.context import _COMPONENT_CONTEXT_KEY, COMPONENT_IS_NESTED_KEY
from django_components.dependencies import (
    DependenciesStrategy,
    cache_component_css,
    cache_component_css_vars,
    cache_component_js,
    cache_component_js_vars,
    insert_component_dependencies_comment,
    set_component_attrs_for_js_and_css,
)
from django_components.dependencies import render_dependencies as _render_dependencies
from django_components.extension import (
    OnComponentDataContext,
    OnComponentInputContext,
    OnComponentRenderedContext,
    extensions,
)
from django_components.perfutil.provide import register_provide_reference
from django_components.template import prepare_component_template
from django_components.util.context import snapshot_context
from django_components.util.exception import set_component_error_message, with_component_error_message
from django_components.util.logger import trace_component_msg
from django_components.util.misc import default, gen_component_id, is_generator, to_dict

if TYPE_CHECKING:
    from django_components.component import (
        Component,
        ComponentNode,
    )
    from django_components.component_registry import ComponentRegistry
    from django_components.slots import SlotResult


ComponentRef: TypeAlias = ReferenceType["Component"]
StartedGenerators: TypeAlias = WeakKeyDictionary["OnRenderGenerator", bool]
OnComponentRenderedResult: TypeAlias = tuple[str | None, Exception | None]


OnRenderGenerator: TypeAlias = Generator[
    "SlotResult | Callable[[], SlotResult] | None",
    "tuple[SlotResult | None, Exception | None]",
    "SlotResult | None",
]
"""
This is the signature of the [`Component.on_render()`](api.md#django_components.Component.on_render)
method if it yields (and thus returns a generator).

When `on_render()` is a generator then it:

- Yields a rendered template (string or `None`) or a lambda function to be called later.

- Receives back a tuple of `(final_output, error)`.

    The final output is the rendered template that now has all its children rendered too.
    May be `None` if you yielded `None` earlier.

    The error is `None` if the rendering was successful. Otherwise the error is set
    and the output is `None`.

- Can yield multiple times within the same method for complex rendering scenarios

- At the end it may return a new string to override the final rendered output.

**Example:**

```py
from django_components import Component, OnRenderGenerator

class MyTable(Component):
    def on_render(
        self,
        context: Context,
        template: Template | None,
    ) -> OnRenderGenerator:
        # Do something BEFORE rendering template
        # Same as `Component.on_render_before()`
        context["hello"] = "world"

        # Yield a function that renders the template
        # to receive fully-rendered template or error.
        html, error = yield lambda: template.render(context)

        # Do something AFTER rendering template, or post-process
        # the rendered template.
        # Same as `Component.on_render_after()`
        if html is not None:
            return html + "<p>Hello</p>"
```

**Multiple yields example:**

```py
class MyTable(Component):
    def on_render(self, context, template) -> OnRenderGenerator:
        # First yield
        with context.push({"mode": "header"}):
            header_html, header_error = yield lambda: template.render(context)

        # Second yield
        with context.push({"mode": "body"}):
            body_html, body_error = yield lambda: template.render(context)

        # Third yield
        footer_html, footer_error = yield "Footer content"

        # Process all results
        if header_error or body_error or footer_error:
            return "Error occurred during rendering"

        return f"{header_html}\n{body_html}\n{footer_html}"
```
"""


# Internal data that's shared across the entire component tree
@dataclass
class ComponentTreeContext:
    # HTML attributes that are passed from parent to child components
    component_attrs: dict[str, list[str]]
    # When we render a component, the root component, together with all the nested Components,
    # shares these dictionaries for storing callbacks.
    # These callbacks are called from within `component_post_render`
    on_component_intermediate_callbacks: dict[str, Callable[[str | None], str | None]]
    on_component_rendered_callbacks: dict[str, Callable[[str | None, Exception | None], OnComponentRenderedResult]]
    # Track which generators have been started. We need this info because the input to
    # `Generator.send()` changes when calling it the first time vs subsequent times.
    # Moreover, we can't simply store this directly on the generator object themselves
    # (e.g. `generator.started = True`), because generator object does not allow setting
    # extra attributes.
    started_generators: StartedGenerators


# Internal data that are made available within the component's template
@dataclass
class ComponentContext:
    component: ComponentRef
    component_path: list[str]
    template_name: str | None
    default_slot: str | None
    outer_context: Context | None
    tree: ComponentTreeContext
    root_id: str | None  # ID of the root component in this tree


# We want to track whether we are inside a component rendering logic.
#
# One use case is to skip the need to pass `deps_strategy="ignore"` explicitly when
# rendering a component nested in another's `get_template_data()`:
#
# ```py
# class Inner(Component):
#     template: types.django_html = '<span class="inner">inner</span>'
#
# class Outer(Component):
#     def get_template_data(self, args, kwargs, slots, context):
#         content = Inner.render()
#         return {"content": content}
#
# rendered = Outer.render()
# ```
#
# To keep track of this, every time we step into `Component.render()`, we push a sentinel value
# onto the stack. When we finish rendering the current Component, we pop the sentinel value off the stack.
#
# See https://github.com/django-components/django-components/issues/1463
_component_render_stack: ContextVar[list[Any] | None] = ContextVar(
    "djc_component_render_stack",
    default=None,
)


def _is_inside_component_render() -> bool:
    """True if we are currently inside a component render (e.g. inside get_template_data)."""
    stack = _component_render_stack.get()
    return stack is not None and len(stack) > 0


@contextmanager
def _render_stack(
    deps_strategy: DependenciesStrategy | None,
) -> Generator[DependenciesStrategy, None, None]:
    """
    Manage populating and emptying the component render stack,
    and resolving of the default `deps_strategy` when nested.
    """
    # Outside of Component context, we default to "document" deps_strategy,
    # so that the rendered HTML can be served from the server directly.
    # But when inside another component, we set the default to "ignore" so that
    # the dependencies are not rendered twice.
    if deps_strategy is None:
        deps_strategy = "ignore" if _is_inside_component_render() else "document"

    stack = _component_render_stack.get()
    if stack is None:
        stack = []
        _component_render_stack.set(stack)
    stack.append(None)  # sentinel
    try:
        yield deps_strategy
    finally:
        stack.pop()


def render_with_error_trace(
    comp_cls: type["Component"],
    context: dict[str, Any] | Context | None = None,
    args: Any | None = None,
    kwargs: Any | None = None,
    slots: Any | None = None,
    deps_strategy: DependenciesStrategy | None = None,
    request: HttpRequest | None = None,
    outer_context: Context | None = None,
    # TODO_v2 - Remove `registered_name` and `registry`
    registry: "ComponentRegistry | None" = None,
    registered_name: str | None = None,
    node: "ComponentNode | None" = None,
) -> str:
    """
    Internal entrypoint for the render function.
    Wraps `_render_impl` with error trace and cleanup.
    """
    component_name = comp_cls._get_component_name(registered_name)

    # Modify the error to display full component path (incl. slots)
    with with_component_error_message([component_name]):
        render_id = gen_component_id()
        with _render_stack(deps_strategy) as deps_strategy_with_default:
            try:
                return _render_impl(
                    comp_cls=comp_cls,
                    render_id=render_id,
                    context=context,
                    args=args,
                    kwargs=kwargs,
                    slots=slots,
                    deps_strategy=deps_strategy_with_default,
                    request=request,
                    outer_context=outer_context,
                    # TODO_v2 - Remove `registered_name` and `registry`
                    registry=registry,
                    registered_name=registered_name,
                    node=node,
                )
            except Exception as e:
                # Clean up if rendering fails
                component_instance_cache.pop(render_id, None)
                raise e from None


def _render_impl(
    comp_cls: type["Component"],
    render_id: str,
    deps_strategy: DependenciesStrategy,
    context: dict[str, Any] | Context | None = None,
    args: Any | None = None,
    kwargs: Any | None = None,
    slots: Any | None = None,
    request: HttpRequest | None = None,
    outer_context: Context | None = None,
    # TODO_v2 - Remove `registered_name` and `registry`
    registry: "ComponentRegistry | None" = None,
    registered_name: str | None = None,
    node: "ComponentNode | None" = None,
) -> str:
    """
    Core render implementation: handle inputs, prepare state, call data methods,
    make context copy, and defer actual template render via a generator.
    """
    # Import here to avoid circular import (component_render <-> component)
    from django_components.component import ComponentVars  # noqa: PLC0415
    from django_components.slots import normalize_slot_fills  # noqa: PLC0415

    ######################################
    # 1. Handle inputs
    ######################################

    # Allow to pass down Request object via context.
    # `context` may be passed explicitly via `Component.render()` and `Component.render_to_response()`,
    # or implicitly via `{% component %}` tag.
    if request is None and context:
        # If the context is `RequestContext`, it has `request` attribute
        request = getattr(context, "request", None)
        # Check if this is a nested component and whether parent has request
        if request is None:
            _, parent_comp_ctx = _get_parent_component_context(context)
            if parent_comp_ctx:
                parent_comp = parent_comp_ctx.component()
                request = parent_comp and parent_comp.request

    component_name = comp_cls._get_component_name(registered_name)

    # Allow to provide no args/kwargs/slots/context
    # NOTE: We make copies of args / kwargs / slots, so that plugins can modify them
    # without affecting the original values.
    args_list: list[Any] = list(default(args, []))
    kwargs_dict = to_dict(default(kwargs, {}))
    slots_dict = normalize_slot_fills(
        to_dict(default(slots, {})),
        component_name=component_name,
    )
    # Use RequestContext if request is provided, so that child non-component template tags
    # can access the request object too.
    context = context if context is not None else (RequestContext(request) if request else Context())

    # Allow to provide a dict instead of Context
    # NOTE: This if/else is important to avoid nested Contexts,
    # See https://github.com/django-components/django-components/issues/414
    if not isinstance(context, (Context, RequestContext)):
        context = RequestContext(request, context) if request else Context(context)

    # Throughout the component tree, we pass down the info about the components' parents.
    # This is used for correctly resolving slot fills, correct rendering order,
    # or CSS scoping.
    parent_id, parent_comp_ctx = _get_parent_component_context(context)
    if parent_comp_ctx is not None:
        component_path = [*parent_comp_ctx.component_path, component_name]
        component_tree_context = parent_comp_ctx.tree
    else:
        component_path = [component_name]
        component_tree_context = ComponentTreeContext(
            component_attrs={},
            on_component_intermediate_callbacks={},
            on_component_rendered_callbacks={},
            started_generators=WeakKeyDictionary(),
        )

    root_id = render_id if parent_comp_ctx is None else parent_comp_ctx.root_id

    # Set parent and root as direct attributes on the component instance.
    # This creates strong references that keep parent/root alive as long as children are alive.
    # NOTE: `parent_id` may be not found in `component_instance_cache` if we are rendering
    #       an orphaned slot function (AKA slot function that we've taken out of the render context)
    if parent_id is not None and parent_id in component_instance_cache:
        parent_component = component_instance_cache[parent_id]
    else:
        parent_component = None

    # NOTE: `root_id` may be not found in `component_instance_cache` if we are rendering
    #       an orphaned slot function (AKA slot function that we've taken out of the render context)
    if root_id is not None and root_id != render_id and root_id in component_instance_cache:
        root_component = component_instance_cache[root_id]
    else:
        root_component = None

    component = comp_cls(
        id=render_id,
        args=args_list,
        kwargs=kwargs_dict,
        slots=slots_dict,
        context=context,
        request=request,
        deps_strategy=deps_strategy,
        outer_context=outer_context,
        # TODO_v2 - Remove `registered_name` and `registry`
        registry=registry,
        registered_name=registered_name,
        node=node,
        parent=parent_component,
        root=root_component,
    )

    # Allow plugins to modify or validate the inputs
    result_override = extensions.on_component_input(
        OnComponentInputContext(
            component=component,
            component_cls=comp_cls,
            component_id=render_id,
            args=args_list,
            kwargs=kwargs_dict,
            slots=slots_dict,
            context=context,
        ),
    )

    # The component rendering was short-circuited by an extension, skipping
    # the rest of the rendering process. This may be for example a cached content.
    if result_override is not None:
        return result_override

    # If user doesn't specify `Args`, `Kwargs`, `Slots` types, then we pass them in as plain
    # dicts / lists.
    component.args = comp_cls.Args(*args_list) if comp_cls.Args is not None else args_list
    component.kwargs = comp_cls.Kwargs(**kwargs_dict) if comp_cls.Kwargs is not None else kwargs_dict
    component.slots = comp_cls.Slots(**slots_dict) if comp_cls.Slots is not None else slots_dict

    ######################################
    # 2. Prepare component state
    ######################################

    context_processors_data = component.context_processors_data

    # Required for compatibility with Django's {% extends %} tag
    # See https://github.com/django-components/django-components/pull/859
    context.render_context.push(  # type: ignore[union-attr]
        {BLOCK_CONTEXT_KEY: context.render_context.get(BLOCK_CONTEXT_KEY, BlockContext())},  # type: ignore[union-attr]
    )

    trace_component_msg(
        "COMP_PREP_START",
        component_name=component_name,
        component_id=render_id,
        slot_name=None,
        component_path=component_path,
        extra=(
            f"Received {len(args_list)} args, {len(kwargs_dict)} kwargs, {len(slots_dict)} slots,"
            f" Available slots: {slots_dict}"
        ),
    )

    # Register the component to provide
    register_provide_reference(context, component)

    # This is data that will be accessible (internally) from within the component's template.
    # NOTE: Be careful with the context - Do not store a strong reference to the component,
    #       because that would prevent the component from being garbage collected.
    # TODO: Test that ComponentContext and Component are garbage collected after render.
    component_ctx = ComponentContext(
        component=ref(component),
        component_path=component_path,
        # Template name is set only once we've resolved the component's Template instance.
        template_name=None,
        # This field will be modified from within `SlotNodes.render()`:
        # - The `default_slot` will be set to the first slot that has the `default` attribute set.
        # - If multiple slots have the `default` attribute set, yet have different name, then
        #   we will raise an error.
        default_slot=None,
        # NOTE: This is only a SNAPSHOT of the outer context.
        outer_context=snapshot_context(outer_context) if outer_context is not None else None,
        tree=component_tree_context,
        root_id=root_id,
    )

    # Instead of passing the ComponentContext directly through the Context, the entry on the Context
    # contains only a key to retrieve the ComponentContext from `component_context_cache`.
    #
    # This way, the flow is easier to debug. Because otherwise, if you tried to print out
    # or inspect the Context object, your screen would be filled with the deeply nested ComponentContext objects.
    # But now, the printed Context may simply look like this:
    # `[{ "True": True, "False": False, "None": None }, {"_DJC_COMPONENT_CTX": "c1A2b3c"}]`
    component_context_cache[render_id] = component_ctx

    ######################################
    # 3. Call data methods
    ######################################

    template_data, js_data, css_data = component._call_data_methods(args_list, kwargs_dict)

    extensions.on_component_data(
        OnComponentDataContext(
            component=component,
            component_cls=comp_cls,
            component_id=render_id,
            # TODO_V1 - Remove `context_data`
            context_data=template_data,
            template_data=template_data,
            js_data=js_data,
            css_data=css_data,
        ),
    )

    # Check if template_data doesn't conflict with context_processors_data
    # See https://github.com/django-components/django-components/issues/1482
    # NOTE: This is done after on_component_data so extensions can modify the data first.
    if context_processors_data:
        for key in template_data:
            if key in context_processors_data:
                raise ValueError(
                    f"Variable '{key}' defined in component '{component_name}' conflicts "
                    "with the same variable from context processors. Rename the variable in the component."
                )

    # Cache component's JS and CSS scripts, in case they have been evicted from the cache.
    cache_component_js(comp_cls, force=False)
    cache_component_css(comp_cls, force=False)

    # Create JS/CSS scripts that will load the JS/CSS variables into the page.
    js_input_hash = cache_component_js_vars(comp_cls, js_data) if js_data else None
    css_input_hash = cache_component_css_vars(comp_cls, css_data) if css_data else None

    #############################################################################
    # 4. Make Context copy
    #
    # NOTE: To support infinite recursion, we make a copy of the context.
    #       This way we don't have to call the whole component tree in one go recursively,
    #       but instead can render one component at a time.
    #############################################################################

    # TODO_v1 - Currently we have to pass `template_data` to `prepare_component_template()`,
    #     so that `get_template_string()`, `get_template_name()`, and `get_template()`
    #     have access to the data from `get_template_data()`.
    #
    #     Because of that there is one layer of `Context.update()` called inside `prepare_component_template()`.
    #
    #     Once `get_template_string()`, `get_template_name()`, and `get_template()` are removed,
    #     we can remove that layer of `Context.update()`, and NOT pass `template_data`
    #     to `prepare_component_template()`.
    #
    #     Then we can simply apply `template_data` to the context in the same layer
    #     where we apply `context_processor_data` and `component_vars`.
    with prepare_component_template(component, template_data) as template:
        # Set `_DJC_COMPONENT_IS_NESTED` based on whether we're currently INSIDE
        # the `{% extends %}` tag.
        # Part of fix for https://github.com/django-components/django-components/issues/508
        # See django_monkeypatch.py
        if template is not None:
            comp_is_nested = bool(context.render_context.get(BLOCK_CONTEXT_KEY))  # type: ignore[union-attr]
        else:
            comp_is_nested = False

        # Capture the template name so we can print better error messages (currently used in slots)
        component_ctx.template_name = template.name if template else None

        with context.update(  # type: ignore[union-attr]
            {
                # Make data from context processors available inside templates
                **context_processors_data,
                # Private context fields
                _COMPONENT_CONTEXT_KEY: render_id,
                COMPONENT_IS_NESTED_KEY: comp_is_nested,
                # NOTE: Public API for variables accessible from within a component's template
                # See https://github.com/django-components/django-components/issues/280#issuecomment-2081180940
                # TODO_V1 - Replace this with Component instance, removing the need for ComponentVars
                "component_vars": ComponentVars(
                    args=component.args,
                    kwargs=component.kwargs,
                    slots=component.slots,
                    # TODO_v1 - Remove this, superseded by `component_vars.slots`
                    #
                    # For users, we expose boolean variables that they may check
                    # to see if given slot was filled, e.g.:
                    # `{% if variable > 8 and component_vars.is_filled.header %}`
                    is_filled=component.is_filled,
                ),
            },
        ):
            # Make a "snapshot" of the context as it was at the time of the render call.
            #
            # Previously, we recursively called `Template.render()` as this point, but due to recursion
            # this was limiting the number of nested components to only about 60 levels deep.
            #
            # Now, we make a flat copy, so that the context copy is static and doesn't change even if
            # we leave the `with context.update` blocks.
            #
            # This makes it possible to render nested components with a queue, avoiding recursion limits.
            context_snapshot = snapshot_context(context)

    # Cleanup
    context.render_context.pop()  # type: ignore[union-attr]

    trace_component_msg(
        "COMP_PREP_END",
        component_name=component_name,
        component_id=render_id,
        slot_name=None,
        component_path=component_path,
    )

    ######################################
    # 5. Render component
    #
    # NOTE: To support infinite recursion, we don't directly call `Template.render()`.
    #       Instead, we defer rendering of the component - we prepare a generator function
    #       that will be called when the rendering process reaches this component.
    ######################################

    trace_component_msg(
        "COMP_RENDER_START",
        component_name=component.name,
        component_id=component.id,
        slot_name=None,
        component_path=component_path,
    )

    component.on_render_before(context_snapshot, template)

    # Emit signal that the template is about to be rendered
    if template is not None:
        template_rendered.send(sender=template, template=template, context=context_snapshot)

    # Instead of rendering component at the time we come across the `{% component %}` tag
    # in the template, we defer rendering in order to scalably handle deeply nested components.
    #
    # See `make_renderer_generator()` for more details.
    renderer_generator = make_renderer_generator(
        component=component,
        template=template,
        context=context_snapshot,
    )

    # This callback is called with the value that was yielded from `Component.on_render()`.
    # It may be called multiple times for the same component, e.g. if `Component.on_render()`
    # contains multiple `yield` keywords.
    def on_component_intermediate(html_content: str | None) -> str | None:
        # HTML attributes passed from parent to current component.
        # NOTE: Is `None` for the root component.
        curr_comp_attrs = component_tree_context.component_attrs.get(render_id, None)

        if html_content:
            # Add necessary HTML attributes to work with JS and CSS variables
            html_content, child_components_attrs = set_component_attrs_for_js_and_css(
                html_content=html_content,
                component_id=render_id,
                css_input_hash=css_input_hash,
                root_attributes=curr_comp_attrs,
            )

            # Store the HTML attributes that will be passed from this component to its children's components
            component_tree_context.component_attrs.update(child_components_attrs)

        return html_content

    component_tree_context.on_component_intermediate_callbacks[render_id] = on_component_intermediate

    # `on_component_rendered` is triggered when a component is rendered.
    # The component's parent(s) may not be fully rendered yet.
    #
    # NOTE: Inside `on_component_rendered`, we access the component indirectly via `component_instance_cache`.
    # This is so that the function does not directly hold a strong reference to the component instance,
    # so that the component instance can be garbage collected.
    component_instance_cache[render_id] = component

    # NOTE: This is called only once for a single component instance.
    def on_component_rendered(
        html: str | None,
        error: Exception | None,
    ) -> OnComponentRenderedResult:
        # NOTE: We expect `on_component_rendered` to be called only once,
        #       so we can release the strong reference to the component instance.
        #       This way, the component instance will persist only if the user keeps a reference to it.
        component = component_instance_cache.pop(render_id, None)
        if component is None:
            raise RuntimeError("Component has been garbage collected")

        # Allow the user to either:
        # - Override/modify the rendered HTML by returning new value
        # - Raise an exception to discard the HTML and bubble up error
        # - Or don't return anything (or return `None`) to use the original HTML / error
        try:
            maybe_output = component.on_render_after(context_snapshot, template, html, error)
            if maybe_output is not None:
                html = maybe_output
                error = None
        except Exception as new_error:  # noqa: BLE001
            error = new_error
            html = None

        # Prepend an HTML comment to instruct how and what JS and CSS scripts are associated with it.
        # E.g. `<!-- _RENDERED table,123,a92ef298,bd002c3 -->`
        if html is not None:
            html = insert_component_dependencies_comment(
                html,
                component_cls=comp_cls,
                component_id=render_id,
                js_input_hash=js_input_hash,
                css_input_hash=css_input_hash,
            )

        # Allow extensions to either:
        # - Override/modify the rendered HTML by returning new value
        # - Raise an exception to discard the HTML and bubble up error
        # - Or don't return anything (or return `None`) to use the original HTML / error
        result = extensions.on_component_rendered(
            OnComponentRenderedContext(
                component=component,
                component_cls=comp_cls,
                component_id=render_id,
                result=html,
                error=error,
            ),
        )

        if result is not None:
            html, error = result

        trace_component_msg(
            "COMP_RENDER_END",
            component_name=component_name,
            component_id=render_id,
            slot_name=None,
            component_path=component_path,
        )

        return html, error

    component_tree_context.on_component_rendered_callbacks[render_id] = on_component_rendered

    # This is triggered after a full component tree was rendered, we resolve
    # all inserted HTML comments into <script> and <link> tags.
    def on_component_tree_rendered(html: str) -> str:
        html = _render_dependencies(html, deps_strategy)
        return html

    return component_post_render(
        renderer=renderer_generator,
        render_id=render_id,
        component_name=component_name,
        parent_render_id=parent_id,
        component_tree_context=component_tree_context,
        on_component_tree_rendered=on_component_tree_rendered,
    )

    # Convert `Component.on_render()` to a generator function.
    #
    # By encapsulating components' output as a generator, we can render components top-down,
    # starting from root component, and moving down.
    #
    # This allows us to pass HTML attributes from parent to children.
    # Because by the time we get to a child component, its parent was already rendered.
    #
    # This whole setup makes it possible for multiple components to resolve to the same HTML element.
    # E.g. if CompA renders CompB, and CompB renders a <div>, then the <div> element will have
    # IDs of both CompA and CompB.
    # ```html
    # <div djc-id-a1b3cf djc-id-f3d3cf>...</div>
    # ```


def make_renderer_generator(
    component: "Component",
    template: Template | None,
    context: Context,
) -> OnRenderGenerator | None:
    """
    Convert Component.on_render() to a generator function so rendering can be
    deferred and done top-down without recursion limits.
    """

    # Convert the component's HTML to a generator function.
    #
    # To access the *final* output (with all its children rendered) from within `Component.on_render()`,
    # users may convert it to a generator by including a `yield` keyword. If they do so, the part of code
    # AFTER the yield will be called once when the component's HTML is fully rendered.
    #
    # ```
    # class MyTable(Component):
    #     def on_render(self, context, template):
    #         html, error = yield lamba: template.render(context)
    #         return html + "<p>Hello</p>"
    # ```
    #
    # However, the way Python works is that when you call a function that contains `yield` keyword,
    # the function is NOT executed immediately. Instead it returns a generator object.
    #
    # On the other hand, if it's a regular function, the function is executed immediately.
    #
    # We must be careful not to execute the function immediately, because that will cause the
    # entire component tree to be rendered recursively. Instead we want to defer the execution
    # and render nested components via a flat stack, as done in `perfutils/component.py`.
    # That allows us to create component trees of any depth, without hitting recursion limits.
    #
    # So we create a wrapper generator function that we KNOW is a generator when called.
    def inner_generator() -> OnRenderGenerator:
        # NOTE: May raise
        html_content_or_generator = component.on_render(context, template)
        # If we DIDN'T raise an exception
        if html_content_or_generator is None:
            return None
        # Generator function (with `yield`) - yield multiple times with the result
        elif is_generator(html_content_or_generator):
            generator = cast("OnRenderGenerator", html_content_or_generator)
            result = yield from generator
            # If the generator had a return statement, `result` will contain that value.
            # So we pass the return value through.
            return result
        # String (or other unknown type) - yield once with the result
        else:
            yield html_content_or_generator
            return None

    return inner_generator()


def _get_parent_component_context(
    context: Context | Mapping,
) -> tuple[None, None] | tuple[str, ComponentContext]:
    parent_id = context.get(_COMPONENT_CONTEXT_KEY, None)
    if parent_id is None:
        return None, None

    # NOTE: This may happen when slots are rendered outside of the component's render context.
    # See https://github.com/django-components/django-components/issues/1189
    if parent_id not in component_context_cache:
        return None, None

    parent_comp_ctx = component_context_cache[parent_id]
    return parent_id, parent_comp_ctx


# ---------------------------------------------------------------------------
# Moved from perfutil/component.py (render-time caches and queue types)
# ---------------------------------------------------------------------------

# When we're inside a component's template, we need to acccess some component data,
# as defined by `ComponentContext`. If we have nested components, then
# each nested component will point to the Context of its parent component
# via `outer_context`. This make is possible to access the correct data
# inside `{% fill %}` tags.
#
# Previously, `ComponentContext` was stored directly on the `Context` object, but
# this was problematic:
# - The need for creating a Context snapshot meant potentially a lot of copying
# - It was hard to trace and debug. Because if you printed the Context, it included the
#   `ComponentContext` data, including the `outer_context` which contained another
#   `ComponentContext` object, and so on.
#
# Thus, similarly to the data stored by `{% provide %}`, we store the actual
# `ComponentContext` data on a separate dictionary, and what's passed through the Context
# is only a key to this dictionary.
component_context_cache: dict[str, "ComponentContext"] = {}

# ComponentID -> Component instance mapping
# This is used so that we can access the component instance from inside `on_component_rendered()`,
# to call `Component.on_render_after()`.
# These are strong references to ensure that the Component instance stays alive until after
# `on_component_rendered()` has been called.
# After that, we release the reference. If user does not keep a reference to the component,
# it will be garbage collected.
component_instance_cache: dict[str, "Component"] = {}


class QueueItemId(NamedTuple):
    """
    Identifies which queue items we should ignore when we come across them
    (due to a component having raised an error).
    """

    component_id: str
    # NOTE: Versions are used so we can `yield` multiple times from `Component.on_render()`.
    # Each time a value is yielded (or returned by `return`), we discard the previous HTML
    # by incrementing the version and tagging the old version to be ignored.
    version: int


class ComponentPart(NamedTuple):
    """Queue item where a component is nested in another component."""

    item_id: QueueItemId
    parent_id: QueueItemId | None
    full_path: list[str]
    """Path of component names from the root component to the current component."""

    def __repr__(self) -> str:
        return f"ComponentPart(item_id={self.item_id!r}, parent_id={self.parent_id!r}, full_path={self.full_path!r})"


class TextPart(NamedTuple):
    """Queue item where a text is between two components."""

    item_id: QueueItemId
    text: str
    is_last: bool


class ErrorPart(NamedTuple):
    """Queue item where a component has thrown an error."""

    item_id: QueueItemId
    error: Exception
    full_path: list[str]


class GeneratorResult(NamedTuple):
    html: str | None
    error: Exception | None
    action: Literal["needs_processing", "rerender", "stop"]
    spent: bool
    """Whether the generator has been "spent" - e.g. reached its end with `StopIteration`."""


# Render-time cache for component rendering
# See component_post_render()
component_renderer_cache: "dict[str, tuple[OnRenderGenerator | None, str]]" = {}

nested_comp_pattern = re.compile(
    r'<template [^>]*?djc-render-id="\w{{{COMP_ID_LENGTH}}}"[^>]*?></template>'.format(COMP_ID_LENGTH=COMP_ID_LENGTH),  # noqa: UP032
)
render_id_pattern = re.compile(
    r'djc-render-id="(?P<render_id>\w{{{COMP_ID_LENGTH}}})"'.format(COMP_ID_LENGTH=COMP_ID_LENGTH),  # noqa: UP032
)


# When a component is rendered, we want to apply HTML attributes like `data-djc-id-ca1b3cf`
# to all root elements. However, we have to approach it smartly, to minimize the HTML parsing.
#
# If we naively first rendered the child components, and then the parent component, then we would
# have to parse the child's HTML twice (once for itself, and once as part of the parent).
# When we have a deeply nested component structure, this can add up to a lot of parsing.
# See https://github.com/django-components/django-components/issues/14#issuecomment-2596096632.
#
# Imagine we first render the child components. Once rendered, child's HTML gets embedded into
# the HTML of the parent. So by the time we get to the root, we will have to parse the full HTML
# document, even if the root component is only a small part of the document.
#
# So instead, when a nested component is rendered, we put there only a placeholder, and store the
# actual HTML content in `component_renderer_cache`.
#
# ```django
# <div>
#   <h2>...</h2>
#   <template djc-render-id="a1b3cf"></template>
#   <span>...</span>
#   <template djc-render-id="f3d3cf"></template>
# </div>
# ```
#
# The full flow is as follows:
# 1. When a component is nested in another, the child component is rendered, but it returns
#    only a placeholder like `<template djc-render-id="a1b3cf"></template>`.
#    The actual HTML output is stored in `component_renderer_cache`.
# 2. The parent of the child component is rendered normally.
# 3. If the placeholder for the child component is at root of the parent component,
#    then the placeholder may be tagged with extra attributes, e.g. `data-djc-id-ca1b3cf`.
#    `<template djc-render-id="a1b3cf" data-djc-id-ca1b3cf></template>`.
# 4. When the parent is done rendering, we go back to step 1., the parent component
#    either returns the actual HTML, or a placeholder.
# 5. Only once we get to the root component, that has no further parents, is when we finally
#    start putting it all together.
# 6. We start at the root component. We search the root component's output HTML for placeholders.
#    Each placeholder has ID `data-djc-render-id` that links to its actual content.
# 7. For each found placeholder, we replace it with the actual content.
#    But as part of step 7), we also:
#    - If any of the child placeholders had extra attributes, we cache these, so we can access them
#      once we get to rendering the child component.
#    - And if the parent component had any extra attributes set by its parent, we apply these
#      to the root elements.
# 8. Lastly, we merge all the parts together, and return the final HTML.
def component_post_render(
    renderer: "OnRenderGenerator | None",
    render_id: str,
    component_name: str,
    parent_render_id: str | None,
    component_tree_context: "ComponentTreeContext",
    on_component_tree_rendered: Callable[[str], str],
) -> str:
    # Instead of rendering the component's HTML content immediately, we store it,
    # so we can render the component only once we know if there are any HTML attributes
    # to be applied to the resulting HTML.
    component_renderer_cache[render_id] = (renderer, component_name)

    # Case: Nested component
    # If component is nested, return a placeholder
    #
    # How this works is that we have nested components:
    # ```
    # ComponentA
    #   ComponentB
    #     ComponentC
    # ```
    #
    # And these components are embedded one in another using the `{% component %}` tag.
    # ```django
    # <!-- ComponentA -->
    # <div>
    #   {% component "ComponentB" / %}
    # </div>
    # ```
    #
    # Then the order in which components call `component_post_render()` is:
    # 1. ComponentB - Triggered by `{% component "ComponentB" / %}` while A's template is being rendered,
    #                 returns only a placeholder.
    # 2. ComponentA - Triggered by the end of A's template. A isn't nested, so it starts full component
    #                 tree render. This replaces B's placeholder with actual HTML and introduces C's placeholder.
    #                 And so on...
    # 3. ComponentC - Triggered by `{% component "ComponentC" / %}` while B's template is being rendered
    #                 as part of full component tree render. Returns only a placeholder, to be replaced in next
    #                 step.
    if parent_render_id is not None:
        return mark_safe(f'<template djc-render-id="{render_id}"></template>')

    # Case: Root component - Construct the final HTML by recursively replacing placeholders
    #
    # We first generate the component's HTML content, by calling the renderer.
    #
    # Then we process the component's HTML from root-downwards, going depth-first.
    # So if we have a template:
    # ```django
    # <div>
    #   <h2>...</h2>
    #   {% component "ComponentB" / %}
    #   <span>...</span>
    #   {% component "ComponentD" / %}
    # </div>
    # ```
    #
    # Then component's template is rendered, replacing nested components with placeholders:
    # ```html
    # <div>
    #   <h2>...</h2>
    #   <template djc-render-id="a1b3cf"></template>
    #   <span>...</span>
    #   <template djc-render-id="f3d3d0"></template>
    # </div>
    # ```
    #
    # Then we first split up the current HTML into parts, splitting at placeholders:
    # - <div><h2>...</h2>
    # - PLACEHOLDER djc-render-id="a1b3cf"
    # - <span>...</span>
    # - PLACEHOLDER djc-render-id="f3d3d0"
    # - </div>
    #
    # And put these into a queue:
    # ```py
    # [
    #     TextPart("<div><h2>...</h2>"),
    #     ComponentPart("a1b3cf"),
    #     TextPart("<span>...</span>"),
    #     ComponentPart("f3d3d0"),
    #     TextPart("</div>"),
    # ]
    # ```
    #
    # Then we process each part:
    # 1. If TextPart, we append the content to the output
    # 2. If ComponentPart, then we fetch the renderer by its placeholder ID (e.g. "a1b3cf")
    # 3. If there were any extra attributes set by the parent component, we apply these to the renderer.
    # 4. We get back the rendered HTML for given component instance, with any extra attributes applied.
    # 5. We split/parse this content by placeholders, resulting in more `TextPart` and `ComponentPart` items.
    # 6. We insert these parts back into the queue, repeating this process until we've processed all nested components.
    # 7. When we reach TextPart with `is_last=True`, then we've reached the end of the component's HTML content,
    #    and we can go one level up to continue the process with component's parent.
    process_queue: deque[ErrorPart | TextPart | ComponentPart] = deque()

    # `html_parts_by_component_id` holds component-specific bits of rendered HTML
    # so that we can call `on_component_rendered` hook with the correct component instance.
    #
    # We then use `content_parts` to collect the final HTML for the component.
    #
    # Example - if component has a template like this:
    #
    # ```django
    # <div>
    #   Hello
    #   {% component "table" / %}
    # </div>
    # ```
    #
    # Then we end up with 3 bits - 1. text before, 2. component, and 3. text after
    #
    # We know when we've arrived at component's end. We then collect the HTML parts by the component ID,
    # and we join all the bits that belong to the same component.
    #
    # Once the component's HTML is joined, we then pass that to the callback for
    # the corresponding component ID.
    #
    # Lastly we assign the child's final HTML to parent's parts, continuing the cycle.
    html_parts_by_component_id: dict[str, list[str]] = {}
    content_parts: list[str] = []

    # Remember which component instance + version had which parent, so we can bubble up errors
    # to the parent component.
    child_to_parent: dict[QueueItemId, QueueItemId | None] = {}

    # We want to avoid having to iterate over the queue every time an error raises an error or
    # when `on_render()` returns a new HTML, making the old HTML stale.
    #
    # So instead we keep track of which combinations of component ID + versions we should skip.
    #
    # When we then come across these instances in the main loop, we skip them.
    ignored_components: set[QueueItemId] = set()

    # When `Component.on_render()` contains a `yield` statement, it becomes a generator.
    #
    # The generator may `yield` multiple times. So we keep track of which generator belongs to
    # which component ID.
    generators_by_component_id: dict[str, OnRenderGenerator | None] = {}

    def get_html_parts(item_id: QueueItemId) -> list[str]:
        component_id = item_id.component_id
        if component_id not in html_parts_by_component_id:
            html_parts_by_component_id[component_id] = []
        return html_parts_by_component_id[component_id]

    def pop_html_parts(item_id: QueueItemId) -> list[str] | None:
        component_id = item_id.component_id
        return html_parts_by_component_id.pop(component_id, None)

    # Split component's rendered HTML by placeholders, from:
    #
    # ```html
    # <div>
    #   <h2>...</h2>
    #   <template djc-render-id="a1b3cf"></template>
    #   <span>...</span>
    #   <template djc-render-id="f3d3d0"></template>
    # </div>
    # ```
    #
    # To:
    #
    # ```py
    # [
    #     TextPart("<div><h2>...</h2>"),
    #     ComponentPart("a1b3cf"),
    #     TextPart("<span>...</span>"),
    #     ComponentPart("f3d3d0"),
    #     TextPart("</div>"),
    # ]
    # ```
    def parse_component_result(
        content: str,
        item_id: QueueItemId,
        full_path: list[str],
    ) -> list[TextPart | ComponentPart]:
        last_index = 0
        parts_to_process: list[TextPart | ComponentPart] = []
        for match in nested_comp_pattern.finditer(content):
            part_before_component = content[last_index : match.start()]
            last_index = match.end()
            comp_part = match[0]

            # Extract the placeholder ID from `<template djc-render-id="a1b3cf"></template>`
            child_id_match = render_id_pattern.search(comp_part)
            if child_id_match is None:
                raise ValueError(f"No placeholder ID found in {comp_part}")
            child_id = child_id_match.group("render_id")

            parts_to_process.extend(
                [
                    TextPart(
                        item_id=item_id,
                        text=part_before_component,
                        is_last=False,
                    ),
                    ComponentPart(
                        # NOTE: Since this is the first that that this component will be rendered,
                        # the version is 0.
                        item_id=QueueItemId(component_id=child_id, version=0),
                        parent_id=item_id,
                        full_path=full_path,
                    ),
                ],
            )

        # Append any remaining text
        parts_to_process.extend(
            [
                TextPart(
                    item_id=item_id,
                    text=content[last_index:],
                    is_last=True,
                ),
            ],
        )

        return parts_to_process

    def handle_error(item_id: QueueItemId, error: Exception, full_path: list[str]) -> None:
        # Cleanup
        # Remove any HTML parts that were already rendered for this component
        pop_html_parts(item_id)

        # Mark any remaining parts of this component version (that may be still in the queue) as errored
        ignored_components.add(item_id)

        # Also mark as ignored any remaining parts of this version of the PARENT component.
        # The reason is because due to the error, parent's rendering flow was disrupted.
        # Parent may recover from the error by returning a new HTML. But in that case
        # we will be processing that *new* HTML (by setting new version), and NOT this broken version.
        parent_id = child_to_parent[item_id]
        if parent_id is not None:
            ignored_components.add(parent_id)

        # Add error item to the queue so we handle it in next iteration
        process_queue.appendleft(
            ErrorPart(
                item_id=item_id,
                error=error,
                full_path=full_path,
            ),
        )

    def next_renderer_result(item_id: QueueItemId, error: Exception | None, full_path: list[str]) -> None:
        parent_id = child_to_parent[item_id]

        component_parts = pop_html_parts(item_id)
        if error is None and component_parts:
            component_html = "".join(component_parts) if component_parts else ""
        else:
            component_html = None

        # If we've got error, and the component has defined `on_render()` as a generator
        # (with `yield`), then pass the result to the generator, and process the result.
        #
        # NOTE: We want to call the generator (`Component.on_render()`) BEFORE
        # we call `Component.on_render_after()`. The latter will be called only once
        # `Component.on_render()` has no more `yield` statements, so that `on_render_after()`
        # (and `on_component_rendered` extension hook) are called at the very end of component rendering.
        on_render_generator = generators_by_component_id.pop(item_id.component_id, None)
        if on_render_generator is not None:
            result = _call_generator(
                on_render_generator=on_render_generator,
                html=component_html,
                error=error,
                started_generators_cache=component_tree_context.started_generators,
                full_path=full_path,
            )
            new_html = result.html

            # Component's `on_render()` contains multiple `yield` keywords, so keep the generator.
            if not result.spent:
                generators_by_component_id[item_id.component_id] = on_render_generator

            # The generator yielded or returned a new HTML. We want to process it as if
            # it's a new component's HTML.
            if result.action == "needs_processing":
                # Ignore the old version of the component
                ignored_components.add(item_id)

                new_version = item_id.version + 1
                new_item_id = QueueItemId(component_id=item_id.component_id, version=new_version)

                # Set the current parent as the parent of the new version
                child_to_parent[new_item_id] = parent_id

                # Allow to optionally override/modify the intermediate result returned from `Component.on_render()`
                # and by extensions' `on_component_intermediate` hooks.
                on_component_intermediate = component_tree_context.on_component_intermediate_callbacks[
                    item_id.component_id
                ]
                # NOTE: [1:] because the root component will be yet again added to the error's
                # `components` list in `render_with_error_trace` so we remove the first element from the path.
                with with_component_error_message(full_path[1:]):
                    new_html = on_component_intermediate(new_html)

                # Split the new HTML by placeholders, and put the parts into the queue.
                parts_to_process = parse_component_result(new_html or "", new_item_id, full_path)
                process_queue.extendleft(reversed(parts_to_process))
                return
            elif result.action == "rerender":
                # Ignore the old version of the component
                ignored_components.add(item_id)

                new_version = item_id.version + 1
                new_item_id = QueueItemId(component_id=item_id.component_id, version=new_version)
                # Set the current parent as the parent of the new version
                child_to_parent[new_item_id] = parent_id

                next_renderer_result(item_id=new_item_id, error=result.error, full_path=full_path)
                return
            else:
                # If we don't need to re-do the processing, then we can just use the result.
                component_html, error = new_html, result.error

        # Allow to optionally override/modify the rendered content from `Component.on_render_after()`
        # and by extensions' `on_component_rendered` hooks.
        on_component_rendered = component_tree_context.on_component_rendered_callbacks[item_id.component_id]
        with with_component_error_message(full_path[1:]):
            component_html, error = on_component_rendered(component_html, error)

        # If this component had an error, then we ignore this component's HTML, and instead
        # bubble the error up to the parent component.
        if error is not None:
            handle_error(item_id=item_id, error=error, full_path=full_path)
            return

        if component_html is None:
            return

        # At this point we have a component, and we've resolved all its children into strings.
        # So the component's full HTML is now only strings.
        #
        # Hence we can transfer the child component's HTML to parent, treating it as if
        # the parent component had the rendered HTML in child's place.
        if parent_id is not None:
            target_list = get_html_parts(parent_id)
            target_list.append(component_html)
        # If there is no parent, then we're at the root component, and we can add the
        # component's HTML to the final output.
        else:
            content_parts.append(component_html)

    # Body of the iteration, scoped in a function to avoid spilling the state out of the loop.
    def on_item(curr_item: ErrorPart | TextPart | ComponentPart) -> None:
        # NOTE: When an error is bubbling up, when the flow goes between `handle_error()`, `next_renderer_result()`,
        # and this branch, until we reach the root component, where the error is finally raised.
        #
        # Any ancestor component of the one that raised can intercept the error and instead return a new string
        # (or a new error).
        if isinstance(curr_item, ErrorPart):
            parent_id = child_to_parent[curr_item.item_id]

            # If there is no parent, then we're at the root component, so we simply propagate the error.
            # This ends the error bubbling.
            if parent_id is None:
                raise curr_item.error from None  # Re-raise

            # This will make the parent component either handle the error and return a new string instead,
            # or propagate the error to its parent.
            next_renderer_result(item_id=parent_id, error=curr_item.error, full_path=curr_item.full_path)
            return

        # Skip parts that belong to component versions that error'd
        if curr_item.item_id in ignored_components:
            return

        # Process text parts
        if isinstance(curr_item, TextPart):
            curr_html_parts = get_html_parts(curr_item.item_id)
            curr_html_parts.append(curr_item.text)

            # In this case we've reached the end of the component's HTML content, and there's
            # no more subcomponents to process. We can call `next_renderer_result()` to process
            # the component's HTML and eventually trigger `on_component_rendered` hook.
            if curr_item.is_last:
                next_renderer_result(item_id=curr_item.item_id, error=None, full_path=[])

            return

        if isinstance(curr_item, ComponentPart):
            component_id = curr_item.item_id.component_id

            # Remember which component ID had which parent ID, so we can bubble up errors
            # to the parent component.
            child_to_parent[curr_item.item_id] = curr_item.parent_id

            on_render_generator, curr_comp_name = component_renderer_cache.pop(component_id)
            full_path = [*curr_item.full_path, curr_comp_name]
            generators_by_component_id[component_id] = on_render_generator

            # This is where we actually render the component
            next_renderer_result(item_id=curr_item.item_id, error=None, full_path=full_path)

        else:
            raise TypeError("Unknown item type")

    # Kick off the process by adding the root component to the queue
    process_queue.append(
        ComponentPart(
            item_id=QueueItemId(component_id=render_id, version=0),
            parent_id=None,
            full_path=[],
        ),
    )

    while len(process_queue):
        curr_item = process_queue.popleft()
        on_item(curr_item)

    # Lastly, join up all pieces of the component's HTML content
    output = "".join(content_parts)

    # Allow to optionally modify the final output
    output = on_component_tree_rendered(output)

    return mark_safe(output)


def _call_generator(
    on_render_generator: "OnRenderGenerator",
    html: str | None,
    error: Exception | None,
    started_generators_cache: "StartedGenerators",
    full_path: list[str],
) -> GeneratorResult:
    is_first_send = not started_generators_cache.get(on_render_generator, False)
    try:
        # `Component.on_render()` may have any number of `yield` statements, so we need to
        # call `.send()` any number of times.
        #
        # To override what HTML / error gets returned, user may either:
        # - Return a new HTML with `return` - We handle error / result ourselves
        # - Yield a new HTML with `yield` - We return back to the user the processed HTML / error
        #                                   for them to process further
        # - Raise a new error
        if is_first_send:
            new_result = on_render_generator.send(None)  # type: ignore[arg-type]
        else:
            new_result = on_render_generator.send((html, error))

    # If we've reached the end of `Component.on_render()` (or `return` statement), then we get `StopIteration`.
    # In that case, we want to check if user returned new HTML from the `return` statement.
    except StopIteration as generator_err:
        # The return value is on `StopIteration.value`
        new_output = generator_err.value
        if new_output is not None:
            return GeneratorResult(html=new_output, error=None, action="needs_processing", spent=True)
        # Nothing returned at the end of the generator, keep the original HTML and error
        return GeneratorResult(html=html, error=error, action="stop", spent=True)

    # Catch if `Component.on_render()` raises an exception, in which case this becomes
    # the new error.
    except Exception as new_error:  # noqa: BLE001
        set_component_error_message(new_error, full_path[1:])
        return GeneratorResult(html=None, error=new_error, action="stop", spent=True)

    # If the generator didn't raise an error then `Component.on_render()` yielded a new HTML result,
    # that we need to process.
    else:
        # NOTE: Users may yield a function from `on_render()` instead of rendered template:
        # ```py
        # class MyTable(Component):
        #     def on_render(self, context, template):
        #         html, error = yield lambda: template.render(context)
        #         return html + "<p>Hello</p>"
        # ```
        # This is so that we can keep the API simple, handling the errors in template rendering.
        # Otherwise, people would have to write out:
        # ```py
        # try:
        #     intermediate = template.render(context)
        # except Exception as err:
        #     result = None
        #     error = err
        # else:
        #     result, error = yield intermediate
        # ```
        if callable(new_result):
            try:
                new_result = new_result()
            except Exception as new_err:  # noqa: BLE001
                started_generators_cache[on_render_generator] = True
                set_component_error_message(new_err, full_path[1:])
                # In other cases, when a component raises an error during rendering,
                # we discard the errored component and move up to the parent component
                # to decide what to do (propagate or return a new HTML).
                #
                # But if user yielded a function from `Component.on_render()`,
                # we want to let the CURRENT component decide what to do.
                # Hence why the action is "rerender" instead of "stop".
                return GeneratorResult(html=None, error=new_err, action="rerender", spent=False)

        if is_first_send or new_result is not None:
            started_generators_cache[on_render_generator] = True
            return GeneratorResult(html=new_result, error=None, action="needs_processing", spent=False)

        # Generator yielded `None`, keep the previous HTML and error
        return GeneratorResult(html=html, error=error, action="stop", spent=False)
