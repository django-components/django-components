Component caching allows you to store the rendered output of a component. Next time the component is rendered
with the same input, the cached output is returned instead of re-rendering the component.

This is particularly useful for components that are expensive to render or do not change frequently.

!!! info

    Component caching uses [Django's cache framework](https://docs.djangoproject.com/en/5.2/topics/cache/),
    so you can use any cache backend that is supported by Django.

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
the [`Component.Cache.hash()`](../../reference/api.md#django_components.ComponentCache.hash)
method to customize how arguments are hashed into the cache key.

```python
class MyComponent(Component):
    class Cache:
        enabled = True

        def hash(self, *args, **kwargs):
            return f"{json.dumps(args)}:{json.dumps(kwargs)}"
```

For even more control, you can override other methods available on the [`ComponentCache`](../../reference/api.md#django_components.ComponentCache) class.

!!! warning

    The default implementation of `Cache.hash()` simply serializes the input into a string.
    As such, it might not be suitable if you need to hash complex objects like Models.

### Caching slots

By default, the cache key is generated based ONLY on the args and kwargs.

To cache the component based on the slots, set [`Component.Cache.include_slots`](../../reference/api.md#django_components.ComponentCache.include_slots) to `True`:

```python
class MyComponent(Component):
    class Cache:
        enabled = True
        include_slots = True
```

with `include_slots = True`, the cache key will be generated also based on the given slots.

As such, the following two calls would generate separate entries in the cache:

```django
{% component "my_component" position="left" %}
    Hello, Alice
{% endcomponent %}

{% component "my_component" position="left" %}
    Hello, Bob
{% endcomponent %}
```

Same when using [`Component.render()`](../../reference/api.md#django_components.Component.render) with string slots:

```py
MyComponent.render(
    kwargs={"position": "left"},
    slots={"content": "Hello, Alice"}
)
MyComponent.render(
    kwargs={"position": "left"},
    slots={"content": "Hello, Bob"}
)
```

!!! warning

    Passing slots as functions to cached components with `include_slots=True` will raise an error.

    ```py
    MyComponent.render(
        kwargs={"position": "left"},
        slots={"content": lambda ctx: "Hello, Alice"}
    )
    ```

!!! warning

    Slot caching DOES NOT account for context variables within
    the [`{% fill %}`](../../reference/template_tags.md#fill) tag.

    For example, the following two cases will be treated as the same entry:

    ```django
    {% with my_var="foo" %}
        {% component "mycomponent" name="foo" %}
            {{ my_var }}
        {% endcomponent %}
    {% endwith %}

    {% with my_var="bar" %}
        {% component "mycomponent" name="bar" %}
            {{ my_var }}
        {% endcomponent %}
    {% endwith %}
    ```

    Currently it's impossible to capture used variables. This will be addressed in v2.
    Read more about it in [django-components/#1164](https://github.com/django-components/django-components/issues/1164).

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

    def get_template_data(self, args, kwargs, slots, context):
        return {"name": kwargs["name"]}
```

In this example, the component's rendered output is cached for 5 minutes using the `my_cache` backend.

## Using Django's `{% cache %}` tag with components

You can wrap Django's
[`{% cache %}` tag](https://docs.djangoproject.com/en/5.2/topics/cache/#template-fragment-caching)
around `{% component %}` calls:

```django
{% load component_tags %}
{% cache 500 "homepage_sidebar" %}
    {% component "user_links" / %}
    {% component "recent_posts" / %}
{% endcache %}
```

It works out of the box; loading `component_tags` installs a component-aware
version of `{% cache %}` automatically.

Use `{% cache %}` to cache a *region* of a template (possibly with several
components inside). Use `Component.Cache` (above) to cache a *single
component* by its inputs.

### Things to watch out for

A cache entry is the **first render's** output, replayed verbatim on every
subsequent hit. A few cases where that bites you:

#### Clicking a button fires the handler more than once

If you embed the same `{% cache %}` block in two places on one page (e.g. a
sidebar in both the header and footer, both with the same cache key), the
inner component's client-side wiring ends up duplicated. A `click` or
`input` handler from `Component.js` will fire N times per event, where N is
the number of embeddings.

❌ Don't:

```django
{# Header and footer, both with the same key #}
{% cache 500 "search_box" %}{% component "search_input" / %}{% endcache %}
...
{% cache 500 "search_box" %}{% component "search_input" / %}{% endcache %}
```

✅ Do: use a distinct cache key per position, or only cache fragments that
appear once per page.

#### After a deploy, components silently lose their JS/CSS variables

If your fragment cache is a persistent backend (Redis, memcached) and your
components define `get_js_data()` or `get_css_data()`, the data those
methods produce can vanish from the page after a server restart. The HTML
still renders normally and no errors are logged, but the per-instance JS
or CSS variables are gone.

This happens because djc stores the actual variable values in a separate
cache that is **per-process and in-memory by default**. After a restart,
the cached fragment refers to variable data the new process no longer has.

✅ Do: set the
[`cache` setting](../../reference/settings.md#django_components.app_settings.ComponentsSettings.cache)
to the same persistent backend you use for the fragment cache, so the
variables survive restarts.

#### Every user sees the first user's data

```django
{# Cache key includes user.id but NOT user.locale #}
{% cache 500 "user_panel" user.id %}
    {% component "user_panel" user=user / %}
{% endcache %}
```

If the component's output depends on `user.locale` (or any input not in
`vary_on`), the first user's locale freezes into the cache. Every other
user with the same `user.id` sees that locale until the entry expires.

✅ Do: include every input that affects the rendered output in `vary_on`.
This is true of any Django fragment cache, but with components it can also
affect client-side behavior, not just visible markup.

### Importing djc patches Django's `{% cache %}` globally

Importing `django_components` replaces Django's built-in `{% cache %}` tag
for the whole Python process, including in plain (non-component) templates.

Behavior is unchanged outside a component render: the patched tag delegates
to Django's original implementation. The only observable difference is for
third-party code that checks `type(node) is CacheNode` — it will see djc's
subclass instead.
