"""
Compatibility shim that makes Django's built-in {% cache %} tag work correctly
inside component templates.

Importing this module overwrites Django's "{% cache %}" tag with `DjcCacheNode`,
a subclass of Django's `CacheNode`. Templates continue to use {% cache %} exactly
as before; no tag rename is required.

Background
----------
django-components uses a two-pass render. Pass 1 (bottom-up): each nested
{% component %} tag detects _COMPONENT_CONTEXT_KEY in the Django Context, stores
its renderer in a process-local dict keyed by a fresh render ID, and returns only
a placeholder `<template djc-render-id="...">`. Pass 2 (root assembly):
the root component walks the queue and replaces every placeholder with the
renderer's output.

When {% cache %} wraps a {% component %} inside a component template:

  Cache miss: {% component %} sees _COMPONENT_CONTEXT_KEY, returns a placeholder.
  Django's {% cache %} stores the placeholder string.

  Cache hit: {% cache %} returns the stored placeholder directly. {% component %}
  is never executed; no renderer is registered. Pass 2 finds the placeholder,
  looks up the missing renderer, and raises a KeyError.

The fix: on a cache miss inside a component render, do the Pass-2 assembly
immediately (see `_assemble_cached_fragment`). The string that ends up in the
cache is fully assembled HTML with no placeholders. On a hit, that string is
returned verbatim and the outer template treats it as opaque text. The
`<!-- _RENDERED ... -->` dependency comments inside it bubble up to the real
root and get resolved by `_render_dependencies` there.

Global side effect on import
----------------------------
The bottom of this module also patches `django.templatetags.cache.register` so
the same `DjcCacheNode` is used even when a template explicitly loads Django's
own `{% load cache %}` library. This is intentional, so that load order does
not change which implementation a template picks up.

The side effect is process-global: any third-party Django code in the same
process that does `{% load cache %}{% cache %}` will get `DjcCacheNode`.
Behavior is unchanged outside a component render (`DjcCacheNode.render` early-
returns to `super().render(context)` when `_COMPONENT_CONTEXT_KEY` is unset),
but code that does an exact-type check (`type(node) is CacheNode`) will see
the subclass instead of the original.

Known limitations of cached fragments
-------------------------------------
Storing a fully-assembled string means two pieces of per-render state get frozen
into the cache:

  1. Inner components' `data-djc-id-<render_id>` attributes (the first
     render's render_ids persist on every hit).
  2. The `js_hash` / `css_hash` keys in `<!-- _RENDERED ... -->` markers.
     They look up entries in `component_media_cache`, which is `LocMemCache`
     by default (per-process). If the fragment cache outlives the process
     (Redis + a deploy), the markers reference JS/CSS variable data that no
     longer exists, and the variables silently drop from the page.

User-facing docs: `docs_old/concepts/advanced/component_caching.md`.
v3 fix (cache `RenderObject` instead of string): #1650.
"""

from django.template import Context
from django.template.base import Parser, Token
from django.templatetags.cache import CacheNode, do_cache
from django.templatetags.cache import register as django_cache_register

from django_components.component_render import OnRenderGenerator, component_context_cache, component_post_render
from django_components.context import _COMPONENT_CONTEXT_KEY
from django_components.util.misc import gen_id


# `value` contains Pass-1 placeholders (<template djc-render-id="...">) for
# any nested {% component %}. Run Pass-2 now so we cache fully assembled
# HTML, not placeholders that depend on per-render queue entries.
def _assemble_cached_fragment(context: Context, value: str) -> str:
    component_id = context.get(_COMPONENT_CONTEXT_KEY)
    if component_id is None:
        return value

    # Tree may have been GC'd between nodelist render and now.
    component_ctx = component_context_cache.get(component_id)
    if component_ctx is None:
        return value

    # Synthetic "cache" pseudo-component to act as the local Pass-2 root.
    # The yielded `value` is what component_post_render treats as the root's HTML.
    render_id = gen_id()

    def render_fragment() -> OnRenderGenerator:
        _ = yield value
        return None

    # Identity callbacks: real components use these to add `data-djc-id-...`
    # attrs and `<!-- _RENDERED ... -->` markers; the cache pseudo-component
    # has no class identity, so both are no-ops.
    component_ctx.tree.on_component_intermediate_callbacks[render_id] = lambda html: html
    component_ctx.tree.on_component_rendered_callbacks[render_id] = lambda html, error: (html, error)

    # `parent_render_id=None` makes this act as a render root, processing
    # placeholders inline. `on_component_tree_rendered` MUST stay a no-op:
    # a normal root passes `_render_dependencies` here, which resolves
    # `<!-- _RENDERED -->` into `<script>`/`<link>` tags. Doing that here
    # would break dep aggregation at the outer real root.
    #
    # Pop the callbacks in `finally` so a template-level loop with many
    # {% cache %} invocations doesn't leave one set of dead lambdas per
    # iteration in the (still-live) tree's callback dicts.
    try:
        return component_post_render(
            renderer=render_fragment(),
            render_id=render_id,
            component_name="cache",
            parent_render_id=None,
            component_tree_context=component_ctx.tree,
            on_component_tree_rendered=lambda html: html,
        )
    finally:
        component_ctx.tree.on_component_intermediate_callbacks.pop(render_id, None)
        component_ctx.tree.on_component_rendered_callbacks.pop(render_id, None)


