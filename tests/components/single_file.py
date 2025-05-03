from typing import Any, Dict

from django.http import HttpResponse

from django_components import Component, register, types


@register("single_file_component")
class SingleFileComponent(Component):
    template: types.django_html = """
        <form method="post">
            {% csrf_token %}
            <input type="text" name="variable" value="{{ variable }}">
            <input type="submit">
        </form>
        """

    class View:
        def post(self, request, *args, **kwargs) -> HttpResponse:
            variable = request.POST.get("variable")
            return SingleFileComponent.render_to_response(
                request=request,
                kwargs={"variable": variable},
            )

        def get(self, request, *args, **kwargs) -> HttpResponse:
            return SingleFileComponent.render_to_response(
                request=request,
                kwargs={"variable": "GET"},
            )

    def get_template_data(self, args, kwargs, slots, context) -> Dict[str, Any]:
        return {"variable": kwargs["variable"]}
