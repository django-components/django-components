"""
This file centralizes various ways we use Django's Context class
pass data across components, nodes, slots, and contexts.

Compared to `django_components/util/context.py`, this file contains the "business" logic
and the list of all internal keys that we define on the `Context` object.
"""

from django.template import Context

from django_components.util.misc import get_last_index

_COMPONENT_CONTEXT_KEY = "_DJC_COMPONENT_CTX"
_STRATEGY_CONTEXT_KEY = "DJC_DEPS_STRATEGY"
_INJECT_CONTEXT_KEY_PREFIX = "_DJC_INJECT__"


def make_isolated_context_copy(context: Context) -> Context:
    context_copy = context.new()
    _copy_forloop_context(context, context_copy)

    # Required for compatibility with Django's {% extends %} tag
    # See https://github.com/django-components/django-components/pull/859
    context_copy.render_context = context.render_context

    # Pass through our internal keys
    if _COMPONENT_CONTEXT_KEY in context:
        context_copy[_COMPONENT_CONTEXT_KEY] = context[_COMPONENT_CONTEXT_KEY]

    # Make inject/provide to work in isolated mode
    context_keys = context.flatten().keys()
    for key in context_keys:
        if key.startswith(_INJECT_CONTEXT_KEY_PREFIX):
            context_copy[key] = context[key]

    return context_copy


def _copy_forloop_context(from_context: Context, to_context: Context) -> None:
    """Forward the info about the current loop"""
    # Note that the ForNode (which implements `{% for %}`) does not
    # only add the `forloop` key, but also keys corresponding to the loop elements
    # So if the loop syntax is `{% for my_val in my_lists %}`, then ForNode also
    # sets a `my_val` key.
    # For this reason, instead of copying individual keys, we copy the whole stack layer
    # set by ForNode.
    if "forloop" in from_context:
        forloop_dict_index = get_last_index(from_context.dicts, lambda d: "forloop" in d) or -1
        to_context.update(from_context.dicts[forloop_dict_index])
