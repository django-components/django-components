This page describes the kinds of assets that django-components caches and how to configure the cache backends.

## Component's JS and CSS files

django-components caches the JS and CSS files associated with your components. This enables components to be rendered as HTML fragments and still having the associated JS and CSS files loaded with them.

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
