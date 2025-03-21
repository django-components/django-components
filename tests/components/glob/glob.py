
from django_components import Component


# The Media JS / CSS glob and are relative to the component directory
class GlobComponent(Component):
    template = """
        {% load component_tags %}
        {% component_js_dependencies %}
        {% component_css_dependencies %}
    """

    class Media:
        css = "glob_*.css"
        js = "glob_*.js"


# The Media JS / CSS glob and are relative to the directory given in
# `COMPONENTS.dirs` and `COMPONENTS.app_dirs`
class GlobComponentRootDir(GlobComponent):
    class Media:
        css = "glob/glob_*.css"
        js = "glob/glob_*.js"
