
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


# The Media JS / CSS are NOT globs and are relative to the directory given in
# `COMPONENTS.dirs` and `COMPONENTS.app_dirs`. These should NOT be modified.
class NonGlobComponentRootDir(Component):
    template = """
        {% load component_tags %}
        {% component_js_dependencies %}
        {% component_css_dependencies %}
    """

    class Media:
        css = "glob/glob_1.css"
        js = "glob/glob_1.js"


# The Media JS / CSS are NOT globs. While relative to the directory given in
# `COMPONENTS.dirs` and `COMPONENTS.app_dirs`, these files do not exist.
# These paths should NOT be modified.
class NonGlobNonexistComponentRootDir(Component):
    template = """
        {% load component_tags %}
        {% component_js_dependencies %}
        {% component_css_dependencies %}
    """

    class Media:
        css = "glob/glob_nonexist.css"
        js = "glob/glob_nonexist.js"


# The Media JS / CSS are NOT globs, but URLs.
class UrlComponent(Component):
    template = """
        {% load component_tags %}
        {% component_js_dependencies %}
        {% component_css_dependencies %}
    """

    class Media:
        css = [
            "https://cdnjs.cloudflare.com/example/style.min.css",
            "http://cdnjs.cloudflare.com/example/style.min.css",
            # :// is not a valid URL - will be resolved as static path
            "://cdnjs.cloudflare.com/example/style.min.css",
            "/path/to/style.css",
        ]
        js = [
            "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.0.2/chart.min.js",
            "http://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.0.2/chart.min.js",
            # :// is not a valid URL - will be resolved as static path
            "://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.0.2/chart.min.js",
            "/path/to/script.js",
        ]
