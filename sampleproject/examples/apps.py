from django.apps import AppConfig

from .utils import discover_example_modules


# This adds finds all examples defined in `docs/examples/` and for each of them
# adds a URL that renders that example's live demo. These are available under
# `http://localhost:8000/examples/<example_name>`.
#
# Overview of all examples is available under `http://localhost:8000/examples/`.
class ExamplesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "examples"

    def ready(self):
        # Auto-discover and register example components and pages
        discover_example_modules()
