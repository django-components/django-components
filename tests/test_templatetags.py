"""Catch-all for tests that use template tags and don't fit other files"""

from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, registry, types
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


#######################
# TESTS
#######################


@djc_test
class TestMultilineTags:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_multiline_tags(self, components_settings):
        @register("test_component")
        class SimpleComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs["variable"],
                    "variable2": kwargs.get("variable2", "default"),
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component
                "test_component"
                variable=123
                variable2="abc"
            %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-ca1bc3f>123</strong>
        """
        assertHTMLEqual(rendered, expected)


@djc_test
class TestNestedTags:
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ var }}</strong>
        """

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "var": kwargs["var"],
            }

    # See https://github.com/django-components/django-components/discussions/671
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_tags(self, components_settings):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var="{% lorem 1 w %}" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-ca1bc3f>lorem</strong>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_quote_single(self, components_settings):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_("organisation's") %} {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-ca1bc3f>organisation&#x27;s</strong>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_quote_single_self_closing(self, components_settings):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_("organisation's") / %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-ca1bc3f>organisation&#x27;s</strong>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_quote_double(self, components_settings):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_('organisation"s') %} {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-ca1bc3f>organisation"s</strong>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_quote_double_self_closing(self, components_settings):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_('organisation"s') / %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong data-djc-id-ca1bc3f>organisation"s</strong>
        """
        assertHTMLEqual(rendered, expected)
