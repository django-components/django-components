"""Django settings for the docs site builder.

This is a minimal Django project that exists to:
1. Render markdown docs pages through the 3-pass pipeline (fence-protect -> Django -> markdown -> layout)
2. Provide a runserver for live preview during docs authoring
3. Eventually be crawled by build_docs to produce a static site for GitHub Pages

It intentionally has no database, no auth, no admin, no middleware -
only what's needed to run Django's template engine and django-components.
"""

import secrets
from pathlib import Path

from django_components import ComponentsSettings

# docs_site/docs_site/settings.py -> docs_site/
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = secrets.token_hex(32)

DEBUG = True

ALLOWED_HOSTS: list[str] = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django_components",
    "apps.docs",  # the docs app (components, templatetags, management commands)
]

# No middleware needed - we don't serve HTTP requests in production
# (the site is pre-rendered to static HTML)
MIDDLEWARE: list[str] = []

ROOT_URLCONF = "docs_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                        "django_components.template_loader.Loader",
                    ],
                )
            ],
            # Make component_tags available everywhere without {% load %}
            "builtins": [
                "django_components.templatetags.component_tags",
            ],
        },
    },
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django_components.finders.ComponentsFileSystemFinder",
]

WSGI_APPLICATION = "docs_site.wsgi.application"

# No database - this project only renders templates
DATABASES: dict = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tell django-components where to find the docs site's components
COMPONENTS = ComponentsSettings(
    autodiscover=True,
    dirs=[BASE_DIR / "apps" / "docs" / "components"],
)

# Where markdown source files live (the "content directory")
CONTENT_DIR = BASE_DIR / "content"

# The repo root (one level above docs_site/)
REPO_ROOT = BASE_DIR.parent

# Where runnable examples live (docs_old/examples/ until Phase 6 cutover)
EXAMPLES_DIR = REPO_ROOT / "docs_old" / "examples"

# Base URL for the published docs site on GitHub Pages
SITE_URL = "https://django-components.github.io/django-components"

# Default output directory for built HTML (gitignored; mirrors mkdocs' site_dir).
# The versioned deploy target (docs/v/<version>/) is set explicitly via --output
# by the release workflow; this is just the everyday dev-build default.
SITE_DIR = REPO_ROOT / "site"
