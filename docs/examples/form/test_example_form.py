# ruff: noqa: S101,ANN201
import pytest
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import registry, types
from django_components.testing import djc_test


# Imported lazily, so we import components only once settings are set
def _create_form_components():
    from docs.examples.form.component import Form, FormLabel

    registry.register("form", Form)
    registry.register("form_label", FormLabel)


@pytest.mark.django_db
@djc_test
class TestExampleForm:
    def test_render_simple_form(self):
        _create_form_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "form" %}
              {% fill "field:project" %}<input name="project">{% endfill %}
              {% fill "field:option" %}<select name="option"></select>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <form method="post" data-djc-id-ca1bc41>
                <div>
                    <div class="grid grid-cols-[auto,1fr] gap-x-4 gap-y-2 items-center">
                        <label for="project" class="font-semibold text-gray-700" data-djc-id-ca1bc42>
                            Project
                        </label>
                        <input name="project">
                        <label for="option" class="font-semibold text-gray-700" data-djc-id-ca1bc43>
                            Option
                        </label>
                        <select name="option"></select>
                    </div>
                </div>
            </form>
            """,
        )

    def test_custom_label(self):
        _create_form_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "form" %}
              {% fill "label:project" %}<strong>Custom Project Label</strong>{% endfill %}
              {% fill "field:project" %}<input name="project">{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "<strong>Custom Project Label</strong>" in rendered
        assert '<label for="project"' not in rendered

    def test_unused_label_raises_error(self):
        _create_form_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "form" %}
              {% fill "label:project" %}Custom Project Label{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(ValueError, match=r"Unused labels: {'label:project'}"):
            template.render(Context({}))

    def test_prepend_append_slots(self):
        _create_form_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "form" %}
              {% fill "prepend" %}<div>Prepended content</div>{% endfill %}
              {% fill "field:project" %}<input name="project">{% endfill %}
              {% fill "append" %}<div>Appended content</div>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "<div>Prepended content</div>" in rendered
        assert "<div>Appended content</div>" in rendered
        assert rendered.find("Prepended content") < rendered.find("project")
        assert rendered.find("Appended content") > rendered.find("project")
