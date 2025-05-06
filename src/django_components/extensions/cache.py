from typing import Any, Dict, List, Optional

from django.core.cache import BaseCache, caches

from django_components.extension import (
    ComponentExtension,
    OnComponentInputContext,
    OnComponentRenderedContext,
)

# NOTE: We allow users to override cache key generation, but then we internally
# still prefix their key with our own prefix, so it's clear where it comes from.
CACHE_KEY_PREFIX = "components:cache:"


class ComponentCache(ComponentExtension.ExtensionClass):  # type: ignore
    """
    The interface for `Component.Cache`.

    The fields of this class are used to configure the component caching.

    Read more about [Component caching](../../concepts/advanced/component_caching).

    **Example:**

    ```python
    from django_components import Component

    class MyComponent(Component):
        class Cache:
            enabled = True
            ttl = 60 * 60 * 24  # 1 day
            cache_name = "my_cache"
    ```
    """

    enabled: bool = False
    """
    Whether this Component should be cached. Defaults to `False`.
    """

    ttl: Optional[int] = None
    """
    The time-to-live (TTL) in seconds, i.e. for how long should an entry be valid in the cache.

    - If `> 0`, the entries will be cached for the given number of seconds.
    - If `-1`, the entries will be cached indefinitely.
    - If `0`, the entries won't be cached.
    - If `None`, the default TTL will be used.
    """

    cache_name: Optional[str] = None
    """
    The name of the cache to use. If `None`, the default cache will be used.
    """

    def get_entry(self, cache_key: str) -> Any:
        cache = self.get_cache()
        return cache.get(cache_key)

    def set_entry(self, cache_key: str, value: Any) -> None:
        cache = self.get_cache()
        cache.set(cache_key, value, timeout=self.ttl)

    def get_cache(self) -> BaseCache:
        cache_name = self.cache_name or "default"
        cache = caches[cache_name]
        return cache

    def get_cache_key(self, args: List, kwargs: Dict, slots: Dict) -> str:
        # Allow user to override how the input is hashed into a cache key with `hash()`,
        # but then still prefix it wih our own prefix, so it's clear where it comes from.
        cache_key = self.hash(args, kwargs)
        cache_key = CACHE_KEY_PREFIX + self.component._class_hash + ":" + cache_key
        return cache_key

    def hash(self, args: List, kwargs: Dict) -> str:
        """
        Defines how the input (both args and kwargs) is hashed into a cache key.

        By default, `hash()` serializes the input into a string. As such, the default
        implementation might NOT be suitable if you need to hash complex objects.
        """
        args_hash = ",".join(str(arg) for arg in args)
        # Sort keys to ensure consistent ordering
        sorted_items = sorted(kwargs.items())
        kwargs_hash = ",".join(f"{k}-{v}" for k, v in sorted_items)
        return f"{args_hash}:{kwargs_hash}"


class CacheExtension(ComponentExtension):
    """
    This extension adds a nested `Cache` class to each `Component`.

    This nested `Cache` class is used to configure component caching.

    **Example:**

    ```python
    from django_components import Component

    class MyComponent(Component):
        class Cache:
            enabled = True
            ttl = 60 * 60 * 24  # 1 day
            cache_name = "my_cache"
    ```

    This extension is automatically added to all components.
    """

    name = "cache"

    ExtensionClass = ComponentCache

    def __init__(self, *args: Any, **kwargs: Any):
        self.render_id_to_cache_key: dict[str, str] = {}

    def on_component_input(self, ctx: OnComponentInputContext) -> Optional[Any]:
        cache_instance = ctx.component.cache
        if not cache_instance.enabled:
            return None

        cache_key = cache_instance.get_cache_key(ctx.args, ctx.kwargs, ctx.slots)
        self.render_id_to_cache_key[ctx.component_id] = cache_key

        # If cache entry exists, return it. This will short-circuit the rendering process.
        cached_result = cache_instance.get_entry(cache_key)
        if cached_result is not None:
            return cached_result
        return None

    # Save the rendered component to cache
    def on_component_rendered(self, ctx: OnComponentRenderedContext) -> None:
        cache_instance = ctx.component.cache
        if not cache_instance.enabled:
            return None

        cache_key = self.render_id_to_cache_key[ctx.component_id]
        cache_instance.set_entry(cache_key, ctx.result)
