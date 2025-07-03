import sys
from typing import Optional

from django.core.cache import BaseCache, caches
from django.core.cache.backends.locmem import LocMemCache

from django_components.app_settings import app_settings
from django_components.util.cache import LRUCache

# TODO_V1 - Remove, won't be needed once we remove `get_template_string()`, `get_template_name()`, `get_template()`
#
# This stores the parsed Templates. This is strictly local for now, as it stores instances.
# NOTE: Lazily initialized so it can be configured based on user-defined settings.
template_cache: Optional[LRUCache] = None

# This stores the inlined component JS and CSS files (e.g. `Component.js` and `Component.css`).
# We also store here the generated JS and CSS scripts that inject JS / CSS variables into the page.
component_media_cache: Optional[BaseCache] = None


# TODO_V1 - Remove, won't be needed once we remove `get_template_string()`, `get_template_name()`, `get_template()`
def get_template_cache() -> LRUCache:
    global template_cache
    if template_cache is None:
        template_cache = LRUCache(maxsize=app_settings.TEMPLATE_CACHE_SIZE)

    return template_cache


def get_component_media_cache() -> BaseCache:
    if app_settings.CACHE is not None:
        return caches[app_settings.CACHE]

    # If no cache is set, use a local memory cache.
    global component_media_cache
    if component_media_cache is None:
        component_media_cache = LocMemCache(
            "django-components-media",
            {
                # No max size nor timeout
                # NOTE: Implementation of `BaseCache` coerces the `MAX_ENTRIES` value
                #       to `int()` so we use exact max size instead of `inf` or `None`.
                #       See https://github.com/django/django/blob/94ebcf8366d62f6360851b40e9c4dfe3f71d202f/django/core/cache/backends/base.py#L73  # noqa: E501
                "TIMEOUT": None,
                "OPTIONS": {
                    "MAX_ENTRIES": sys.maxsize,
                },
            },
        )

    return component_media_cache
