from typing import Any, Dict

from django.http import HttpResponse

from django_components import Component, register


@register("relative_file_component")
class RelativeFileComponent(Component):
    template_file = "relative_file.html"

    class Media:
        js = "relative_file.js"
        css = "relative_file.css"

    class View:
        def post(self, request, *args, **kwargs) -> HttpResponse:
            variable = request.POST.get("variable")
            return RelativeFileComponent.render_to_response(
                request=request,
                kwargs={"variable": variable},
            )

        def get(self, request, *args, **kwargs) -> HttpResponse:
            return RelativeFileComponent.render_to_response(
                request=request,
                kwargs={"variable": "GET"},
            )

    def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
        return {"variable": variable}
