"""
Tests for django-components' compatibility with Django's built-in {% cache %} tag.

When a template loads {% load component_tags %}, the {% cache %} tag is replaced
with a component-aware version (DjcCacheNode) that stores fully-assembled HTML
rather than Pass-1 placeholders.  See src/django_components/cache_tag.py for the
full explanation of why this is necessary.
"""

from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, registry, types
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


@djc_test(
    django_settings={
        "CACHES": {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            },
            "altcache": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            },
        },
    },
)
class TestCacheTagCompatibility:
    def test_toplevel_component_works(self):
        """
        {% cache %} wrapping a {% component %} at the top level of a plain template
        (no parent component) stores and returns complete HTML on both miss and hit.
        """
        render_count = 0

        class SimpleComponent(Component):
            template: types.django_html = "<b>hello</b>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {}

        registry.register("simple", SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% cache 500 "toplevel" %}
                {% component "simple" / %}
            {% endcache %}
        """

        first = Template(template_str).render(Context({}))
        assert render_count == 1
        assertHTMLEqual(first, '<b data-djc-id-ca1bc3f="">hello</b>')

        second = Template(template_str).render(Context({}))
        assert render_count == 1, "Component should not re-render on cache hit"
        assertHTMLEqual(second, '<b data-djc-id-ca1bc3f="">hello</b>')

    def test_nested_component_cache_miss(self):
        """
        On a cache miss, {% cache %} inside a component template renders its body
        with _COMPONENT_CONTEXT_KEY cleared, so the inner {% component %} acts as
        a render root and returns complete assembled HTML.
        """

        class InnerComponent(Component):
            template: types.django_html = "<span>inner</span>"

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% cache 500 "nested_miss" %}
                        {% component "inner" / %}
                    {% endcache %}
                </div>
            """

        registry.register("inner", InnerComponent)
        registry.register("outer", OuterComponent)

        rendered = Template('{% load component_tags %}{% component "outer" / %}').render(Context({}))
        assertHTMLEqual(
            rendered,
            '<div data-djc-id-ca1bc3f=""><span data-djc-id-ca1bc41="">inner</span></div>',
        )

    def test_nested_component_cache_hit(self):
        """
        On a cache HIT, {% cache %} returns the stored complete HTML directly.
        OuterComponent's Pass-2 assembly succeeds and the inner component's HTML
        is present in the output without re-executing InnerComponent.
        """
        render_count = 0

        class InnerComponent(Component):
            template: types.django_html = "<span>inner</span>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {}

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% cache 500 "nested_hit" %}
                        {% component "inner" / %}
                    {% endcache %}
                </div>
            """

        registry.register("inner", InnerComponent)
        registry.register("outer", OuterComponent)

        outer_tpl = Template('{% load component_tags %}{% component "outer" / %}')

        first = outer_tpl.render(Context({}))
        assert render_count == 1, "InnerComponent should render on cache miss"
        assertHTMLEqual(
            first,
            '<div data-djc-id-ca1bc3f=""><span data-djc-id-ca1bc41="">inner</span></div>',
        )

        second = outer_tpl.render(Context({}))
        assert render_count == 1, "InnerComponent should NOT re-render on cache hit"
        # OuterComponent gets a fresh render_id each time (it is not cached itself),
        # so its data-djc-id changes between renders.  The inner span comes from the
        # cache and is identical to the first render.
        assert '<span data-djc-id-ca1bc41="">inner</span>' in second

    def test_nested_component_cache_hit_with_explicit_cache_load(self):
        """
        Explicitly loading Django's `cache` library after `component_tags` should
        still use the component-aware cache implementation.
        """
        render_count = 0

        class InnerComponent(Component):
            template: types.django_html = "<span>inner</span>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {}

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags cache %}
                <div>
                    {% cache 500 "nested_hit_explicit_cache" %}
                        {% component "inner_explicit_cache" / %}
                    {% endcache %}
                </div>
            """

        registry.register("inner_explicit_cache", InnerComponent)
        registry.register("outer_explicit_cache", OuterComponent)

        outer_tpl = Template('{% load component_tags %}{% component "outer_explicit_cache" / %}')

        first = outer_tpl.render(Context({}))
        assert render_count == 1
        assertHTMLEqual(
            first,
            '<div data-djc-id-ca1bc3f=""><span data-djc-id-ca1bc41="">inner</span></div>',
        )

        second = outer_tpl.render(Context({}))
        assert render_count == 1, "InnerComponent should NOT re-render on cache hit"
        assert '<span data-djc-id-ca1bc41="">inner</span>' in second

    def test_cache_with_slot_inside_component(self):
        """
        Caching a fragment that contains {% slot %} should preserve the component
        context while rendering the cache body.
        """

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% cache 500 "slot_fragment" %}
                        {% slot "content" default %}fallback{% endslot %}
                    {% endcache %}
                </div>
            """

        registry.register("outer_slot_cache", OuterComponent)

        template = Template(
            """
            {% load component_tags %}
            {% component "outer_slot_cache" %}
                {% fill "content" %}HELLO{% endfill %}
            {% endcomponent %}
            """
        )

        first = template.render(Context({}))
        assert "HELLO" in first

        second = template.render(Context({}))
        assert "HELLO" in second

    def test_expire_time_as_variable(self):
        """
        expire_time can be a context variable rather than a literal integer.
        The component should still be cached correctly.
        """
        render_count = 0

        class SimpleComponent(Component):
            template: types.django_html = "<b>hello</b>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {}

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% cache timeout "expire_var" %}
                    {% component "simple" / %}
                {% endcache %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"timeout": 500}

        registry.register("simple", SimpleComponent)
        registry.register("outer", OuterComponent)

        tpl = Template('{% load component_tags %}{% component "outer" / %}')

        first = tpl.render(Context({}))
        assert render_count == 1
        assert "<b" in first
        assert "hello" in first

        tpl.render(Context({}))
        assert render_count == 1, "Component should not re-render on cache hit"

    def test_expire_time_none(self):
        """
        expire_time=None means cache indefinitely (no timeout).
        The component should be cached and not re-render on a subsequent call.
        """
        render_count = 0

        class SimpleComponent(Component):
            template: types.django_html = "<b>forever</b>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {}

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% cache None "expire_none" %}
                    {% component "simple" / %}
                {% endcache %}
            """

        registry.register("simple", SimpleComponent)
        registry.register("outer", OuterComponent)

        tpl = Template('{% load component_tags %}{% component "outer" / %}')

        first = tpl.render(Context({}))
        assert render_count == 1
        assert "forever" in first

        tpl.render(Context({}))
        assert render_count == 1, "Component should not re-render when cached with no timeout"

    def test_vary_on_single_variable(self):
        """
        A single vary_on variable causes separate cache entries per unique value.
        Each distinct value renders the component once; repeating a value hits the cache.
        """
        render_count = 0

        class GreetComponent(Component):
            template: types.django_html = "<span>{{ name }}</span>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {"name": kwargs["name"]}

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% cache 500 "vary_single" user %}
                    {% component "greet" name=user / %}
                {% endcache %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"user": kwargs["user"]}

        registry.register("greet", GreetComponent)
        registry.register("outer", OuterComponent)

        tpl = Template('{% load component_tags %}{% component "outer" user=user / %}')

        tpl.render(Context({"user": "alice"}))
        assert render_count == 1

        tpl.render(Context({"user": "bob"}))
        assert render_count == 2, "Different vary_on value should cause a cache miss"

        tpl.render(Context({"user": "alice"}))
        assert render_count == 2, "Repeated vary_on value should hit the cache"

        tpl.render(Context({"user": "bob"}))
        assert render_count == 2, "Repeated vary_on value should hit the cache"

    def test_vary_on_multiple_variables(self):
        """
        Multiple vary_on variables all participate in the cache key.
        Only the exact same combination of values is a cache hit.
        """
        render_count = 0

        class ItemComponent(Component):
            template: types.django_html = "<li>{{ lang }}/{{ section }}</li>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {"lang": kwargs["lang"], "section": kwargs["section"]}

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% cache 500 "vary_multi" lang section %}
                    {% component "item" lang=lang section=section / %}
                {% endcache %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"lang": kwargs["lang"], "section": kwargs["section"]}

        registry.register("item", ItemComponent)
        registry.register("outer", OuterComponent)

        tpl = Template('{% load component_tags %}{% component "outer" lang=lang section=section / %}')

        tpl.render(Context({"lang": "en", "section": "home"}))
        assert render_count == 1

        tpl.render(Context({"lang": "en", "section": "about"}))
        assert render_count == 2, "Different second vary_on value should miss"

        tpl.render(Context({"lang": "fr", "section": "home"}))
        assert render_count == 3, "Different first vary_on value should miss"

        tpl.render(Context({"lang": "en", "section": "home"}))
        assert render_count == 3, "Same combination should hit the cache"

    def test_using_named_cache_backend(self):
        """
        using="altcache" routes storage to the named cache backend.
        The component should still be cached and not re-render on a hit.
        """
        render_count = 0

        class SimpleComponent(Component):
            template: types.django_html = "<b>alt</b>"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal render_count
                render_count += 1
                return {}

        class OuterComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% cache 500 "using_alt" using="altcache" %}
                    {% component "simple" / %}
                {% endcache %}
            """

        registry.register("simple", SimpleComponent)
        registry.register("outer", OuterComponent)

        tpl = Template('{% load component_tags %}{% component "outer" / %}')

        first = tpl.render(Context({}))
        assert render_count == 1
        assert "alt" in first

        tpl.render(Context({}))
        assert render_count == 1, "Component should not re-render on cache hit via named backend"
