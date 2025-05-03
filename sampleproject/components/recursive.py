import time
from typing import NamedTuple

from django_components import Component, register, types


@register("recursive")
class Recursive(Component):
    template: types.django_html = """
        <div id="recursive">
            depth: {{ depth }}
            <hr/>
            {% if depth <= 100 %}
                {% component "recursive" depth=depth / %}
            {% endif %}
        </div>
    """

    class Kwargs(NamedTuple):
        depth: int

    class Defaults:
        depth = 0

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {"depth": kwargs.depth + 1}

    class View:
        def get(self, request):
            time_before = time.time()
            output = Recursive.render_to_response(
                request=request,
                kwargs=Recursive.Kwargs(
                    depth=0,
                ),
            )
            time_after = time.time()
            print("TIME: ", time_after - time_before)
            return output
