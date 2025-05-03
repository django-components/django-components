from django_components import Component, register


# Used for testing the template_loader
@register("nested_app_lvl_comp")
class AppLvlCompComponent(Component):
    template = """
        {{ variable }}
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {"variable": kwargs["variable"]}
