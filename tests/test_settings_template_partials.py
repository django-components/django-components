"""Test settings for template_partials integration tests."""

from .testutils import *  # noqa

# Add template_partials to INSTALLED_APPS for this test
INSTALLED_APPS = list(INSTALLED_APPS)
try:
    import template_partials  # noqa
    if 'template_partials' not in INSTALLED_APPS:
        INSTALLED_APPS.append('template_partials')
except ImportError:
    pass

INSTALLED_APPS = tuple(INSTALLED_APPS)