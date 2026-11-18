import base64
import hashlib
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

# Taken from the shipped file, so that rebuilding the runtime does not touch every test
_CORE_JS_PATH = (
    Path(__file__).parent.parent / "src/django_components/static/django_components/django_components.min.js"
)
_CORE_JS_HASH = hashlib.sha384(_CORE_JS_PATH.read_bytes())
CORE_JS_INTEGRITY = "sha384-" + base64.b64encode(_CORE_JS_HASH.digest()).decode()
CORE_JS_URL = f"django_components/django_components.min.js?v={_CORE_JS_HASH.hexdigest()[:12]}"

# How the runtime appears in a document
CORE_JS_TAG = f'<script src="{CORE_JS_URL}" integrity="{CORE_JS_INTEGRITY}" crossorigin="anonymous"></script>'

# How the runtime appears in a fragment
CORE_JS_LOADER = f"""
    <script>(function() {{
        const current = Object.getOwnPropertyDescriptor(Document.prototype, "currentScript").get.call(document);
        if (!Object.prototype.hasOwnProperty.call(globalThis, "DjangoComponents")) {{
            const s = document.createElement('script');
            s.src = "{CORE_JS_URL}";
            s.integrity = "{CORE_JS_INTEGRITY}";
            s.crossOrigin = "anonymous";
            if (current && current.nonce) s.nonce = current.nonce;
            document.head.appendChild(s);
        }}
        // Remove this loader script
        if (current) current.remove();
    }})();</script>
"""


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
