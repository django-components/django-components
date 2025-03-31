This page describes the kinds of assets that django-components caches and how to configure the cache backends.

## Component caching

You can cache the output of your components by setting the [`Component.Cache`](../../reference/api.md#django_components.Component.Cache) options.

Read more about [Component caching](../../concepts/advanced/component_caching.md).

## Component's JS and CSS files

django-components simultaneously supports:

- Rendering and fetching components as HTML fragments
- Allowing components (even fragments) to have JS and CSS files associated with them
- Features like JS/CSS variables or CSS scoping

To achieve all this, django-components defines additional temporary JS and CSS files. These temporary files need to be stored somewhere, so that they can be fetched by the browser when the component is rendered as a fragment. And for that, django-components uses Django's cache framework.

This includes:

- Inlined JS/CSS defined via [`Component.js`](../../reference/api.md#django_components.Component.js) and [`Component.css`](../../reference/api.md#django_components.Component.css)
- JS/CSS variables generated from [`get_js_data()`](../../reference/api.md#django_components.Component.get_js_data) and [`get_css_data()`](../../reference/api.md#django_components.Component.get_css_data)

By default, django-components uses Django's local memory cache backend to store these assets. You can configure it to use any of your Django cache backends by setting the [`COMPONENTS.cache`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.cache) option in your settings:

```python
COMPONENTS = {
    # Name of the cache backend to use
    "cache": "my-cache-backend",
}
```

The value should be the name of one of your configured cache backends from Django's [`CACHES`](https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-CACHES) setting.

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

See [`COMPONENTS.cache`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.cache) for more details about this setting.
