import copy
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from django.http import HttpRequest
from django.template import Engine
from django.template.context import BaseContext, Context
from django.template.loader_tags import BlockContext

if TYPE_CHECKING:
    from collections.abc import Callable

# We cache the context processors data for each request, so that we don't have to
# generate it for each component.
context_processors_data: WeakKeyDictionary[HttpRequest, dict[str, Any]] = WeakKeyDictionary()


class CopiedDict(dict):
    """Dict subclass to identify dictionaries that have been copied with `snapshot_context`"""


def snapshot_context(context: Context) -> Context:
    """
    Make a copy of the Context object, so that it can be used as a snapshot.

    Snapshot here means that the copied Context can leave any scopes that the original
    Context is part of, and the copy will NOT be modified:

    ```py
    ctx = Context({ ... })
    with ctx.render_context.push({}):
        with ctx.update({"a": 1}):
            snapshot = snapshot_context(ctx)

    assert snapshot["a"] == 1  # OK
    assert ctx["a"] == 1       # ERROR
    ```

    This function aims to make a shallow copy, but needs to make deeper copies
    for certain features like forloops or support for `{% block %}` / `{% extends %}`.
    """
    # Using `copy()` should also copy flags like `autoescape`, `use_l10n`, etc.
    context_copy = copy.copy(context)

    # Context is a list of dicts, where the dicts can be thought of as "layers" - when a new
    # layer is added, the keys defined on the latest layer overshadow the previous layers.
    #
    # For some special cases, like when we're inside forloops, we need to make deep copies
    # of the objects created by the forloop, so all forloop metadata (index, first, last, etc.)
    # is preserved for all (potentially nested) forloops.
    #
    # For non-forloop layers, we just make shallow copies.
    dicts_with_copied_forloops: list[CopiedDict] = []

    # NOTE: For better performance, we iterate over the dicts in reverse order.
    #       This is because:
    #       1. Layers are added to the end of the list.
    #       2. We assume that user won't be replacing the dicts in the older layers.
    #       3. Thus, when we come across a layer that has already been copied,
    #          we know that all layers before it have also been copied.
    for ctx_dict_index in reversed(range(len(context.dicts))):
        ctx_dict = context.dicts[ctx_dict_index]

        # This layer is already copied, reuse this and all before it
        if isinstance(ctx_dict, CopiedDict):
            # NOTE: +1 because we want to include the current layer
            dicts_with_copied_forloops = context.dicts[: ctx_dict_index + 1] + dicts_with_copied_forloops
            break

        # Copy the dict
        ctx_dict_copy = CopiedDict(ctx_dict)
        if "forloop" in ctx_dict:
            ctx_dict_copy["forloop"] = ctx_dict["forloop"].copy()

            # Recursively copy the state of potentially nested forloops
            curr_forloop = ctx_dict_copy["forloop"]
            while curr_forloop is not None:
                curr_forloop["parentloop"] = curr_forloop["parentloop"].copy()
                if "parentloop" in curr_forloop["parentloop"]:
                    curr_forloop = curr_forloop["parentloop"]
                else:
                    break

        dicts_with_copied_forloops.insert(0, ctx_dict_copy)

    context_copy.dicts = dicts_with_copied_forloops

    # Make a copy of RenderContext
    render_ctx_copies: list[CopiedDict] = []
    for render_ctx_dict_index in reversed(range(len(context.render_context.dicts))):
        render_ctx_dict = context.render_context.dicts[render_ctx_dict_index]

        # This layer is already copied, reuse this and all before it
        if isinstance(render_ctx_dict, CopiedDict):
            # NOTE: +1 because we want to include the current layer
            render_ctx_copies = context.render_context.dicts[: render_ctx_dict_index + 1] + render_ctx_copies
            break

        # This holds info on what `{% block %}` blocks are defined
        render_ctx_dict_copy = CopiedDict(render_ctx_dict)
        if "block_context" in render_ctx_dict:
            render_ctx_dict_copy["block_context"] = _copy_block_context(render_ctx_dict["block_context"])

        # "extends_context" is a list of Origin objects
        if "extends_context" in render_ctx_dict:
            render_ctx_dict_copy["extends_context"] = render_ctx_dict["extends_context"].copy()

        render_ctx_dict_copy["_djc_snapshot"] = True
        render_ctx_copies.insert(0, render_ctx_dict_copy)

    context_copy.render_context.dicts = render_ctx_copies
    return context_copy


def _copy_block_context(block_context: BlockContext) -> BlockContext:
    """Make a shallow copy of BlockContext"""
    block_context_copy = block_context.__class__()
    for key, val in block_context.blocks.items():
        # Individual dict values should be lists of Nodes. We don't
        # need to modify the Nodes, but we need to make a copy of the lists.
        block_context_copy.blocks[key] = val.copy()
    return block_context_copy


# Django's logic for generating context processors data. The gist is the same as
# `RequestContext.bind_template()`, but without depending on a Template object.
# See https://github.com/django/django/blame/2d34ebe49a25d0974392583d5bbd954baf742a32/django/template/context.py#L255
def gen_context_processors_data(context: BaseContext, request: HttpRequest) -> dict[str, Any]:
    if request in context_processors_data:
        return context_processors_data[request].copy()

    # TODO_REMOVE_IN_V2 - In v2, if we still support context processors,
    #     it should be set on our settings, so we wouldn't have to get the Engine for that.
    #     In v2 it should be also possible to remove RequestContext, and use only Context,
    #     since we're internalized the behaviour of RequestContext.
    default_engine = Engine.get_default()

    # NOTE: Compatibility with `RequestContext`, which accepts an optional
    #       `processors` argument.
    request_context_processors: tuple[Callable[..., Any], ...] = getattr(context, "_processors", ())

    # This part is same as in `RequestContext.bind_template()`
    processors = default_engine.template_context_processors + request_context_processors
    processors_data = {}
    for processor in processors:
        data = processor(request)
        try:
            processors_data.update(data)
        except TypeError as e:
            raise TypeError(f"Context processor {processor.__qualname__} didn't return a dictionary.") from e

    context_processors_data[request] = processors_data

    return processors_data
