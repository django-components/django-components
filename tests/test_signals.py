from functools import wraps

from django.template import Context, Template

from django_components import Component, registry, types

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_file = "slotted_template.html"


def _get_templates_used_to_render(subject_template, render_context=None):
    """Emulate django.test.client.Client (see request method)."""
    from django.test.signals import template_rendered

    templates_used = []

    def receive_template_signal(sender, template, context, **_kwargs):
        templates_used.append(template.name)

    template_rendered.connect(receive_template_signal, dispatch_uid="test_method")
    subject_template.render(render_context or Context({}))
    template_rendered.disconnect(dispatch_uid="test_method")
    return templates_used


def with_template_signal(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Emulate Django test instrumentation for TestCase (see setup_test_environment)
        from django.test.utils import instrumented_test_render
        from django.template import Template

        original_template_render = Template._render
        Template._render = instrumented_test_render

        func(*args, **kwargs)

        Template._render = original_template_render

    return wrapper


@djc_test
class TestTemplateSignal:
    class InnerComponent(Component):
        template_file = "simple_template.html"

        def get_context_data(self, variable, variable2="default"):
            return {
                "variable": variable,
                "variable2": variable2,
            }

        class Media:
            css = "style.css"
            js = "script.js"

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    @with_template_signal
    def test_template_rendered(self, components_settings):
        registry.register("test_component", SlottedComponent)
        registry.register("inner_component", self.InnerComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}{% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = _get_templates_used_to_render(template)
        assert "slotted_template.html" in templates_used

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    @with_template_signal
    def test_template_rendered_nested_components(self, components_settings):
        registry.register("test_component", SlottedComponent)
        registry.register("inner_component", self.InnerComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}
              {% fill "header" %}
                {% component 'inner_component' variable='foo' %}{% endcomponent %}
              {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = _get_templates_used_to_render(template)
        assert "slotted_template.html" in templates_used
        assert "simple_template.html" in templates_used
