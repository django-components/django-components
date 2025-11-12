"""This module contains optimizations for the `{% provide %}` feature."""

from collections import defaultdict
from contextlib import contextmanager
from typing import TYPE_CHECKING, Dict, Generator, NamedTuple, Set, cast

from django.template import Context

from django_components.context import _INJECT_CONTEXT_KEY_PREFIX

if TYPE_CHECKING:
    from django_components.component import Component

# Originally, when `{% provide %}` was used, the provided data was passed down
# through the Context object.
#
# However, this was hard to debug if the provided data was large (e.g. a long
# list of items).
#
# Instead, similarly to how the component internal data is passed through
# the Context object, there's now a level of indirection - the Context now stores
# only a key that points to the provided data.
#
# So when we inspect a Context layers, we may see something like this:
#
# ```py
# [
#     {"False": False, "None": None, "True": True}, # All Contexts contain this
#     {"custom_key": "custom_value"},               # Data passed to Context()
#     {"_DJC_INJECT__my_provide": "a1b3c3"},        # Data provided by {% provide %}
#                                                   # containing only the key to "my_provide"
# ]
# ```
#
# Since the provided data is represented only as a key, we have to store the ACTUAL
# data somewhere. Thus, we store it in a separate dictionary.
#
# So when one calls `Component.inject(key)`, we use the key to look up the actual data
# in the dictionary and return that.
#
# This approach has several benefits:
# - Debugging: One needs to only follow the IDs to trace the flow of data.
# - Debugging: All provided data is stored in a separate dictionary, so it's easy to
#   see what data is provided.
# - Perf: The Context object is copied each time we call `Component.render()`, to have a "snapshot"
#   of the context, in order to defer the rendering. Passing around only the key instead
#   of actual value avoids potentially copying the provided data. This also keeps the source of truth
#   unambiguous.
# - Tests: It's easier to test the provided data, as we can just modify the dictionary directly.
#
# However, there is a price to pay for this:
# - Manual memory management - Because the data is stored in a separate dictionary, we now need to
#   keep track of when to delete the entries.
#
# The challenge with this manual memory management is that:
# 1. Component rendering is deferred, so components are rendered AFTER we finish `Template.render()`.
# 2. For the deferred rendering, we copy the Context object.
#
# This means that:
# 1. We can't rely on simply reaching the end of `Template.render()` to delete the provided data.
# 2. We can't rely on the Context object being deleted to delete the provided data.
#
# So we need to manually delete the provided data when we know it's no longer needed.
#
# Thus, the strategy is to count references to the provided data:
# 1. When `{% provide %}` is used, it adds a key to the context.
# 2. When we come across `{% component %}` that is within the `{% provide %}` tags,
#    the component will see the provide's key and the component will register itself as a "child" of
#    the `{% provide %}` tag at `Component.render()`.
# 3. Once the component's deferred rendering takes place and finishes, the component makes a call
#    to unregister itself from any "subscribed" provided data.
# 4. While unsubscribing, if we see that there are no more children subscribed to the provided data,
#    we can finally delete the provided data from the cache.
#
# However, this leaves open the edge case of when `{% provide %}` contains NO components.
# In such case, we check if there are any subscribed components after rendering the contents
# of `{% provide %}`. If there are NONE, we delete the provided data.


# Similarly to ComponentContext instances, we store the actual Provided data
# outside of the Context object, to make it easier to debug the data flow.
provide_cache: Dict[str, NamedTuple] = {}

# Given a `{% provide %}` instance, keep track of which components are referencing it.
# ProvideID -> Component[]
# NOTE: We manually clean up the entries when either:
#       - `{% provide %}` ends and there are no more references to it
#       - The last component that referenced it is garbage collected
provide_references: Dict[str, Set[str]] = defaultdict(set)

# The opposite - Given a component, keep track of which `{% provide %}` instances it is referencing.
# Component -> ProvideID[]
# NOTE: We manually clean up the entries when components are garbage collected.
component_provides: Dict[str, Dict[str, str]] = defaultdict(dict)

