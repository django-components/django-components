from typing import Dict, List

from django_components import Component, register, types

DESCRIPTION = "Track component errors or success rates to send them to Sentry or other services."

# A mock analytics service
analytics_events: List[Dict] = []
error_rate = {
    "error": 0,
    "success": 0,
}


@register("api_widget")
class ApiWidget(Component):
    class Kwargs:
        simulate_error: bool = False

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        if kwargs.simulate_error:
            raise ConnectionError("API call failed")
        return {"data": "Mock API response data"}

    template: types.django_html = """
        <div class="p-4 border rounded-lg bg-gray-50">
            <h4 class="font-bold text-gray-800">API Widget</h4>
            <p class="text-gray-600">Data: {{ data }}</p>
        </div>
    """


@register("sentry_error_tracker")
class SentryErrorTracker(Component):
    def on_render_after(self, context, template, result, error):
        if error:
            event = {
                "type": "error",
                "component": self.registered_name,
                "error": error,
            }
            analytics_events.append(event)
            print(f"SENTRY: Captured error in component {self.registered_name}: {error}")

    template: types.django_html = """
        {% load component_tags %}
        {% slot "default" / %}
    """


@register("success_rate_tracker")
class SuccessRateTracker(Component):
    def on_render_after(self, context, template, result, error):
        # Track error
        if error:
            error_rate["error"] += 1
        # Track success
        else:
            error_rate["success"] += 1

    template: types.django_html = """
        {% load component_tags %}
        {% slot "default" / %}
    """
