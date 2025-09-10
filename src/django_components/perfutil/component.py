import re
from collections import deque
from typing import TYPE_CHECKING, Callable, Deque, Dict, List, NamedTuple, Optional, Set, Tuple, Union

from django.utils.safestring import mark_safe

from django_components.constants import COMP_ID_LENGTH
from django_components.util.exception import component_error_message

if TYPE_CHECKING:
    from django_components.component import ComponentContext, OnRenderGenerator

OnComponentRenderedResult = Tuple[Optional[str], Optional[Exception]]

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
component_context_cache: Dict[str, "ComponentContext"] = {}


class ComponentPart(NamedTuple):
    """Queue item where a component is nested in another component."""

    child_id: str
    parent_id: Optional[str]
    component_name_path: List[str]

    def __repr__(self) -> str:
        return (
            f"ComponentPart(child_id={self.child_id!r}, parent_id={self.parent_id!r}, "
            f"component_name_path={self.component_name_path!r})"
        )


class TextPart(NamedTuple):
    """Queue item where a text is between two components."""

    text: str
    is_last: bool
    parent_id: str


class ErrorPart(NamedTuple):
    """Queue item where a component has thrown an error."""

    child_id: str
    error: Exception


# Function that accepts a list of extra HTML attributes to be set on the component's root elements
# and returns the component's HTML content and a dictionary of child components' IDs
# and their root elements' HTML attributes.
#
# In other words, we use this to "delay" the actual rendering of the component's HTML content,
# until we know what HTML attributes to apply to the root elements.
ComponentRenderer = Callable[
    [Optional[List[str]]],
    Tuple[str, Dict[str, List[str]], Optional["OnRenderGenerator"]],
]

