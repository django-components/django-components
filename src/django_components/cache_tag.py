"""
Compatibility shim that makes Django's built-in {% cache %} tag work correctly
inside component templates.

When component_tags is loaded, this module re-registers the "cache" tag with a
subclass of Django's CacheNode whose render() clears _COMPONENT_CONTEXT_KEY before
rendering the nodelist on a cache miss.  The fix is transparent: templates continue
to use {% cache %} exactly as before; no tag rename is required.

Background
----------
django-components uses a two-pass render.  Pass 1 (bottom-up): each nested
{% component %} tag detects _COMPONENT_CONTEXT_KEY in the Django Context, stores
its renderer in a module-level dict keyed by a fresh render ID, and returns only a
placeholder `<template djc-render-id="...">`.  Pass 2 (root assembly): the root
component replaces each placeholder with the renderer's output.

When {% cache %} wraps a {% component %} inside a component template:

  Cache miss: {% component %} sees _COMPONENT_CONTEXT_KEY, returns a placeholder,
  {% cache %} stores the placeholder string.

  Cache hit: {% cache %} returns the stored placeholder directly.  {% component %}
  is never executed; no renderer is registered.  Pass 2 finds the placeholder,
  looks up the missing renderer, and raises a KeyError.

The fix: on a cache miss, temporarily remove _COMPONENT_CONTEXT_KEY from the
context before rendering the nodelist.  Each {% component %} inside then acts as a
render root and performs full two-pass assembly inline, producing complete HTML
(including <!-- _RENDERED ... --> dependency comments).  That complete HTML is what
gets cached and returned on subsequent hits.
"""

from django.template import Context
from django.templatetags.cache import CacheNode, do_cache

from django_components.context import _COMPONENT_CONTEXT_KEY


class DjcCacheNode(CacheNode):
    def render(self, context: Context) -> str:
        # If we are not inside a component render, the two-pass system is not
        # active; delegate to the original implementation unchanged.
        if not context.get(_COMPONENT_CONTEXT_KEY):
            return super().render(context)

        # Inside a component render, check the cache first (avoid touching the
        # nodelist at all on a hit — identical to the original logic).
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

        value = fragment_cache.get(cache_key)
        if value is not None:
            return value

        # Cache miss: clear _COMPONENT_CONTEXT_KEY so every {% component %} inside
        # acts as a render root and returns complete, assembled HTML.
        with context.update({_COMPONENT_CONTEXT_KEY: None}):
            value = self.nodelist.render(context)

        fragment_cache.set(cache_key, value, expire_time)
        return value


def do_djc_cache(parser, token):
    """Identical to Django's {% cache %} parser, but produces a DjcCacheNode."""
    node = do_cache(parser, token)
    node.__class__ = DjcCacheNode
    return node
