from django.template import Context, Template

from django_components import Component, cached_template, types

from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestTemplateCache:
    def test_cached_template(self):
        template_1 = cached_template("Variable: <strong>{{ variable }}</strong>")
        template_1._test_id = "123"

        template_2 = cached_template("Variable: <strong>{{ variable }}</strong>")

        assert template_2._test_id == "123"

    def test_cached_template_accepts_class(self):
        class MyTemplate(Template):
            pass

        template = cached_template("Variable: <strong>{{ variable }}</strong>", MyTemplate)
        assert isinstance(template, MyTemplate)

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

        comp = SimpleComponent()
        template_1 = comp._get_template(Context({}), component_id="123")
        template_1._test_id = "123"

        template_2 = comp._get_template(Context({}), component_id="123")
        assert template_2._test_id == "123"
