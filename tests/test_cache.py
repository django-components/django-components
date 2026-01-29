import base64

from django_components import Component, register
from django_components.testing import djc_test
from django_components.util.cache import LRUCache

from .testutils import setup_test_config

setup_test_config()


@djc_test
class TestCache:
    def test_cache(self):
        cache = LRUCache[int](maxsize=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3

        cache.set("d", 4)

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

        cache.set("e", 5)
        cache.set("f", 6)

        assert cache.get("b") is None
        assert cache.get("c") is None
        assert cache.get("d") == 4
        assert cache.get("e") == 5
        assert cache.get("f") == 6

        cache.clear()

        assert cache.get("d") is None
        assert cache.get("e") is None
        assert cache.get("f") is None

    def test_cache_maxsize_zero(self):
        cache = LRUCache[int](maxsize=0)

        cache.set("a", 1)
        assert cache.get("a") is None

        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("b") is None
        assert cache.get("c") is None

        # Same with negative numbers
        cache = LRUCache[int](maxsize=-1)
        cache.set("a", 1)
        assert cache.get("a") is None

        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("b") is None
        assert cache.get("c") is None


@djc_test
class TestComponentMediaCache:
    @djc_test(
        components_settings={"cache": "test-cache"},
        django_settings={
            "CACHES": {
                # See https://docs.djangoproject.com/en/5.2/topics/cache/#local-memory-caching
                "test-cache": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "test-cache",
                    "TIMEOUT": None,  # No timeout
                    "OPTIONS": {
                        "MAX_ENTRIES": 10_000,
                    },
                },
            },
        },
    )
    def test_component_media_caching(self):
        from django.core.cache import caches

        test_cache = caches["test-cache"]

        @register("test_simple")
        class TestSimpleComponent(Component):
            template = """
                <div>Template only component</div>
            """

        @register("test_media_no_vars")
        class TestMediaNoVarsComponent(Component):
            template = """
                <div>Template and JS component</div>
                {% component "test_simple" / %}
            """
            js = "console.log('Hello from JS');"
            css = ".novars-component { color: blue; }"

        class TestMediaAndVarsComponent(Component):
            template = """
                <div>Full component</div>
                {% component "test_media_no_vars" / %}
            """
            js = "console.log('Hello from full component');"
            css = ".full-component { color: blue; }"

            def get_js_data(self, args, kwargs, slots, context):
                return {"message": "Hello"}

            def get_css_data(self, args, kwargs, slots, context):
                return {"color": "blue"}

        # Check that JS/CSS is cached for components that have them
        assert test_cache.has_key(f"__components:{TestMediaAndVarsComponent.class_id}:js")
        assert test_cache.has_key(f"__components:{TestMediaAndVarsComponent.class_id}:css")
        assert test_cache.has_key(f"__components:{TestMediaNoVarsComponent.class_id}:js")
        assert test_cache.has_key(f"__components:{TestMediaNoVarsComponent.class_id}:css")
        assert not test_cache.has_key(f"__components:{TestSimpleComponent.class_id}:js")
        assert not test_cache.has_key(f"__components:{TestSimpleComponent.class_id}:css")

        # Check that we cache `Component.js` / `Component.css`
        assert test_cache.get(f"__components:{TestMediaNoVarsComponent.class_id}:js").strip() == (
            '{"kind": "component", '
            '"url": null, '
            '"content": "console.log(\'Hello from JS\');", '
            '"attrs": {}, '
            '"origin_class_id": "TestMediaNoVarsComponent_0fa819"}'
        )
        assert test_cache.get(f"__components:{TestMediaNoVarsComponent.class_id}:css").strip() == (
            '{"kind": "component", '
            '"url": null, '
            '"content": ".novars-component { color: blue; }", '
            '"attrs": {}, '
            '"origin_class_id": "TestMediaNoVarsComponent_0fa819"}'
        )

        # Render the components to trigger caching of JS/CSS variables from `get_js_data` / `get_css_data`
        TestMediaAndVarsComponent.render()

        # Check that we cache JS / CSS scripts generated from `get_js_data` / `get_css_data`
        # NOTE: The hashes is generated from the data.
        js_vars_hash = "216ecc"
        css_vars_hash = "d039a3"

        # Verify CSS variables are cached
        css_vars_content = test_cache.get(f"__components:{TestMediaAndVarsComponent.class_id}:css:{css_vars_hash}")
        assert css_vars_content is not None
        assert css_vars_content.strip() != ""
        # Verify the CSS contains the variable definition
        assert "--color: blue;" in css_vars_content
        assert f"[data-djc-css-{css_vars_hash}]" in css_vars_content

        # Verify JS variables are cached
        js_vars_content = test_cache.get(f"__components:{TestMediaAndVarsComponent.class_id}:js:{js_vars_hash}")
        assert js_vars_content is not None
        assert js_vars_content.strip() != ""
        # Verify the JS contains the JSON data
        assert base64.b64encode(b'{"message": "Hello"}').decode() in js_vars_content
