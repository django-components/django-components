import re
from collections import deque
from typing import TYPE_CHECKING, Callable, Deque, Dict, List, NamedTuple, Optional, Tuple

from django.utils.safestring import mark_safe

from django_components.constants import COMP_ID_LENGTH
from django_components.util.exception import component_error_message

if TYPE_CHECKING:
    from django_components.component import ComponentContext

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


class PostRenderQueueItem(NamedTuple):
    content_before_component: str
    child_id: Optional[str]
    parent_id: Optional[str]
    grandparent_id: Optional[str]
    component_name_path: List[str]

    def __repr__(self) -> str:
        return (
            f"PostRenderQueueItem(child_id={self.child_id!r}, parent_id={self.parent_id!r}, "
            f"grandparent_id={self.grandparent_id!r}, component_name_path={self.component_name_path!r}, "
            f"content_before_component={self.content_before_component[:10]!r})"
        )


# Function that accepts a list of extra HTML attributes to be set on the component's root elements
# and returns the component's HTML content and a dictionary of child components' IDs
# and their root elements' HTML attributes.
#
# In other words, we use this to "delay" the actual rendering of the component's HTML content,
# until we know what HTML attributes to apply to the root elements.
ComponentRenderer = Callable[[Optional[List[str]]], Tuple[str, Dict[str, List[str]]]]

# Render-time cache for component rendering
# See component_post_render()
component_renderer_cache: Dict[str, Tuple[ComponentRenderer, str]] = {}
child_component_attrs: Dict[str, List[str]] = {}

nested_comp_pattern = re.compile(
    r'<template [^>]*?djc-render-id="\w{{{COMP_ID_LENGTH}}}"[^>]*?></template>'.format(COMP_ID_LENGTH=COMP_ID_LENGTH)
)
render_id_pattern = re.compile(
    r'djc-render-id="(?P<render_id>\w{{{COMP_ID_LENGTH}}})"'.format(COMP_ID_LENGTH=COMP_ID_LENGTH)
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
    on_component_rendered_callbacks: Dict[str, Callable[[str], str]],
    on_html_rendered: Callable[[str], str],
) -> str:
    # Instead of rendering the component's HTML content immediately, we store it,
    # so we can render the component only once we know if there are any HTML attributes
    # to be applied to the resulting HTML.
    component_renderer_cache[render_id] = (renderer, component_name)

    if parent_id is not None:
        # Case: Nested component
        # If component is nested, return a placeholder
        return mark_safe(f'<template djc-render-id="{render_id}"></template>')

    # Case: Root component - Construct the final HTML by recursively replacing placeholders
    #
    # We first generate the component's HTML content, by calling the renderer.
    #
    # Then we process the component's HTML from root-downwards, going depth-first.
    # So if we have a structure:
    # <div>
    #   <h2>...</h2>
    #   <template djc-render-id="a1b3cf"></template>
    #   <span>...</span>
    #   <template djc-render-id="f3d3cf"></template>
    # </div>
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
    process_queue: Deque[PostRenderQueueItem] = deque()

    process_queue.append(
        PostRenderQueueItem(
            content_before_component="",
            child_id=render_id,
            parent_id=None,
            grandparent_id=None,
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
    # We know when we've arrived at component's end, because `child_id` will be set to `None`.
    # So we can collect the HTML parts by the component ID, and when we hit the end, we join
    # all the bits that belong to the same component.
    #
    # Once the component's HTML is joined, we can call the callback for the component, and
    # then add the joined HTML to the cache for the parent component to continue the cycle.
    html_parts_by_component_id: Dict[str, List[str]] = {}
    content_parts: List[str] = []

    def get_html_parts(component_id: str) -> List[str]:
        if component_id not in html_parts_by_component_id:
            html_parts_by_component_id[component_id] = []
        return html_parts_by_component_id[component_id]

    while len(process_queue):
        curr_item = process_queue.popleft()

        # In this case we've reached the end of the component's HTML content, and there's
        # no more subcomponents to process.
        if curr_item.child_id is None:
            # Parent ID must NOT be None in this branch
            if curr_item.parent_id is None:
                raise RuntimeError("Parent ID is None")

            parent_parts = html_parts_by_component_id.pop(curr_item.parent_id, [])

            # Add the left-over content
            parent_parts.append(curr_item.content_before_component)

            # Allow to optionally override/modify the rendered content from outside
            component_html = "".join(parent_parts)
            on_component_rendered = on_component_rendered_callbacks[curr_item.parent_id]
            component_html = on_component_rendered(component_html)  # type: ignore[arg-type]

            # Add the component's HTML to parent's parent's HTML parts
            if curr_item.grandparent_id is not None:
                target_list = get_html_parts(curr_item.grandparent_id)
                target_list.append(component_html)
            else:
                content_parts.append(component_html)

            continue

        # Process content before the component
        if curr_item.content_before_component:
            if curr_item.parent_id is None:
                raise RuntimeError("Parent ID is None")
            parent_html_parts = get_html_parts(curr_item.parent_id)
            parent_html_parts.append(curr_item.content_before_component)

        # Generate component's content, applying the extra HTML attributes set by the parent component
        curr_comp_renderer, curr_comp_name = component_renderer_cache.pop(curr_item.child_id)
        # NOTE: This may be undefined, because this is set only for components that
        # are also root elements in their parent's HTML
        curr_comp_attrs = child_component_attrs.pop(curr_item.child_id, None)

        full_path = [*curr_item.component_name_path, curr_comp_name]

        # This is where we actually render the component
        #
        # NOTE: [1:] because the root component will be yet again added to the error's
        # `components` list in `_render_with_error_trace` so we remove the first element from the path.
        with component_error_message(full_path[1:]):
            curr_comp_content, grandchild_component_attrs = curr_comp_renderer(curr_comp_attrs)

        # Exclude the `data-djc-scope-...` attribute from being applied to the child component's HTML
        for key in list(grandchild_component_attrs.keys()):
            if key.startswith("data-djc-scope-"):
                grandchild_component_attrs.pop(key, None)

        child_component_attrs.update(grandchild_component_attrs)

        # Process the component's content
        last_index = 0
        parts_to_process: List[PostRenderQueueItem] = []

        # Split component's content by placeholders, and put the pairs of (content, placeholder_id) into the queue
        for match in nested_comp_pattern.finditer(curr_comp_content):
            part_before_component = curr_comp_content[last_index : match.start()]  # noqa: E203
            last_index = match.end()
            comp_part = match[0]

            # Extract the placeholder ID from `<template djc-render-id="a1b3cf"></template>`
            grandchild_id_match = render_id_pattern.search(comp_part)
            if grandchild_id_match is None:
                raise ValueError(f"No placeholder ID found in {comp_part}")
            grandchild_id = grandchild_id_match.group("render_id")
            parts_to_process.append(
                PostRenderQueueItem(
                    content_before_component=part_before_component,
                    child_id=grandchild_id,
                    parent_id=curr_item.child_id,
                    grandparent_id=curr_item.parent_id,
                    component_name_path=full_path,
                )
            )

        # Append any remaining text
        parts_to_process.append(
            PostRenderQueueItem(
                content_before_component=curr_comp_content[last_index:],
                # Setting `child_id` to None means that this is the last part of the component's HTML
                # and we're done with this component
                child_id=None,
                parent_id=curr_item.child_id,
                grandparent_id=curr_item.parent_id,
                component_name_path=full_path,
            )
        )

        process_queue.extendleft(reversed(parts_to_process))

    # Lastly, join up all pieces of the component's HTML content
    output = "".join(content_parts)

    output = on_html_rendered(output)

    return mark_safe(output)
