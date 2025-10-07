from django.http import HttpRequest, HttpResponse

from django_components import Component, register, types

from .component import analytics_events, error_rate


class AnalyticsPage(Component):
    class Media:
        js = ("https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,container-queries",)

    template: types.django_html = """
        {% load component_tags %}
        <html>
            <head>
                <title>Analytics Example</title>
            </head>
            <body class="bg-gray-100 p-8">
                <div class="max-w-4xl mx-auto bg-white p-6 rounded-lg shadow-md">
                    <h1 class="text-2xl font-bold mb-4">
                        Component Analytics
                    </h1>
                    <p class="text-gray-600 mb-6">
                        Track component errors or success rates to send them
                        to Sentry or other services.
                    </p>

                    {# NOTE: Intentionally hidden so we focus on the events tracking #}
                    <div style="display: none;">
                        {% component "template_with_errors" / %}
                    </div>

                    {% component "captured_events" / %}
                </div>
            </body>
        </html>
    """

    class View:
        def get(self, request: HttpRequest) -> HttpResponse:
            # Clear events on each page load
            analytics_events.clear()
            error_rate["error"] = 0
            error_rate["success"] = 0

            return AnalyticsPage.render_to_response(request=request)


@register("template_with_errors")
class TemplateWithErrors(Component):
    template: types.django_html = """
        <div class="mb-8">
            <h2 class="text-xl font-semibold mb-2">
                Sentry Error Tracking
            </h2>
            <p class="text-sm text-gray-500 mb-2">
                This component only logs events when an error occurs.
            </p>
            {% component "error_fallback" %}
                {% component "sentry_error_tracker" %}
                    {% component "api_widget" simulate_error=True / %}
                {% endcomponent %}
            {% endcomponent %}
            {% component "sentry_error_tracker" %}
                {% component "api_widget" simulate_error=False / %}
            {% endcomponent %}
        </div>

        <div>
            <h2 class="text-xl font-semibold mb-2">
                Success Rate Analytics
            </h2>
            <p class="text-sm text-gray-500 mb-2">
                This component logs both successful and failed renders.
            </p>
            {% component "error_fallback" %}
                {% component "success_rate_tracker" %}
                    {% component "api_widget" simulate_error=True / %}
                {% endcomponent %}
            {% endcomponent %}
            {% component "success_rate_tracker" %}
                {% component "api_widget" simulate_error=False / %}
            {% endcomponent %}
        </div>
    """


# NOTE: Since this runs after `template_with_errors`,
#       the `analytics_events` will be populated.
@register("captured_events")
class CapturedEvents(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {"events": analytics_events, "error_rate": error_rate}

    template: types.django_html = """
        <div class="mt-8 p-4 border rounded-lg bg-gray-50">
            <h3 class="text-lg font-semibold mb-2">
                Captured Analytics Events
            </h3>
            <pre class="text-sm text-gray-700 whitespace-pre-wrap">
                {% for event in events %}
                    {{ event }}
                {% endfor %}
            </pre>
        </div>
        <div class="mt-8 p-4 border rounded-lg bg-gray-50">
            <h3 class="text-lg font-semibold mb-2">
                Error Rate
            </h3>
            <pre class="text-sm text-gray-700 whitespace-pre-wrap">
                {{ error_rate }}
            </pre>
            <p class="text-sm text-gray-500">
                {{ error_rate.error }} errors out of {{ error_rate.success }} calls.
            </p>
        </div>
    """
