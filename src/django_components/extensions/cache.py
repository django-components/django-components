from typing import Any, Optional, Sequence

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

    def get_cache_key(self, *args: Any, **kwargs: Any) -> str:
        # Allow user to override how the input is hashed into a cache key with `hash_input()`,
        # but then still prefix it wih our own prefix, so it's clear where it comes from.
        cache_key = self.hash_input(*args, **kwargs)
        cache_key = CACHE_KEY_PREFIX + cache_key
        return cache_key

    def hash_input(self, *args: Any, **kwargs: Any) -> str:
        """
        Defines how the input (both args and kwargs) iss hashed into a cache key.

        By default, `hash_input()` calls
        [`hash_args()`](../api#django_components.ComponentCache.hash_args)
        and [`hash_kwargs()`](../api#django_components.ComponentCache.hash_kwargs).
        """
        args_hash = self.hash_args(args)
        kwargs_hash = self.hash_kwargs(kwargs)
        return f"{self.component._class_hash}:{args_hash}:{kwargs_hash}"

    def hash_args(self, args: Sequence[Any]) -> str:
        """Defines how positional arguments are hashed into a cache key segment."""
        return "-".join(str(arg) for arg in args)

    def hash_kwargs(self, kwargs: dict) -> str:
        """Defines how keyword arguments are hashed into a cache key segment."""
        # Sort keys to ensure consistent ordering
        sorted_items = sorted(kwargs.items())
        return "-".join(f"{k}:{v}" for k, v in sorted_items)


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
        cache_instance: ComponentCache = ctx.component.cache
        if not cache_instance.enabled:
            return None

        cache_key = cache_instance.get_cache_key(*ctx.args, **ctx.kwargs)
        self.render_id_to_cache_key[ctx.component_id] = cache_key

        # If cache entry exists, return it. This will short-circuit the rendering process.
        cached_result = cache_instance.get_entry(cache_key)
        if cached_result is not None:
            return cached_result
        return None

    # Save the rendered component to cache
    def on_component_rendered(self, ctx: OnComponentRenderedContext) -> None:
        cache_instance: ComponentCache = ctx.component.cache
        if not cache_instance.enabled:
            return None

        cache_key = self.render_id_to_cache_key[ctx.component_id]
        cache_instance.set_entry(cache_key, ctx.result)
