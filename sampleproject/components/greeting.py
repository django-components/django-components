from typing import Any, Dict

from django_components import component
from django_components import types as t


@component.register("greeting")
class Greeting(component.Component):
    def get(self, request, *args, **kwargs):
        slots = {"message": "Hello, world!"}
        context = {"name": request.GET.get("name", "")}
        return self.render_to_response(context, slots)

    def get_context_data(self, *args, **kwargs) -> Dict[str, Any]:
        # NOTE: Because of MyPy in Python v3.6, arg `name` cannot be declared as separate variable
        name = args[0]
        return {"name": name}

    template: t.django_html = """
        <div id="greeting">Hello, {{ name }}!</div>
        {% slot "message" %}{% endslot %}
    """

    css: t.css = """
        #greeting {
            display: inline-block;
            color: blue;
            font-size: 2em;
        }
    """

    js: t.js = """
        document.getElementById("greeting").addEventListener("click", (event) => {
            alert("Hello!");
        });
    """
