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

# Source for the generated /releases/ pages (one page per "## vX.Y.Z" section)
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"

# Where runnable examples live
EXAMPLES_DIR = REPO_ROOT / "docs_site" / "examples"

# Pre-built static directories copied verbatim into the built site (skipping the
# markdown pipeline) at their mount path. The asv benchmark report is already
# HTML, so it's a passthrough rather than rendered content: `benchmarks/report/`
# (asv's `html_dir`) is served at `/benchmarks/`, matching the old mkdocs layout.
# Each entry is (source_dir, mount_path_relative_to_site_root).
STATIC_PASSTHROUGHS = [
    (REPO_ROOT / "benchmarks" / "report", "benchmarks"),
]

# Base URL for the published docs site on GitHub Pages
SITE_URL = "https://django-components.github.io/django-components"

# Google Search Console site-verification token (rendered as a
# <meta name="google-site-verification"> tag in every page's <head>). Ported
# from the old mkdocs setup's `extra.google_site_verification`. Set to "" to
# omit the tag.
GOOGLE_SITE_VERIFICATION = "vQA3d50F2ByQxG0eB6b0YoPnYW9gZo8xnd6HKhCyuys"

# GitHub repository, used to build "See source code" links in the API reference
# (the old mkdocs setup read this from mkdocs.yml's `repo_url`). The branch is
# the ref those links point at.
REPO_URL = "https://github.com/django-components/django-components"
SOURCE_CODE_GIT_BRANCH = "master"

# Default output directory for built HTML (gitignored; mirrors mkdocs' site_dir).
# This is the everyday dev-build / preview default; at deploy CI assembles the
# committed version snapshots (VERSIONS_DIR) into site/v/* alongside it.
SITE_DIR = REPO_ROOT / "site"

# Committed per-version snapshots: docs_site/versions/<version>/, plus a sibling
# versions.json manifest and redirect stubs for aliases (latest/). `docs-build
# --docs-version X` writes the snapshot here; the deploy mounts it at /v/X/.
# (Supersedes the spike's docs/v/ target per DESIGN.md section 4.0a.)
VERSIONS_DIR = BASE_DIR / "versions"

# Config for `docs-build-all` (which tags to rebuild): pattern, include/exclude,
# oldest/newest bounds, latest alias. Lives at the docs-project root.
VERSIONS_CONFIG = BASE_DIR / "docs_versions.toml"

# Phase 5c (feature 5c.12): deprecation date for the legacy dotted-path API
# anchors (`#django_components.X`), which are emitted as aliases so old inbound
# links keep resolving. Set this to (cutover date + 12 months) AT cutover. After
# it, the `anchor_deprecation` guard fails the build on any content source still
# using the long-form anchor, so internal usages get migrated before the aliases
# are removed (a deliberate manual step). None = timer not started (guard
# dormant). Example: `import datetime; ANCHOR_ALIAS_DEPRECATION_DATE = datetime.date(2027, 6, 1)`.
ANCHOR_ALIAS_DEPRECATION_DATE = None
