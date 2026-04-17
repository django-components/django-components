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
