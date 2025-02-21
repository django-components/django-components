from typing import Optional

from django.core.cache import BaseCache, caches
from django.core.cache.backends.locmem import LocMemCache

from django_components.app_settings import app_settings
from django_components.util.cache import LRUCache

# This stores the parsed Templates. This is strictly local for now, as it stores instances.
# NOTE: Lazily initialized so it can be configured based on user-defined settings.
#
# TODO: Once we handle whole template parsing ourselves, this could store just
#       the parsed template AST (+metadata) instead of Template instances. In that case
#       we could open this up to be stored non-locally and shared across processes.
#       This would also allow us to remove our custom `LRUCache` implementation.
template_cache: Optional[LRUCache] = None

# This stores the inlined component JS and CSS files (e.g. `Component.js` and `Component.css`).
# We also store here the generated JS and CSS scripts that inject JS / CSS variables into the page.
component_media_cache: Optional[BaseCache] = None


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
                "TIMEOUT": None,  # No timeout
                "MAX_ENTRIES": None,  # No max size
                "CULL_FREQUENCY": 3,
            },
        )

    return component_media_cache