# Track which {% provide %} blocks are currently active (rendering).
# This prevents premature cache cleanup when components are garbage collected.
active_provides: Set[str] = set()


@contextmanager
def managed_provide_cache(provide_id: str) -> Generator[None, None, None]:
    # Mark this provide block as active
    active_provides.add(provide_id)
    try:
        yield
    except Exception as e:
        # Mark this provide block as no longer active
        active_provides.discard(provide_id)
        # NOTE: In case of an error in within the `{% provide %}` block (e.g. when rendering a component),
        # we rely on the component finalizer to remove the references.
        # But we still want to call cleanup in case `{% provide %}` contained no components.
        _cache_cleanup(provide_id)
        # Forward the error
        raise e from None

    # Mark this provide block as no longer active
    active_provides.discard(provide_id)
    # Cleanup on success
    _cache_cleanup(provide_id)


def _cache_cleanup(provide_id: str) -> None:
    # Don't cleanup if the provide block is still active.
    if provide_id in active_provides:
        return

    # Remove provided data from the cache, IF there are no more references to it.
    # A `{% provide %}` will have no reference if:
    # - It contains no components in its body
    # - It contained components, but those components were already garbage collected
    if provide_id in provide_references and not provide_references[provide_id]:
        provide_references.pop(provide_id)
        provide_cache.pop(provide_id, None)

    # Case: `{% provide %}` contained no components in its body.
    # The provided data was not referenced by any components, but it's still in the cache.
    elif provide_id not in provide_references and provide_id in provide_cache:
        provide_cache.pop(provide_id)


# TODO - Once components can access their parents:
#        Do NOT pass provide keys through components in isolated mode.
#        Instead get parent's provide keys by getting the parent's id, `component.parent.id`
#        and then accessing `component_provides[component.parent.id]`.
#        The logic below would still remain, as that defines the `{% provide %}`
#        instances defined INSIDE the parent component.
#        And we would combine the two sources, and set that to `component_provides[component.id]`.
def register_provide_reference(context: Context, component: "Component") -> None:
    # No `{% provide %}` among the ancestors, nothing to register to
    if not provide_cache:
        return

    # For all instances of `{% provide %}` that the current component is within,
    # make note that this component has access to them.
    for key, value in context.flatten().items():
        # NOTE: Provided data is stored on the Context object as e.g.
        # `{"_DJC_INJECT__my_provide": "a1b3c3"}`
        # Where "a1b3c3" is the ID of the provided data.
        if not key.startswith(_INJECT_CONTEXT_KEY_PREFIX):
            continue

        provide_id = cast("str", value)
        provide_key = key.split(_INJECT_CONTEXT_KEY_PREFIX, 1)[1]

        # Update the Provide -> Component[] mapping.
        provide_references[provide_id].add(component.id)

        # Update the Component -> Provide[] mapping.
        component_provides[component.id][provide_key] = provide_id


def unregister_provide_reference(component_id: str) -> None:
    # List of `{% provide %}` IDs that the component had access to.
    component_provides_ids = component_provides.get(component_id)
    if not component_provides_ids:
        return

    # Remove this component from all provide references it was subscribed to
    for provide_id in component_provides_ids.values():
        references_to_this_provide = provide_references.get(provide_id)
        if references_to_this_provide:
            references_to_this_provide.discard(component_id)


def unlink_component_from_provide_on_gc(component_id: str) -> None:
    """
    Finalizer function to be called when a Component object is garbage collected.

    Unlinking the component at this point ensures that one can call `Component.inject()`
    even after the component was rendered, as long as one keeps the reference to the component object.
    """
    unregister_provide_reference(component_id)
    provide_ids = component_provides.pop(component_id, None)
    if provide_ids:
        for provide_id in provide_ids.values():
            _cache_cleanup(provide_id)
