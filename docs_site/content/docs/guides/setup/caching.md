This page describes the kinds of assets that django-components caches and how to configure the cache backends.

## Component caching

You can cache the output of your components by setting the [`Component.Cache`][Component.Cache] options.

Read more about [Component caching](../../concepts/advanced/component_caching.md).

## Component's JS and CSS files

django-components simultaneously supports:

- Rendering and fetching components as HTML fragments
- Allowing components (even fragments) to have JS and CSS files associated with them
- Features like JS/CSS variables or CSS scoping

To achieve all this, django-components defines additional temporary JS and CSS files. These temporary files need to be stored somewhere, so that they can be fetched by the browser when the component is rendered as a fragment. And for that, django-components uses Django's cache framework.

This includes:

- Inlined JS/CSS defined via [`Component.js`][Component.js] and [`Component.css`][Component.css]
- JS/CSS variables generated from [`get_js_data()`][Component.get_js_data] and [`get_css_data()`][Component.get_css_data]

By default, django-components uses Django's local memory cache backend to store these assets. You can configure it to use any of your Django cache backends by setting the [`COMPONENTS.cache`][ComponentsSettings.cache] option in your settings:

```python
COMPONENTS = {
    # Name of the cache backend to use
    "cache": "my-cache-backend",
}
```

The value should be the name of one of your configured cache backends from Django's [`CACHES`](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-CACHES) setting.

For example, to use Redis for caching component assets:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "component-media": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}

COMPONENTS = {
    # Use the Redis cache backend
    "cache": "component-media",
}
```

See [`COMPONENTS.cache`][ComponentsSettings.cache] for more details about this setting.

### Limits on JS and CSS variables

Each distinct value from [`get_js_data()`][Component.get_js_data] or [`get_css_data()`][Component.get_css_data] adds an entry to the cache. If those values depend on your users, the entries can keep adding up, so they have limits.

With the default in-memory cache, each server process keeps them for 24 hours after a render last used them, and uses at most 64 MiB of memory for them. When that memory is full, the process drops the entries that a render used longest ago. Your components' own [`Component.js`][Component.js] and [`Component.css`][Component.css] do not count toward this limit and are never dropped to make room.

You can change both limits:

```python
COMPONENTS = {
    # Keep the variables for a week
    "vars_cache_max_age": 7 * 24 * 60 * 60,
    # Allow up to 256 MiB in each server process
    "vars_cache_max_bytes": 256 * 1024 * 1024,
}
```

Both must be positive integers. Any other value raises a `ValueError` when Django starts.

If an entry is gone when a page needs it, that page's components miss their variables. A page that links the variables gets a 404 for that file. A render that produces the same variables stores them again.

With your own cache backend set in [`COMPONENTS.cache`][ComponentsSettings.cache], these two settings do not apply. That backend's own `TIMEOUT` and size limits decide how long entries stay, so set both. With `"TIMEOUT": None` and no limit on size, every new value adds an entry that stays for good.