class DjcCacheNode(CacheNode):
    def render(self, context: Context) -> str:
        # ---- djc-specific ----
        # If we are not inside a component render, the two-pass system is not
        # active; delegate to Django's original implementation unchanged. This
        # keeps {% cache %} behaving identically for non-component templates.
        if not context.get(_COMPONENT_CONTEXT_KEY):
            return super().render(context)

        # ---- Copied from django.templatetags.cache.CacheNode.render (Django 5.2)
        # The block below (expire_time / cache_name / fragment_cache / cache_key
        # / fragment_cache.get) is a verbatim port of Django's CacheNode.render,
        # with only these mechanical changes:
        #   1. Imports moved inline (PLC0415) so importing this module does not
        #      pull in cache machinery for templates that never use {% cache %}.
        #   2. `raise ... from err` instead of bare `raise` (B904).
        #   3. f-strings instead of `%` formatting.
        #   4. Hit check inverted to early-return (`if value is not None: return`)
        #      so the djc-specific assembly below is unindented.
        # Keep this block in sync with upstream when bumping Django.
        from django.core.cache import InvalidCacheBackendError, caches  # noqa: PLC0415
        from django.core.cache.utils import make_template_fragment_key  # noqa: PLC0415
        from django.template import TemplateSyntaxError, VariableDoesNotExist  # noqa: PLC0415

        try:
            expire_time = self.expire_time_var.resolve(context)
        except VariableDoesNotExist as err:
            raise TemplateSyntaxError(f'"cache" tag got an unknown variable: {self.expire_time_var.var}') from err
        if expire_time is not None:
            try:
                expire_time = int(expire_time)
            except (ValueError, TypeError) as err:
                raise TemplateSyntaxError(f'"cache" tag got a non-integer timeout value: {expire_time}') from err

        if self.cache_name:
            try:
                cache_name = self.cache_name.resolve(context)
            except VariableDoesNotExist as err:
                raise TemplateSyntaxError(f'"cache" tag got an unknown variable: {self.cache_name.var}') from err
            try:
                fragment_cache = caches[cache_name]
            except InvalidCacheBackendError as err:
                raise TemplateSyntaxError(f"Invalid cache name specified for cache tag: {cache_name}") from err
        else:
            try:
                fragment_cache = caches["template_fragments"]
            except InvalidCacheBackendError:
                fragment_cache = caches["default"]

        vary_on = [var.resolve(context) for var in self.vary_on]
        cache_key = make_template_fragment_key(self.fragment_name, vary_on)

        # Cache hit: return the stored value directly. Django does the same.
        # For djc, the stored value is fully assembled HTML (no Pass-1
        # placeholders), so the outer component's Pass-2 walks past it as text.
        value = fragment_cache.get(cache_key)
        if value is not None:
            return value
        # ---- end Django-copied block ----

        # Cache miss: render the cache body the same way Django would.
        # Inside a component render, nested {% component %} tags return Pass-1
        # placeholders (<template djc-render-id="...">), so `value` here is
        # NOT yet a complete HTML fragment.
        value = self.nodelist.render(context)

        # ---- djc-specific ----
        # Resolve those placeholders inline by running a one-shot Pass-2
        # assembly rooted at a synthetic "cache" pseudo-component. Result is
        # fully assembled HTML, with `data-djc-id-...` attributes and
        # `<!-- _RENDERED ... -->` markers baked in so the outer root can still
        # aggregate JS/CSS dependencies across the whole page.
        # See `_assemble_cached_fragment` above.
        value = _assemble_cached_fragment(context, value)

        # ---- Copied from Django: store the value and return it. ----
        fragment_cache.set(cache_key, value, expire_time)
        return value


def do_djc_cache(parser: Parser, token: Token) -> DjcCacheNode:
    """Identical to Django's {% cache %} parser, but produces a DjcCacheNode."""
    node = do_cache(parser, token)
    node.__class__ = DjcCacheNode
    return node


# Patch Django's cache library too, so explicit `{% load cache %}` keeps using
# the component-aware implementation regardless of tag library load order.
django_cache_register.tag("cache", do_djc_cache)