# Render-time cache for component rendering
# See component_post_render()
component_renderer_cache: Dict[str, Tuple[ComponentRenderer, str]] = {}
child_component_attrs: Dict[str, List[str]] = {}

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
    renderer: ComponentRenderer,
    render_id: str,
    component_name: str,
    parent_id: Optional[str],
    on_component_rendered_callbacks: Dict[
        str,
        Callable[[Optional[str], Optional[Exception]], OnComponentRenderedResult],
    ],
    on_html_rendered: Callable[[str], str],
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
    if parent_id is not None:
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
    #   <template djc-render-id="f3d3cf"></template>
    # </div>
    # ```
    #
    # Then we first split up the current HTML into parts, splitting at placeholders:
    # - <div><h2>...</h2>
    # - PLACEHOLDER djc-render-id="a1b3cf"
    # - <span>...</span>
    # - PLACEHOLDER djc-render-id="f3d3cf"
    # - </div>
    #
    # And put the pairs of (content, placeholder_id) into a queue:
    # - ("<div><h2>...</h2>", "a1b3cf")
    # - ("<span>...</span>", "f3d3cf")
    # - ("</div>", None)
    #
    # Then we process each part:
    # 1. Append the content to the output
    # 2. If the placeholder ID is not None, then we fetch the renderer by its placeholder ID (e.g. "a1b3cf")
    # 3. If there were any extra attributes set by the parent component, we apply these to the renderer.
    # 4. We split the content by placeholders, and put the pairs of (content, placeholder_id) into the queue,
    #    repeating this whole process until we've processed all nested components.
    # 5. If the placeholder ID is None, then we've reached the end of the component's HTML content,
    #    and we can go one level up to continue the process with component's parent.
    process_queue: Deque[Union[ErrorPart, TextPart, ComponentPart]] = deque()

    process_queue.append(
        ComponentPart(
            child_id=render_id,
            parent_id=None,
            component_name_path=[],
        )
    )

    # By looping over the queue below, we obtain bits of rendered HTML, which we then
    # must all join together into a single final HTML.
    #
    # But instead of joining it all up once at the end, we join the bits on component basis.
    # So if component has a template like this:
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
    # and when we hit the end, we join all the bits that belong to the same component.
    #
    # Once the component's HTML is joined, we can call the callback for the component, and
    # then add the joined HTML to the cache for the parent component to continue the cycle.
    html_parts_by_component_id: Dict[str, List[str]] = {}
    content_parts: List[str] = []

    # Remember which component ID had which parent ID, so we can bubble up errors
    # to the parent component.
    child_id_to_parent_id: Dict[str, Optional[str]] = {}

    def get_html_parts(component_id: str) -> List[str]:
        if component_id not in html_parts_by_component_id:
            html_parts_by_component_id[component_id] = []
        return html_parts_by_component_id[component_id]

    def handle_error(component_id: str, error: Exception) -> None:
        # Cleanup
        # Remove any HTML parts that were already rendered for this component
        html_parts_by_component_id.pop(component_id, None)
        # Mark any remaining parts of this component (that may be still in the queue) as errored
        ignored_ids.add(component_id)
        # Also mark as ignored any remaining parts of the PARENT component.
        # The reason is because due to the error, parent's rendering flow was disrupted.
        # Even if parent recovers from the error by returning a new HTML, this new HTML
        # may have nothing in common with the original HTML.
        parent_id = child_id_to_parent_id[component_id]
        if parent_id is not None:
            ignored_ids.add(parent_id)

        # Add error item to the queue so we handle it in next iteration
        process_queue.appendleft(
            ErrorPart(
                child_id=component_id,
                error=error,
            )
        )

    def finalize_component(component_id: str, error: Optional[Exception]) -> None:
        parent_id = child_id_to_parent_id[component_id]

        component_parts = html_parts_by_component_id.pop(component_id, [])
        if error is None:
            component_html = "".join(component_parts)
        else:
            component_html = None

        # Allow to optionally override/modify the rendered content from `Component.on_render()`
        # and by extensions' `on_component_rendered` hooks.
        on_component_rendered = on_component_rendered_callbacks[component_id]
        component_html, error = on_component_rendered(component_html, error)

        # If this component had an error, then we ignore this component's HTML, and instead
        # bubble the error up to the parent component.
        if error is not None:
            handle_error(component_id=component_id, error=error)
            return

        if component_html is None:
            raise RuntimeError("Unexpected `None` from `Component.on_render()`")

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

    # To avoid having to iterate over the queue multiple times to remove from it those
    # entries that belong to components that have thrown error, we instead keep track of which
    # components have thrown error, and skip any remaining parts of the component.
    ignored_ids: Set[str] = set()

    while len(process_queue):
        curr_item = process_queue.popleft()

        # NOTE: When an error is bubbling up, then the flow goes between `handle_error()`, `finalize_component()`,
        # and this branch, until we reach the root component, where the error is finally raised.
        #
        # Any ancestor component of the one that raised can intercept the error and instead return a new string
        # (or a new error).
        if isinstance(curr_item, ErrorPart):
            parent_id = child_id_to_parent_id[curr_item.child_id]

            # If there is no parent, then we're at the root component, so we simply propagate the error.
            # This ends the error bubbling.
            if parent_id is None:
                raise curr_item.error from None  # Re-raise

            # This will make the parent component either handle the error and return a new string instead,
            # or propagate the error to its parent.
            finalize_component(component_id=parent_id, error=curr_item.error)
            continue

        # Skip parts of errored components
        if curr_item.parent_id in ignored_ids:
            continue

        # Process text parts
        if isinstance(curr_item, TextPart):
            parent_html_parts = get_html_parts(curr_item.parent_id)
            parent_html_parts.append(curr_item.text)

            # In this case we've reached the end of the component's HTML content, and there's
            # no more subcomponents to process. We can call `finalize_component()` to process
            # the component's HTML and eventually trigger `on_component_rendered` hook.
            if curr_item.is_last:
                finalize_component(component_id=curr_item.parent_id, error=None)

            continue

        # The rest of this branch assumes `curr_item` is a `ComponentPart`
        component_id = curr_item.child_id

        # Remember which component ID had which parent ID, so we can bubble up errors
        # to the parent component.
        child_id_to_parent_id[component_id] = curr_item.parent_id

        # Generate component's content, applying the extra HTML attributes set by the parent component
        curr_comp_renderer, curr_comp_name = component_renderer_cache.pop(component_id)
        # NOTE: Attributes passed from parent to current component are `None` for the root component.
        curr_comp_attrs = child_component_attrs.pop(component_id, None)

        full_path = [*curr_item.component_name_path, curr_comp_name]

        # This is where we actually render the component
        #
        # NOTE: [1:] because the root component will be yet again added to the error's
        # `components` list in `_render_with_error_trace` so we remove the first element from the path.
        try:
            with component_error_message(full_path[1:]):
                comp_content, grandchild_component_attrs, on_render_generator = curr_comp_renderer(curr_comp_attrs)
        # This error may be triggered when any of following raises:
        # - `Component.on_render()` (first part - before yielding)
        # - `Component.on_render_before()`
        # - Rendering of component's template
        #
        # In all cases, we want to mark the component as errored, and let the parent handle it.
        except Exception as err:  # noqa: BLE001
            handle_error(component_id=component_id, error=err)
            continue

        # To access the *final* output (with all its children rendered) from within `Component.on_render()`,
        # users may convert it to a generator by including a `yield` keyword. If they do so, the part of code
        # AFTER the yield will be called once, when the component's HTML is fully rendered.
        #
        # We want to make sure we call the second part of `Component.on_render()` BEFORE
        # we call `Component.on_render_after()`. The latter will be triggered by calling
        # corresponding `on_component_rendered`.
        #
        # So we want to wrap the `on_component_rendered` callback, so we get to call the generator first.
        if on_render_generator is not None:
            unwrapped_on_component_rendered = on_component_rendered_callbacks[component_id]
            on_component_rendered_callbacks[component_id] = _call_generator_before_callback(
                on_render_generator,
                unwrapped_on_component_rendered,
            )

        child_component_attrs.update(grandchild_component_attrs)

        # Split component's content by placeholders, and put the pairs of
        # `(text_between_components, placeholder_id)`
        # into the queue.
        last_index = 0
        parts_to_process: List[Union[TextPart, ComponentPart]] = []
        for match in nested_comp_pattern.finditer(comp_content):
            part_before_component = comp_content[last_index : match.start()]
            last_index = match.end()
            comp_part = match[0]

            # Extract the placeholder ID from `<template djc-render-id="a1b3cf"></template>`
            grandchild_id_match = render_id_pattern.search(comp_part)
            if grandchild_id_match is None:
                raise ValueError(f"No placeholder ID found in {comp_part}")
            grandchild_id = grandchild_id_match.group("render_id")

            parts_to_process.extend(
                [
                    TextPart(
                        text=part_before_component,
                        is_last=False,
                        parent_id=component_id,
                    ),
                    ComponentPart(
                        child_id=grandchild_id,
                        parent_id=component_id,
                        component_name_path=full_path,
                    ),
                ]
            )

        # Append any remaining text
        parts_to_process.extend(
            [
                TextPart(
                    text=comp_content[last_index:],
                    is_last=True,
                    parent_id=component_id,
                ),
            ]
        )

        process_queue.extendleft(reversed(parts_to_process))

    # Lastly, join up all pieces of the component's HTML content
    output = "".join(content_parts)

    output = on_html_rendered(output)

    return mark_safe(output)


