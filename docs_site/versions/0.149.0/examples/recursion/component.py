from django_components import Component, register, types

DESCRIPTION = "100 nested components? Not a problem! Handle recursive rendering out of the box."


@register("recursion")
class Recursion(Component):
    class Kwargs:
        current_depth: int = 0

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        current_depth = kwargs.current_depth
        return {
            "current_depth": current_depth,
            "next_depth": current_depth + 1,
        }

    template: types.django_html = """
        {% load component_tags %}
        <div class="py-4 border-l-2 border-gray-300 ml-1">
            {% if current_depth < 100 %}
                <p class="text-sm text-gray-600">
                    Recursion depth: {{ current_depth }}
                </p>
                {% component "recursion" current_depth=next_depth / %}
            {% else %}
                <p class="text-sm font-semibold text-green-600">
                    Reached maximum recursion depth!
                </p>
            {% endif %}
        </div>
    """
