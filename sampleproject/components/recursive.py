import time
from typing import Any, Dict

from django_components import Component, register, types


@register("recursive")
class Recursive(Component):
    class View:
        def get(self, request):
            time_before = time.time()
            output = Recursive.render_to_response(
                request=request,
                kwargs={
                    "depth": 0,
                },
            )
            time_after = time.time()
            print("TIME: ", time_after - time_before)
            return output

    def get_context_data(self, depth: int = 0) -> Dict[str, Any]:
        return {"depth": depth + 1}

    template: types.django_html = """
        <div id="recursive">
            depth: {{ depth }}
            <hr/>
            {% if depth <= 100 %}
                {% component "recursive" depth=depth / %}
            {% endif %}
        </div>
    """
