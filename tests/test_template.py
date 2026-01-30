from django.template import Template

from django_components import Component, cached_template, types
from django_components.template import _get_component_template
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


@djc_test
class TestTemplateCache:
    # TODO_v1 - Remove
    def test_cached_template(self):
        template_1 = cached_template("Variable: <strong>{{ variable }}</strong>")
        template_1._test_id = "123"

        template_2 = cached_template("Variable: <strong>{{ variable }}</strong>")

        assert template_2._test_id == "123"

    # TODO_v1 - Remove
    def test_cached_template_accepts_class(self):
        class MyTemplate(Template):
            pass

        template = cached_template("Variable: <strong>{{ variable }}</strong>", MyTemplate)
        assert isinstance(template, MyTemplate)

    # TODO_v1 - Move to `test_component.py`. While `cached_template()` will be removed,
    #           we will internally still cache templates by class, and we will want to test for that.
    def test_component_template_is_cached(self):
        class SimpleComponent(Component):
            def get_template(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

        comp = SimpleComponent(kwargs={"variable": "test"})

        # Check that we get the same template instance
        template_1 = _get_component_template(comp)
        template_1._test_id = "123"  # type: ignore[union-attr]

        template_2 = _get_component_template(comp)
        assert template_2._test_id == "123"  # type: ignore[union-attr]


@djc_test
class TestTemplateMonkeypatch:
    # See https://github.com/django-components/django-components/issues/1571
    def test_unpatched_template_class_is_patched_when_rendering_component(self):
        # Access the Template class and remove the internal attribute used to detect patching.
        # This simulates encountering Django's Template before django-components has patched it.
        if hasattr(Template, "_djc_patched"):
            delattr(Template, "_djc_patched")

        class SimpleComponent(Component):
            template = "Hello"

            def get_template_data(self, args, kwargs, slots, context):
                return {}

        # Render a component
        component = SimpleComponent()
        component.render()

        # The Template class should now have been patched (attribute restored).
        assert getattr(Template, "_djc_patched", False) is True
