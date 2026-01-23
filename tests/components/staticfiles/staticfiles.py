from typing import Any

from django_components import Component, register


# Used for testing the staticfiles finder in `test_staticfiles.py`
@register("staticfiles_component")
class RelativeFileWithPathObjComponent(Component):
    template_file = "staticfiles.html"

    class Media:
        js = "staticfiles.js"
        css = "staticfiles.css"

    def get_template_data(self, args, kwargs, slots, context) -> dict[str, Any]:
        return {"variable": kwargs["variable"]}
