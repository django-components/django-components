import gc
import re
import time
import weakref

import pytest
from django.core.cache import caches
from django.template import Template
from django.template.context import Context

from django_components import Component, register
from django_components.extension import ComponentExtension, OnComponentInputContext
from django_components.extension import extensions as extension_manager
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


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

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_get
                did_call_get = True

        # First render
        component = TestComponent()
        result = component.render()

        assert did_call_get
        assert result == "Hello"

        # Check if the cache entry is set
        cache_key = component.cache.get_cache_key([], {}, {})
        assert cache_key == "components:cache:c98bf483e9a1937732d4542c714462ac"
        assert component.cache.get_entry(cache_key) == "<!-- _RENDERED TestComponent_c9770f,ca1bc3f,, -->Hello"
        assert caches["default"].get(cache_key) == "<!-- _RENDERED TestComponent_c9770f,ca1bc3f,, -->Hello"

        # Second render
        did_call_get = False
        component.render()

        # get_template_data not called because the cache entry was returned
        assert not did_call_get
        assert result == "Hello"

    def test_cache_disabled(self):
        did_call_get = False

        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = False

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_get
                did_call_get = True

        # First render
        component = TestComponent()
        result = component.render()

        assert did_call_get
        assert result == "Hello"

        # Check if the cache entry is not set
        cache_instance = component.cache
        cache_key = cache_instance.get_cache_key([], {}, {})
        assert cache_instance.get_entry(cache_key) is None

        # Second render
        did_call_get = False
        result = component.render()

        # get_template_data IS called because the cache is NOT used
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
        cache_key = cache_instance.get_cache_key([], {}, {})
        assert cache_instance.get_entry(cache_key) == "<!-- _RENDERED TestComponent_42aca9,ca1bc3f,, -->Hello"

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
            component.cache.get_entry("components:cache:bcb4b049d8556e06871b39e0e584e452")
            == "<!-- _RENDERED TestComponent_90ef7a,ca1bc3f,, -->Hello"
        )

    def test_cache_by_input(self):
        class TestComponent(Component):
            template = "Hello {{ input }}"

            class Cache:
                enabled = True

            def get_template_data(self, args, kwargs, slots, context):
                return {"input": kwargs["input"]}

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
            component.cache.get_entry("components:cache:3535e1d1e5f6fa5bc521e7fe203a68d0")
            == "<!-- _RENDERED TestComponent_648b95,ca1bc3f,, -->Hello world"
        )
        assert (
            component.cache.get_entry("components:cache:a98a8bd5e72a544d7601798d5e777a77")
            == "<!-- _RENDERED TestComponent_648b95,ca1bc40,, -->Hello cake"
        )

    def test_cache_input_hashing(self):
        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True

        component = TestComponent()
        component.render(args=(1, 2), kwargs={"key": "value"})

        # The key consists of `component.class_id`, hashed args, and hashed kwargs
        expected_key = "1,2:key-value"
        assert component.cache.hash([1, 2], {"key": "value"}) == expected_key

    def test_override_hash_methods(self):
        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True

                def hash(self, *args, **kwargs):
                    # Custom hash method for args and kwargs
                    return "custom-args-and-kwargs"

        component = TestComponent()
        component.render(args=(1, 2), kwargs={"key": "value"})

        # The key should use the custom hash methods
        expected_key = "components:cache:3d54974c467a578c509efec189b0d14b"
        assert component.cache.get_cache_key([1, 2], {"key": "value"}, {}) == expected_key
        assert component.cache.get_entry(expected_key) == "<!-- _RENDERED TestComponent_28880f,ca1bc3f,, -->Hello"

    def test_cached_component_inside_include(self):
        @register("test_component")
        class TestComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True

        template = Template(
            """
            {% extends "component_inside_include_base.html" %}
            {% block content %}
                THIS_IS_IN_ACTUAL_TEMPLATE_SO_SHOULD_NOT_BE_OVERRIDDEN
            {% endblock %}
        """,
        )

        result = template.render(Context({}))
        assert "THIS_IS_IN_BASE_TEMPLATE_SO_SHOULD_BE_OVERRIDDEN" not in result
        assert "THIS_IS_IN_ACTUAL_TEMPLATE_SO_SHOULD_NOT_BE_OVERRIDDEN" in result

        result_cached = template.render(Context({}))
        assert "THIS_IS_IN_BASE_TEMPLATE_SO_SHOULD_BE_OVERRIDDEN" not in result_cached
        assert "THIS_IS_IN_ACTUAL_TEMPLATE_SO_SHOULD_NOT_BE_OVERRIDDEN" in result_cached

    def test_cache_slots__fills(self):
        @register("test_component")
        class TestComponent(Component):
            template = "Hello {{ input }} <div>{% slot 'content' default / %}</div>"

            class Cache:
                enabled = True
                include_slots = True

            def get_template_data(self, args, kwargs, slots, context):
                return {"input": kwargs["input"]}

        Template(
            """
            {% component "test_component" input="cake" %}
                ONE
            {% endcomponent %}
        """,
        ).render(Context({}))

        Template(
            """
            {% component "test_component" input="cake" %}
                ONE
            {% endcomponent %}
        """,
        ).render(Context({}))

        # Check if the cache entry is set
        component = TestComponent()
        cache = caches["default"]

        assert len(cache._cache) == 1
        assert (
            component.cache.get_entry("components:cache:87b9e27abdd3c6ef70982d065fc836a9")
            == '<!-- _RENDERED TestComponent_dd1dee,ca1bc3f,, -->Hello cake <div data-djc-id-ca1bc3f="">\n                ONE\n            </div>'  # noqa: E501
        )

        Template(
            """
            {% component "test_component" input="cake" %}
                TWO
            {% endcomponent %}
        """,
        ).render(Context({}))

        assert len(cache._cache) == 2
        assert (
            component.cache.get_entry("components:cache:1d7e3a58972550cf9bec18f457fb1a61")
            == '<!-- _RENDERED TestComponent_dd1dee,ca1bc45,, -->Hello cake <div data-djc-id-ca1bc45="">\n                TWO\n            </div>'  # noqa: E501
        )

    def test_cache_slots__strings(self):
        class TestComponent(Component):
            template = "Hello {{ input }} <div>{% slot 'content' default / %}</div>"

            class Cache:
                enabled = True
                include_slots = True

            def get_template_data(self, args, kwargs, slots, context):
                return {"input": kwargs["input"]}

        TestComponent.render(
            kwargs={"input": "cake"},
            slots={"content": "ONE"},
        )
        TestComponent.render(
            kwargs={"input": "cake"},
            slots={"content": "ONE"},
        )

        # Check if the cache entry is set
        component = TestComponent()
        cache = caches["default"]

        assert len(cache._cache) == 1
        assert (
            component.cache.get_entry("components:cache:362766726cd0e991f33b0527ef8a513c")
            == '<!-- _RENDERED TestComponent_34b6d1,ca1bc3e,, -->Hello cake <div data-djc-id-ca1bc3e="">ONE</div>'
        )

        TestComponent.render(
            kwargs={"input": "cake"},
            slots={"content": "TWO"},
        )

        assert len(cache._cache) == 2
        assert (
            component.cache.get_entry("components:cache:468e3f122ac305cff5d9096a3c548faf")
            == '<!-- _RENDERED TestComponent_34b6d1,ca1bc42,, -->Hello cake <div data-djc-id-ca1bc42="">TWO</div>'
        )

    def test_cache_slots_raises_on_func(self):
        class TestComponent(Component):
            template = "Hello {{ input }} <div>{% slot 'content' default / %}</div>"

            class Cache:
                enabled = True
                include_slots = True

            def get_template_data(self, args, kwargs, slots, context):
                return {"input": kwargs["input"]}

        with pytest.raises(
            TypeError,
            match=re.escape(
                "Cannot hash slot 'content' of component 'TestComponent' - Slot functions are unhashable.",
            ),
        ):
            TestComponent.render(
                kwargs={"input": "cake"},
                slots={"content": lambda _ctx: "ONE"},
            )


