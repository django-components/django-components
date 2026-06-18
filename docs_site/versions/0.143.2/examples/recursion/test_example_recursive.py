import pytest
from django.template import Context, Template

from django_components import registry, types
from django_components.testing import djc_test


def _import_components():
    from docs.examples.recursion.component import Recursion  # noqa: PLC0415

    registry.register("recursion", Recursion)


@pytest.mark.django_db
@djc_test
class TestRecursion:
    def test_renders_recursively(self):
        _import_components()

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "recursion" / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # Expect 101 levels of depth (0 to 100)
        assert rendered.count("Recursion depth:") == 100
        assert "Reached maximum recursion depth!" in rendered
