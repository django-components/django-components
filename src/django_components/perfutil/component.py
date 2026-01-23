import re
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, NamedTuple, TypeAlias

from django.utils.safestring import mark_safe

from django_components.constants import COMP_ID_LENGTH
from django_components.util.exception import component_error_message, set_component_error_message

if TYPE_CHECKING:
    from django_components.component import (
        Component,
        ComponentContext,
        ComponentTreeContext,
        OnRenderGenerator,
        StartedGenerators,
    )

OnComponentRenderedResult: TypeAlias = tuple[str | None, Exception | None]

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
                # `components` list in `_render_with_error_trace` so we remove the first element from the path.
                with component_error_message(full_path[1:]):
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
        with component_error_message(full_path[1:]):
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
