import pytest
from django.template import Context, Template

from django_components import registry, types
from django_components.testing import djc_test


def _import_components():
    from docs.examples.fragments.component import AlpineFragment, SimpleFragment  # noqa: PLC0415
    from docs.examples.fragments.page import FragmentsPage  # noqa: PLC0415

    registry.register("alpine_fragment", AlpineFragment)
    registry.register("simple_fragment", SimpleFragment)
    registry.register("fragments_page", FragmentsPage)


@pytest.mark.django_db
@djc_test
class TestFragments:
    def test_page_renders(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "fragments_page" / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assert "HTML Fragments" in rendered
        assert "Vanilla JS" in rendered
        assert "AlpineJS" in rendered
        assert "HTMX" in rendered

    def test_alpine_fragment_view(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "alpine_fragment" type="alpine" / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assert 'class="frag_alpine"' in rendered

    def test_simple_fragment_view(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "simple_fragment" type="plain" / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assert "Fragment with JS and CSS (plain)" in rendered
