import pytest
from django.template import Context, Template

from django_components import registry, types
from django_components.testing import djc_test


# Imported lazily, so we import components only once settings are set
def _create_components():
    from docs.examples.analytics.component import (  # noqa: PLC0415
        ApiWidget,
        SentryErrorTracker,
        SuccessRateTracker,
        analytics_events,
        error_rate,
    )

    registry.register("api_widget", ApiWidget)
    registry.register("sentry_error_tracker", SentryErrorTracker)
    registry.register("success_rate_tracker", SuccessRateTracker)
    analytics_events.clear()
    error_rate["error"] = 0
    error_rate["success"] = 0
    return analytics_events, error_rate


@pytest.mark.django_db
@djc_test
class TestAnalytics:
    def test_sentry_tracker_logs_only_errors(self):
        analytics_events, error_rate = _create_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% component "sentry_error_tracker" %}
                    {% component "api_widget" simulate_error=True / %}
                {% endcomponent %}
            {% endcomponent %}
            {% component "sentry_error_tracker" %}
                {% component "api_widget" simulate_error=False / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        template.render(Context({}))

        assert error_rate["error"] == 0
        assert error_rate["success"] == 0
        assert len(analytics_events) == 1
        assert analytics_events[0]["type"] == "error"
        assert analytics_events[0]["component"] == "sentry_error_tracker"
        assert analytics_events[0]["error"] is not None

    def test_success_rate_tracker_logs_all(self):
        analytics_events, error_rate = _create_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% component "success_rate_tracker" %}
                    {% component "api_widget" simulate_error=True / %}
                {% endcomponent %}
            {% endcomponent %}
            {% component "success_rate_tracker" %}
                {% component "api_widget" simulate_error=False / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        template.render(Context({}))

        assert len(analytics_events) == 0
        assert error_rate["error"] == 1
        assert error_rate["success"] == 1
