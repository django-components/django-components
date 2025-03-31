import time
from typing import Any

from django.core.cache import caches

from django_components import Component
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


# Common settings for all tests
@djc_test(
    django_settings={
        "CACHES": {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            },
        },
    },
)
class TestComponentCache:
    def test_cache_enabled(self):
        did_call_get = False

        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True

            def get_context_data(self, **kwargs: Any):
                nonlocal did_call_get
                did_call_get = True
                return {}

        # First render
        component = TestComponent()
        result = component.render()

        assert did_call_get
        assert result == "Hello"

        # Check if the cache entry is set
        cache_key = component.cache.get_cache_key()
        assert cache_key == "components:cache:TestComponent_c9770f::"
        assert component.cache.get_entry(cache_key) == "<!-- _RENDERED TestComponent_c9770f,a1bc3e,, -->Hello"
        assert caches["default"].get(cache_key) == "<!-- _RENDERED TestComponent_c9770f,a1bc3e,, -->Hello"

        # Second render
        did_call_get = False
        component.render()

        # get_context_data not called because the cache entry was returned
        assert not did_call_get
        assert result == "Hello"

    def test_cache_disabled(self):
        did_call_get = False

        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = False

            def get_context_data(self, **kwargs: Any):
                nonlocal did_call_get
                did_call_get = True
                return {}

        # First render
        component = TestComponent()
        result = component.render()

        assert did_call_get
        assert result == "Hello"

        # Check if the cache entry is not set
        cache_instance = component.cache
        cache_key = cache_instance.get_cache_key()
        assert cache_instance.get_entry(cache_key) is None

        # Second render
        did_call_get = False
        result = component.render()

        # get_context_data IS called because the cache is NOT used
        assert did_call_get
        assert result == "Hello"

    def test_cache_ttl(self):
        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True
                ttl = 0.1  # .1 seconds TTL

        component = TestComponent()
        component.render()

        cache_instance = component.cache
        cache_key = cache_instance.get_cache_key()
        assert cache_instance.get_entry(cache_key) == "<!-- _RENDERED TestComponent_42aca9,a1bc3e,, -->Hello"

        # Wait for TTL to expire
        time.sleep(0.2)

        assert cache_instance.get_entry(cache_key) is None

    @djc_test(
        django_settings={
            "CACHES": {
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "default",
                },
                "custom": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "custom",
                },
            },
        },
    )
    def test_custom_cache_name(self):
        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True
                cache_name = "custom"

        component = TestComponent()
        component.render()

        assert component.cache.get_cache() is caches["custom"]
        assert (
            component.cache.get_entry("components:cache:TestComponent_90ef7a::")
            == "<!-- _RENDERED TestComponent_90ef7a,a1bc3e,, -->Hello"
        )  # noqa: E501

    def test_cache_by_input(self):
        class TestComponent(Component):
            template = "Hello {{ input }}"

            class Cache:
                enabled = True

            def get_context_data(self, input, **kwargs: Any):
                return {"input": input}

        component = TestComponent()
        component.render(
            kwargs={"input": "world"},
        )

        component.render(
            kwargs={"input": "cake"},
        )

        # Check if the cache entry is set
        cache = caches["default"]
        assert len(cache._cache) == 2
        assert (
            component.cache.get_entry("components:cache:TestComponent_648b95::input:world")
            == "<!-- _RENDERED TestComponent_648b95,a1bc3e,, -->Hello world"
        )  # noqa: E501
        assert (
            component.cache.get_entry("components:cache:TestComponent_648b95::input:cake")
            == "<!-- _RENDERED TestComponent_648b95,a1bc3f,, -->Hello cake"
        )  # noqa: E501

    def test_cache_input_hashing(self):
        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True

        component = TestComponent()
        component.render(args=(1, 2), kwargs={"key": "value"})

        # The key consists of `component._class_hash`, hashed args, and hashed kwargs
        expected_key = "TestComponent_52dd91:1-2:key:value"
        assert component.cache.hash_input(1, 2, key="value") == expected_key

    def test_override_hash_methods(self):
        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True

                def hash_args(self, args):
                    # Custom hash method for args
                    return "custom-args"

                def hash_kwargs(self, kwargs):
                    # Custom hash method for kwargs
                    return "custom-kwargs"

            def get_context_data(self, *args, **kwargs: Any):
                return {}

        component = TestComponent()
        component.render(args=(1, 2), kwargs={"key": "value"})

        # The key should use the custom hash methods
        expected_key = "components:cache:TestComponent_28880f:custom-args:custom-kwargs"
        assert component.cache.get_cache_key(1, 2, key="value") == expected_key
