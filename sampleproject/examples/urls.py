import importlib

from django.urls import path

from django_components.component import Component

from .utils import discover_example_modules
from .views import ExamplesIndexPage


# For each example in `docs/examples/*`, register a URL pattern that points to the example's view.
# The example will be available at `http://localhost:8000/examples/<example_name>`.
# The view is the first Component class that we find in example's `page.py` module.
#
# So if we have an example called `form`:
# 1. We look for a module `examples.dynamic.form.page`,
# 2. We find the first Component class in that module (in this case `FormPage`),
# 3. We register a URL pattern that points to that view (in this case `http://localhost:8000/examples/form`).
def get_example_urls():
    # First, ensure all example modules are discovered and imported
    examples_names = discover_example_modules()

    urlpatterns = [
        # Index page that lists all examples
        path("examples/", ExamplesIndexPage.as_view(), name="examples_index"),
    ]
    for example_name in examples_names:
        try:
            # Import the page module (should already be loaded by discover_example_modules)
            module_name = f"examples.dynamic.{example_name}.page"
            module = importlib.import_module(module_name)

            # Find the view class (assume it's the first Component class)
            view_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if issubclass(attr, Component) and attr_name != "Component":
                    view_class = attr
                    break

            if not view_class:
                raise ValueError(f"No Component class found in {module_name}")

            # Make the example availble under localhost:8000/examples/<example_name>
            url_pattern = f"examples/{example_name}"
            view_name = example_name

            urlpatterns.append(path(url_pattern, view_class.as_view(), name=view_name))
            print(f"Registered URL: {url_pattern} -> {view_class.__name__}")

        except Exception as e:  # noqa: BLE001
            print(f"Failed to register URL for {example_name}: {e}")

    return urlpatterns


urlpatterns = get_example_urls()
