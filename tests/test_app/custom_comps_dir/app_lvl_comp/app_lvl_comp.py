from django_components import Component, register


# Used for testing the template_loader
@register("custom_app_lvl_comp")
class AppLvlCompComponent(Component):
    template_file = "app_lvl_comp.html"

    class Media:
        js = "app_lvl_comp.js"
        css = "app_lvl_comp.css"

    def get_template_data(self, args, kwargs, slots, context):
        return {"variable": kwargs["variable"]}