def _call_generator_before_callback(
    on_render_generator: Optional["OnRenderGenerator"],
    inner_fn: Callable[[Optional[str], Optional[Exception]], OnComponentRenderedResult],
) -> Callable[[Optional[str], Optional[Exception]], OnComponentRenderedResult]:
    if on_render_generator is None:
        return inner_fn

    def on_component_rendered_wrapper(
        html: Optional[str],
        error: Optional[Exception],
    ) -> OnComponentRenderedResult:
        try:
            on_render_generator.send((html, error))
        # `Component.on_render()` should contain only one `yield` statement, so calling `.send()`
        # should reach `return` statement in `Component.on_render()`, which triggers `StopIteration`.
        # In that case, the value returned from `Component.on_render()` with the `return` keyword
        # is the new output (if not `None`).
        except StopIteration as generator_err:
            # To override what HTML / error gets returned, user may either:
            # - Return a new HTML at the end of `Component.on_render()` (after yielding),
            # - Raise a new error
            new_output = generator_err.value
            if new_output is not None:
                html = new_output
                error = None

        # Catch if `Component.on_render()` raises an exception, in which case this becomes
        # the new error.
        except Exception as new_error:  # noqa: BLE001
            error = new_error
            html = None
        # This raises if `StopIteration` was not raised, which may be if `Component.on_render()`
        # contains more than one `yield` statement.
        else:
            raise RuntimeError("`Component.on_render()` must include only one `yield` statement")

        return inner_fn(html, error)

    return on_component_rendered_wrapper
