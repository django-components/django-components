from typing import Optional

from django_components import Component, register


# Used for testing the template_loader
@register("app_lvl_comp")
class AppLvlCompComponent(Component):
    template_file: Optional[str] = "app_lvl_comp.html"
    js_file = "app_lvl_comp.js"
    css_file = "app_lvl_comp.css"

    class Media:
        js = "app_lvl_comp.js"
        css = "app_lvl_comp.css"

    def get_template_data(self, args, kwargs, slots, context):
        return {"variable": kwargs["variable"]}
