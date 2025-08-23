"""This module contains optimizations for the `{% provide %}` feature."""

from contextlib import contextmanager
from typing import Dict, Generator, NamedTuple, Set

from django.template import Context

from django_components.context import _INJECT_CONTEXT_KEY_PREFIX

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

# Keep track of how many components are referencing each provided data.
provide_references: Dict[str, Set[str]] = {}

# Keep track of all the listeners that are referencing any provided data.
all_reference_ids: Set[str] = set()


@contextmanager
def managed_provide_cache(provide_id: str) -> Generator[None, None, None]:
    all_reference_ids_before = all_reference_ids.copy()

    def cache_cleanup() -> None:
        # Lastly, remove provided data from the cache that was generated during this run,
        # IF there are no more references to it.
        if provide_id in provide_references and not provide_references[provide_id]:
            provide_references.pop(provide_id)
            provide_cache.pop(provide_id)

        # Case: `{% provide %}` contained no components in its body.
        # The provided data was not referenced by any components, but it's still in the cache.
        elif provide_id not in provide_references and provide_id in provide_cache:
            provide_cache.pop(provide_id)

    try:
        yield
    except Exception as e:
        # In case of an error in `Component.render()`, there may be some
        # references left hanging, so we remove them.
        new_reference_ids = all_reference_ids - all_reference_ids_before
        for reference_id in new_reference_ids:
            unregister_provide_reference(reference_id)

        # Cleanup
        cache_cleanup()
        # Forward the error
        raise e from None

    # Cleanup
    cache_cleanup()


def register_provide_reference(context: Context, reference_id: str) -> None:
    # No `{% provide %}` among the ancestors, nothing to register to
    if not provide_cache:
        return

    all_reference_ids.add(reference_id)

    for key, provide_id in context.flatten().items():
        if not key.startswith(_INJECT_CONTEXT_KEY_PREFIX):
            continue

        if provide_id not in provide_references:
            provide_references[provide_id] = set()
        provide_references[provide_id].add(reference_id)


def unregister_provide_reference(reference_id: str) -> None:
    # No registered references, nothing to unregister
    if reference_id not in all_reference_ids:
        return

    all_reference_ids.remove(reference_id)

    for provide_id in list(provide_references.keys()):
        if reference_id not in provide_references[provide_id]:
            continue

        provide_references[provide_id].remove(reference_id)

        # There are no more references to the provided data, so we can delete it.
        if not provide_references[provide_id]:
            provide_cache.pop(provide_id)
            provide_references.pop(provide_id)
