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
    from sampleproject.examples.components.tabs.tabs import Tab, Tablist, _TablistImpl

    # NOTE: We're importing the component classes from the sampleproject, so we're
    # testing the actual implementation.
    registry.register("Tab", Tab)
    registry.register("Tablist", Tablist)
    registry.register("_tabset", _TablistImpl)


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
class TestExampleTabs:
    def test_render_simple_tabs(self, components_settings):
        _create_tab_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "Tablist" name="My Tabs" %}
                {% component "Tab" header="Tab 1" %}Content 1{% endcomponent %}
                {% component "Tab" header="Tab 2" %}Content 2{% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        if components_settings["context_behavior"] == "django":
            comp_id = "ca1bc4b"
        else:
            comp_id = "ca1bc47"

        assertHTMLEqual(
            rendered,
            f"""
            <div x-data="{{ selectedTab: 'my-tabs_tab-1_tab' }}" id="my-tabs" data-djc-id-{comp_id}>
                <div role="tablist" aria-label="My Tabs">
                    <button
                        :aria-selected="selectedTab === 'my-tabs_tab-1_tab'"
                        @click="selectedTab = 'my-tabs_tab-1_tab'"
                        id="my-tabs_tab-1_tab"
                        role="tab"
                        aria-controls="my-tabs_tab-1_content">
                        Tab 1
                    </button>
                    <button
                        :aria-selected="selectedTab === 'my-tabs_tab-2_tab'"
                        @click="selectedTab = 'my-tabs_tab-2_tab'"
                        id="my-tabs_tab-2_tab"
                        role="tab"
                        aria-controls="my-tabs_tab-2_content">
                        Tab 2
                    </button>
                </div>
                <article
                    :hidden="selectedTab != 'my-tabs_tab-1_tab'"
                    role="tabpanel"
                    id="my-tabs_tab-1_content"
                    aria-labelledby="my-tabs_tab-1_tab">
                    Content 1
                </article>
                <article
                    :hidden="selectedTab != 'my-tabs_tab-2_tab'"
                    role="tabpanel"
                    id="my-tabs_tab-2_content"
                    aria-labelledby="my-tabs_tab-2_tab"
                    hidden>
                    Content 2
                </article>
            </div>
            """,
        )

    def test_disabled_tab(self, components_settings):
        _create_tab_components()
        template_str = """
            {% load component_tags %}
            {% component "Tablist" name="My Tabs" %}
                {% component "Tab" header="Tab 1" %}Content 1{% endcomponent %}
                {% component "Tab" header="Tab 2" disabled=True %}Content 2{% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "disabled" in rendered
        assert "Content 2" in rendered

    def test_custom_ids(self, components_settings):
        _create_tab_components()
        template_str = """
            {% load component_tags %}
            {% component "Tablist" id="custom-list" name="My Tabs" %}
                {% component "Tab" id="custom-tab" header="Tab 1" %}Content 1{% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert 'id="custom-list"' in rendered
        assert 'id="custom-tab_tab"' in rendered
        assert 'aria-controls="custom-tab_content"' in rendered
        assert 'id="custom-tab_content"' in rendered
        assert 'aria-labelledby="custom-tab_tab"' in rendered

    def test_tablist_in_tab_raise_error(self, components_settings):
        _create_tab_components()
        template_str = """
            {% load component_tags %}
            {% component "Tablist" name="Outer Tabs" %}
                {% component "Tab" header="Outer 1" %}
                    {% component "Tablist" name="Inner Tabs" %}
                        {% component "Tab" header="Inner 1" %}
                            Inner Content
                        {% endcomponent %}
                    {% endcomponent %}
                {% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)

        rendered = template.render(Context({}))

        assert "Inner Content" in rendered

    def test_tab_in_tab_raise_error(self, components_settings):
        _create_tab_components()
        template_str = """
            {% load component_tags %}
            {% component "Tablist" name="Outer Tabs" %}
                {% component "Tab" header="Outer 1" %}
                    {% component "Tab" header="Inner 1" %}
                        Inner Content
                    {% endcomponent %}
                {% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(RuntimeError, match="Component 'Tab' was called with no parent Tablist component"):
            template.render(Context({}))
