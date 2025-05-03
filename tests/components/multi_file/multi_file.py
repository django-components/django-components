from typing import Any, Dict

from django.http import HttpResponse

from django_components import Component, register


@register("multi_file_component")
class MultFileComponent(Component):
    template_file = "multi_file/multi_file.html"

    class View:
        def post(self, request, *args, **kwargs) -> HttpResponse:
            variable = request.POST.get("variable")
            return MultFileComponent.render_to_response(
                request=request,
                kwargs={"variable": variable},
            )

        def get(self, request, *args, **kwargs) -> HttpResponse:
            return MultFileComponent.render_to_response(
                request=request,
                kwargs={"variable": "GET"},
            )

    def get_template_data(self, args, kwargs, slots, context) -> Dict[str, Any]:
        return {"variable": kwargs["variable"]}
