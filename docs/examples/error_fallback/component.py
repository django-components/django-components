import random
from typing import NamedTuple

from django_components import Component, register, types

DESCRIPTION = "A component that catches errors and displays fallback content, similar to React's ErrorBoundary."


@register("weather_widget")
class WeatherWidget(Component):
    class Kwargs(NamedTuple):
        location: str
        simulate_error: bool = False

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        if kwargs.simulate_error:
            raise OSError(f"Failed to connect to weather service for '{kwargs.location}'.")

        return {
            "location": kwargs.location,
            "temperature": f"{random.randint(10, 30)}°C",
            "condition": random.choice(["Sunny", "Cloudy", "Rainy"]),
        }

    template: types.django_html = """
        <div class="bg-white rounded-lg shadow-md p-6">
            <h3 class="text-xl font-semibold text-gray-800 mb-2">
                Weather in {{ location }}
            </h3>
            <p class="text-gray-600">
                <strong class="font-medium text-gray-700">Temperature:</strong>
                {{ temperature }}
            </p>
            <p class="text-gray-600">
                <strong class="font-medium text-gray-700">Condition:</strong>
                {{ condition }}
            </p>
        </div>
    """