class ShortCircuitExtension(ComponentExtension):
    """
    Test extension that short-circuits the render from `on_component_input`, and records
    weakrefs to the components it sees so a test can assert they are garbage-collected.

    Because user extensions are always ordered after the built-in `CacheExtension`, this
    reproduces the scenario where `CacheExtension.on_component_input` has already run (and
    stored its key) but `on_component_rendered` never fires for the component.
    """

    name = "short_circuit"

    def __init__(self) -> None:
        self.seen_component_refs: list[weakref.ReferenceType] = []

    def on_component_input(self, ctx: OnComponentInputContext) -> str:
        self.seen_component_refs.append(weakref.ref(ctx.component))
        return "SHORT_CIRCUITED"


@djc_test(
    django_settings={
        "CACHES": {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            },
        },
    },
)
class TestCacheRenderKeyLifecycle:
    def test_error_does_not_cache(self):
        class ErrorComponent(Component):
            template = "Hello"

            class Cache:
                enabled = True

            def on_render(self, context, template):
                raise ValueError("deliberate error")

        with pytest.raises(ValueError, match="deliberate error"):
            ErrorComponent.render()

        # Nothing should have been written to the cache on the error path.
        assert len(caches["default"]._cache) == 0  # type: ignore[attr-defined]

    @djc_test(components_settings={"extensions": [ShortCircuitExtension]})
    def test_no_leak_when_later_extension_short_circuits(self):
        """
        Regression test for the leak where `CacheExtension.on_component_input` stored a key
        on a cache miss, but a later extension short-circuited the render so
        `on_component_rendered` never ran to release it.

        The key now lives on the per-component-instance config, so it must be released
        together with the component. We assert that by checking the component instances are
        garbage-collected.
        """

        class TestComponent(Component):
            template = "Hello {{ name }}"

            class Cache:
                enabled = True

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "world")}

        short_circuit_ext = None
        for ext in extension_manager.extensions:
            if isinstance(ext, ShortCircuitExtension):
                short_circuit_ext = ext
                break
        assert short_circuit_ext is not None

        for i in range(5):
            output = TestComponent.render(kwargs={"name": f"n{i}"})
            assert output == "SHORT_CIRCUITED"

        # The extension saw all 5 components on a cache miss (CacheExtension ran first and
        # stashed a key on each component's config).
        assert len(short_circuit_ext.seen_component_refs) == 5

        gc.collect()

        # None of the components (and thus none of the stashed cache keys) are retained.
        assert all(ref() is None for ref in short_circuit_ext.seen_component_refs)
