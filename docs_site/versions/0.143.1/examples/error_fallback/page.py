from django.http import HttpRequest, HttpResponse
from django.utils.safestring import mark_safe

from django_components import Component, types


class ErrorFallbackPage(Component):
    class Media:
        js = (
            mark_safe(
                '<script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp,container-queries"></script>'
            ),
        )

    template: types.django_html = """
        {% load component_tags %}
        <html>
            <head>
                <title>ErrorFallback Example</title>
            </head>
            <body class="bg-gray-100 p-8">
                <div class="max-w-2xl mx-auto bg-white p-6 rounded-lg shadow-md">
                    <h1 class="text-2xl font-bold mb-4">Weather API Widget Example</h1>
                    <p class="text-gray-600 mb-6">
                        This example demonstrates using ErrorFallback to handle potential API failures gracefully.
                    </p>

                    <div class="mb-8">
                        <h2 class="text-xl font-semibold mb-2">Case 1: API call is successful</h2>
                        {% component "error_fallback" %}
                            {% fill "content" %}
                                {% component "weather_widget" location="New York" / %}
                            {% endfill %}
                            {% fill "fallback" %}
                                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                                    <strong class="font-bold">Error:</strong>
                                    <span class="block sm:inline">Could not load weather data.</span>
                                </div>
                            {% endfill %}
                        {% endcomponent %}
                    </div>

                    <div>
                        <h2 class="text-xl font-semibold mb-2">Case 2: API call fails</h2>
                        {% component "error_fallback" %}
                            {% fill "content" %}
                                {% component "weather_widget" location="Atlantis" simulate_error=True / %}
                            {% endfill %}
                            {% fill "fallback" %}
                                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                                    <strong class="font-bold">Error:</strong>
                                    <span class="block sm:inline">
                                        Could not load weather data for
                                        <strong>Atlantis</strong>.
                                        The location may not be supported or the service is temporarily down.
                                    </span>
                                </div>
                            {% endfill %}
                        {% endcomponent %}
                    </div>
                </div>
            </body>
        </html>
    """  # noqa: E501

    class View:
        def get(self, request: HttpRequest) -> HttpResponse:
            return ErrorFallbackPage.render_to_response(request=request)
