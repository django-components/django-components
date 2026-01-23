from pathlib import Path

import django
from django.conf import settings

# Common use case in our tests is to check that the component works in both
# "django" and "isolated" context behaviors. If you need only that, pass this
# tuple to `djc_test` as the `parametrize` argument.
PARAMETRIZE_CONTEXT_BEHAVIOR = (
    ["components_settings"],
    [
        [{"context_behavior": "django"}],
        [{"context_behavior": "isolated"}],
    ],
    ["django", "isolated"],
)


def setup_test_config(
    components: dict | None = None,
    extra_settings: dict | None = None,
) -> None:
    if settings.configured:
        return

    default_settings = {
        "BASE_DIR": Path(__file__).resolve().parent,
        "INSTALLED_APPS": ("django_components", "tests.test_app"),
        "TEMPLATES": [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [
                    "tests/templates/",
                    "tests/components/",  # Required for template relative imports in tests
                ],
                "OPTIONS": {
                    "builtins": [
                        "django_components.templatetags.component_tags",
                    ],
                    "loaders": [
                        # Default Django loader
                        "django.template.loaders.filesystem.Loader",
                        # Including this is the same as APP_DIRS=True
                        "django.template.loaders.app_directories.Loader",
                        # Components loader
                        "django_components.template_loader.Loader",
                    ],
                },
            },
        ],
        "COMPONENTS": {
            "autodiscover": False,
            **(components or {}),
        },
        "MIDDLEWARE": [],
        "DATABASES": {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            },
        },
        "SECRET_KEY": "secret",
        "ROOT_URLCONF": "django_components.urls",
    }

    settings.configure(
        **{
            **default_settings,
            **(extra_settings or {}),
        },
    )

    django.setup()
