import sys
import time
from collections import OrderedDict
from threading import Lock, RLock
from typing import Any

from django.core.cache import BaseCache, caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.locmem import LocMemCache

from django_components.app_settings import app_settings
from django_components.util.cache import LRUCache
from django_components.util.logger import logger

# TODO_V2 - Remove, won't be needed once we remove `get_template_string()`, `get_template_name()`, `get_template()`
#
# This stores the parsed Templates. This is strictly local for now, as it stores instances.
# NOTE: Lazily initialized so it can be configured based on user-defined settings.
template_cache: LRUCache | None = None

# This stores the inlined component JS and CSS files (e.g. `Component.js` and `Component.css`).
# There is one entry per script of each component class, so it does not need a limit.
component_media_cache: BaseCache | None = None

# This stores the generated JS and CSS scripts that inject JS / CSS variables into the page.
# There is one entry per distinct set of values, and those values can come from your users,
# so unlike the cache above it has limits. It is separate so that many new values can
# push out only other variables, never the JS and CSS that every page of a component needs.
component_vars_cache: BaseCache | None = None
_component_vars_cache_lock = Lock()

# What one stored entry costs on top of its two strings, whose own size `sys.getsizeof()` gives:
# the tuple that holds the value, its expiry time and size, and the entry's slot in the dictionary.
# Counting this means that many tiny entries use up the byte limit too.
_VARS_ENTRY_OVERHEAD_BYTES = 256


class ComponentVarsCache(BaseCache):
    """
    An in-memory cache with a limit on the age of its entries, and on the bytes they use.

    Django's `LocMemCache` can limit only the number of entries, which does not limit
    the memory, because a single value can be of any size.

    `has_key()` is what we call before we link an entry into a page, so here it also counts
    as a use. It resets the entry's age and makes it the last one to be dropped.
    Without this, an entry in steady use would expire every so often right after a page linked it.
    `get()` does not do this, so that requests for a file cannot keep it stored.

    Single-process only, like `LocMemCache`. Holds strings only, as it measures just the top-level
    object that it is given.
    """

    def __init__(self, max_age: int, max_bytes: int) -> None:
        super().__init__({"TIMEOUT": max_age})
        self._max_bytes = max_bytes
        self._total_bytes = 0
        # Reentrant, so that `add()` can make its check and its write one step.
        self._lock = RLock()
        # Maps a key to (value, expiry time, size). The order is the order of last use, oldest first.
        # All our entries live equally long, so that is also the order in which they expire.
        self._entries: OrderedDict[str, tuple[Any, float | None, int]] = OrderedDict()

    def _is_expired(self, expires_at: float | None) -> bool:
        return expires_at is not None and expires_at <= time.time()

    def _remove(self, key: str) -> None:
        """Remove an entry, keeping the byte count right. The caller must hold the lock."""
        entry = self._entries.pop(key, None)
        if entry is not None:
            self._total_bytes -= entry[2]

    def _remove_expired(self) -> None:
        """Remove what has expired, even though nothing reads it. The caller must hold the lock."""
        while self._entries:
            key, (_, expires_at, _) = next(iter(self._entries.items()))
            if not self._is_expired(expires_at):
                break
            self._remove(key)

    def _get_live_entry(self, key: str) -> tuple[Any, float | None, int] | None:
        """Get an entry unless it has expired. The caller must hold the lock."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        if self._is_expired(entry[1]):
            self._remove(key)
            return None
        return entry

    def add(self, key: Any, value: Any, timeout: Any = DEFAULT_TIMEOUT, version: int | None = None) -> bool:
        cache_key = self.make_and_validate_key(key, version=version)
        with self._lock:
            if self._get_live_entry(cache_key) is not None:
                return False
            self.set(key, value, timeout=timeout, version=version)
            return True

    def get(self, key: Any, default: Any = None, version: int | None = None) -> Any:
        cache_key = self.make_and_validate_key(key, version=version)
        with self._lock:
            entry = self._get_live_entry(cache_key)
        return default if entry is None else entry[0]

    def set(self, key: Any, value: Any, timeout: Any = DEFAULT_TIMEOUT, version: int | None = None) -> None:
        cache_key = self.make_and_validate_key(key, version=version)
        expires_at = self.get_backend_timeout(timeout)
        # `getsizeof()` gives the memory really used, which `len()` does not. One character above
        # U+00FF makes the whole string take 2 or 4 bytes per character.
        size = sys.getsizeof(cache_key) + sys.getsizeof(value) + _VARS_ENTRY_OVERHEAD_BYTES

        with self._lock:
            # A rewrite replaces the old value, so its bytes leave the count first.
            self._remove(cache_key)
            self._remove_expired()
            is_too_large = size > self._max_bytes
            if not is_too_large:
                self._entries[cache_key] = (value, expires_at, size)
                self._total_bytes += size
                while self._total_bytes > self._max_bytes:
                    self._remove(next(iter(self._entries)))

        # An entry over the whole limit could be kept only by emptying the store, and it still
        # would not fit. So we leave the store as it is, and tell the app author why variables
        # are missing. The message gives only sizes, so that it does not repeat the data.
        if is_too_large:
            logger.warning(
                f"JS or CSS variables of about {size} bytes were not stored, as that is more than "
                f"COMPONENTS.vars_cache_max_bytes ({self._max_bytes}). Components that use them will miss them."
            )

    def touch(self, key: Any, timeout: Any = DEFAULT_TIMEOUT, version: int | None = None) -> bool:
        cache_key = self.make_and_validate_key(key, version=version)
        expires_at = self.get_backend_timeout(timeout)
        with self._lock:
            entry = self._get_live_entry(cache_key)
            if entry is None:
                return False
            self._entries[cache_key] = (entry[0], expires_at, entry[2])
            self._entries.move_to_end(cache_key)
            return True

    def has_key(self, key: Any, version: int | None = None) -> bool:
        return self.touch(key, version=version)

    def delete(self, key: Any, version: int | None = None) -> bool:
        cache_key = self.make_and_validate_key(key, version=version)
        with self._lock:
            is_stored = cache_key in self._entries
            self._remove(cache_key)
        return is_stored

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._total_bytes = 0


# TODO_V2 - Remove, won't be needed once we remove `get_template_string()`, `get_template_name()`, `get_template()`
def get_template_cache() -> LRUCache:
    global template_cache  # noqa: PLW0603
    if template_cache is None:
        template_cache = LRUCache(maxsize=app_settings.TEMPLATE_CACHE_SIZE)

    return template_cache


def get_component_media_cache() -> BaseCache:
    if app_settings.CACHE is not None:
        return caches[app_settings.CACHE]

    # If no cache is set, use a local memory cache.
    global component_media_cache  # noqa: PLW0603
    if component_media_cache is None:
        component_media_cache = LocMemCache(
            "django-components-media",
            {
                # No max size nor timeout. There is one entry per script of each component class.
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


def get_component_vars_cache() -> BaseCache:
    """Get the cache for the scripts generated from `get_js_data()` and `get_css_data()`."""
    if app_settings.CACHE is not None:
        return caches[app_settings.CACHE]

    # If no cache is set, use a local memory cache with limits.
    global component_vars_cache  # noqa: PLW0603
    if component_vars_cache is None:
        # Two threads of a new process could get here together, and whatever the
        # one that lost the race stored would be gone, so the page would miss it.
        with _component_vars_cache_lock:
            if component_vars_cache is None:
                component_vars_cache = ComponentVarsCache(
                    max_age=app_settings.VARS_CACHE_MAX_AGE,
                    max_bytes=app_settings.VARS_CACHE_MAX_BYTES,
                )

    return component_vars_cache
