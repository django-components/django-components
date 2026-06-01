import pytest
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import registry, types
from django_components.testing import djc_test


# Imported lazily, so we import it only once settings are set
def _create_tab_components() -> None:
    from docs.examples.tabs.component import Tab, Tablist, _TablistImpl  # noqa: PLC0415

    registry.register("Tab", Tab)
    registry.register("Tablist", Tablist)
    registry.register("_tabset", _TablistImpl)


@pytest.mark.django_db
@djc_test
class TestExampleTabs:
    def test_render_simple_tabs(self):
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

        assertHTMLEqual(
            rendered,
            """
            <div x-data="{
                selectedTab: 'my-tabs_tab-1_tab',
            }"
                id="my-tabs" data-djc-id-ca1bc4b>
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

    def test_disabled_tab(self):
        _create_tab_components()
        template_str: types.django_html = """
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

    def test_custom_ids(self):
        _create_tab_components()
        template_str: types.django_html = """
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

    def test_tablist_in_tab_raise_error(self):
        _create_tab_components()
        template_str: types.django_html = """
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

    def test_tab_in_tab_raise_error(self):
        _create_tab_components()
        template_str: types.django_html = """
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
