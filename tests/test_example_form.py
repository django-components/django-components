from pathlib import Path

import pytest
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import registry, types
from django_components.testing import djc_test
from tests.testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


# Instead of having to re-define the components from the examples section in documentation,
# we import them directly from sampleproject.
def _create_tab_components():
    # Imported lazily, so we import it only once settings are set
    from sampleproject.examples.components.form.form import Form, FormLabel

    # NOTE: We're importing the component classes from the sampleproject, so we're
    # testing the actual implementation.
    registry.register("form", Form)
    registry.register("form_label", FormLabel)


@djc_test(
    parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
    components_settings={
        "dirs": [
            Path(__file__).parent / "components",
            # Include the directory where example components are defined
            Path(__file__).parent.parent / "sampleproject/examples/components",
        ],
    },
)
class TestExampleForm:
    def test_render_simple_form(self, components_settings):
        _create_tab_components()
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

    def test_custom_label(self, components_settings):
        _create_tab_components()
        template_str = """
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

    def test_unused_label_raises_error(self, components_settings):
        _create_tab_components()
        template_str = """
            {% load component_tags %}
            {% component "form" %}
              {% fill "label:project" %}Custom Project Label{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(ValueError, match=r"Unused labels: {'label:project'}"):
            template.render(Context({}))

    def test_prepend_append_slots(self, components_settings):
        _create_tab_components()
        template_str = """
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
