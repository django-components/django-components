import pytest
from django.template import Context, Template

from django_components import registry, types
from django_components.testing import djc_test


# Imported lazily, so we import components only once settings are set
def _create_components():
    from docs.examples.error_fallback.component import WeatherWidget  # noqa: PLC0415

    registry.register("weather_widget", WeatherWidget)


@pytest.mark.django_db
@djc_test
class TestExampleWeatherWidget:
    def test_renders_successfully(self):
        _create_components()

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% fill "content" %}
                    {% component "weather_widget" location="New York" / %}
                {% endfill %}
                {% fill "fallback" %}
                    Error!
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "Weather in New York" in rendered
        assert "Error!" not in rendered

    def test_renders_fallback_on_error(self):
        _create_components()

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% fill "content" %}
                    {% component "weather_widget" location="Atlantis" simulate_error=True / %}
                {% endfill %}
                {% fill "fallback" %}
                    <p>Weather service unavailable.</p>
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "Weather in Atlantis" not in rendered
        assert "Weather service unavailable." in rendered
