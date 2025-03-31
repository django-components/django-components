Component caching allows you to store the rendered output of a component. Next time the component is rendered
with the same input, the cached output is returned instead of re-rendering the component.

This is particularly useful for components that are expensive to render or do not change frequently.

!!! info

    Component caching uses Django's cache framework, so you can use any cache backend that is supported by Django.

### Enabling caching

Caching is disabled by default.

To enable caching for a component, set [`Component.Cache.enabled`](../../reference/api.md#django_components.ComponentCache.enabled) to `True`:

```python
from django_components import Component

class MyComponent(Component):
    class Cache:
        enabled = True
```

### Time-to-live (TTL)

You can specify a time-to-live (TTL) for the cache entry with [`Component.Cache.ttl`](../../reference/api.md#django_components.ComponentCache.ttl), which determines how long the entry remains valid. The TTL is specified in seconds.

```python
class MyComponent(Component):
    class Cache:
        enabled = True
        ttl = 60 * 60 * 24  # 1 day
```

- If `ttl > 0`, entries are cached for the specified number of seconds.
- If `ttl = -1`, entries are cached indefinitely.
- If `ttl = 0`, entries are not cached.
- If `ttl = None`, the default TTL is used.

### Custom cache name

Since component caching uses Django's cache framework, you can specify a custom cache name with [`Component.Cache.cache_name`](../../reference/api.md#django_components.ComponentCache.cache_name) to use a different cache backend:

```python
class MyComponent(Component):
    class Cache:
        enabled = True
        cache_name = "my_cache"
```

### Cache key generation

By default, the cache key is generated based on the component's input (args and kwargs). So the following two calls would generate separate entries in the cache:

```py
MyComponent.render(name="Alice")
MyComponent.render(name="Bob")
```

However, you have full control over the cache key generation. As such, you can:

- Cache the component on all inputs (default)
- Cache the component on particular inputs
- Cache the component irrespective of the inputs

To achieve that, you can override
the [`Component.Cache.hash_args()`](../../reference/api.md#django_components.ComponentCache.hash_args)
and [`Component.Cache.hash_kwargs()`](../../reference/api.md#django_components.ComponentCache.hash_kwargs)
methods to customize how arguments are hashed into the cache key.

```python
class MyComponent(Component):
    class Cache:
        enabled = True

        def hash_args(self, args):
            return "custom-args"

        def hash_kwargs(self, kwargs):
            return "custom-kwargs"
```

For even more control, you can override the [`Component.Cache.hash_input()`](../../reference/api.md#django_components.ComponentCache.hash_input) method, or other methods available on the [`ComponentCache`](../../reference/api.md#django_components.ComponentCache) class.

### Example

Here's a complete example of a component with caching enabled:

```python
from django_components import Component

class MyComponent(Component):
    template = "Hello, {{ name }}"

    class Cache:
        enabled = True
        ttl = 300  # Cache for 5 minutes
        cache_name = "my_cache"

    def get_context_data(self, name, **kwargs):
        return {"name": name}
```

In this example, the component's rendered output is cached for 5 minutes using the `my_cache` backend.
