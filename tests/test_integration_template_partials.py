"""
Tests for template_partials integration with django-components.

See https://github.com/django-components/django-components/issues/1327
and https://github.com/django-components/django-components/issues/1323.

This file can be deleted after Django 5.2 reached end of life.
See https://github.com/django-components/django-components/issues/1323#issuecomment-3163478287.
"""

from typing import NamedTuple

import pytest
from django.http import HttpRequest
from django.shortcuts import render

from django_components import Component, register
from django_components.testing import djc_test

from .testutils import setup_test_config

try:
    from template_partials.templatetags.partials import TemplateProxy
except ImportError:
    TemplateProxy = None


setup_test_config()


# Test compatibility with django-template-partials.
# See https://github.com/django-components/django-components/issues/1323#issuecomment-3156654329
@djc_test(django_settings={"INSTALLED_APPS": ("template_partials", "django_components", "tests.test_app")})
class TestTemplatePartialsIntegration:
    @pytest.mark.skipif(TemplateProxy is None, reason="template_partials not available")
    def test_render_partial(self):
        @register("calendar")
        class Calendar(Component):
            template = """
                <div class="calendar-component">
                    <div>Today's date is <span>{{ date }}</span></div>
                </div>
            """
            css = """
                .calendar-component { width: 200px; background: pink; }
                .calendar-component span { font-weight: bold; }
            """
            js = """
                (function(){
                    if (document.querySelector(".calendar-component")) {
                        document.querySelector(".calendar-component").onclick = function(){ alert("Clicked calendar!"); };
                    }
                })()
            """  # noqa: E501

            class Kwargs(NamedTuple):
                date: str

            def get_template_data(self, args, kwargs: Kwargs, slots, context):
                return {
                    "date": kwargs.date,
                }

        # NOTE: When a full template is rendered (without the `#` syntax), the output should be as usual.
        request = HttpRequest()
        result = render(request, "integration_template_partials.html")
        content = result.content

        assert b"<!-- _RENDERED" not in content
        assert b"width: 200px;" in content
        assert b'alert("Clicked calendar!")' in content

        # NOTE: When a partial is rendered with the `#` syntax, what *actually*
        # gets rendered is `TemplateProxy` from template_partials, instead of Django's own `Template` class.
        # Hence, the monkeypatching that we've done on the Template class does NOT apply to TemplateProxy.
        # So we want to check that the result HAS its CSS/JS processed, which means that the monkeypatching
        # works as expected.
        request2 = HttpRequest()
        result2 = render(request2, "integration_template_partials.html#test___partial")
        content2 = result2.content

        assert b"<!-- _RENDERED" not in content2
        assert b"width: 200px;" in content2
        assert b'alert("Clicked calendar!")' in content2
