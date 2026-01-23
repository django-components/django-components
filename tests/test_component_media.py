# ruff: noqa: E501
import os
import re
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media
from django.template import Context, Template
from django.templatetags.static import static
from django.utils.html import format_html, html_safe
from django.utils.safestring import mark_safe
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import Component, autodiscover, registry, render_dependencies, types
from django_components.component_media import UNSET, ComponentMedia
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


# "Main media" refer to the HTML, JS, and CSS set on the Component class itself
# (as opposed via the `Media` class). These have special handling in the Component.
@djc_test
class TestMainMedia:
    def test_html_js_css_inlined(self):
        class TestComponent(Component):
            template = dedent(
                """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
                <div class='html-css-only'>Content</div>
                """,
            )
            css = ".html-css-only { color: blue; }"
            js = "console.log('HTML and JS only');"

        assert TestComponent.css == ".html-css-only { color: blue; }"
        assert TestComponent.js == "console.log('HTML and JS only');"

        rendered = TestComponent.render()

        assertInHTML(
            '<div class="html-css-only" data-djc-id-ca1bc3e>Content</div>',
            rendered,
        )
        assertInHTML(
            "<style>.html-css-only { color: blue; }</style>",
            rendered,
        )
        assertInHTML(
            "<script>console.log('HTML and JS only');</script>",
            rendered,
        )

        # Check that the HTML / JS / CSS can be accessed on the component class
        assert TestComponent.template == dedent(
            """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            <div class='html-css-only'>Content</div>
            """,
        )
        assert TestComponent.css == ".html-css-only { color: blue; }"
        assert TestComponent.js == "console.log('HTML and JS only');"

        assert isinstance(TestComponent._template, Template)
        assert TestComponent._template.origin.component_cls is TestComponent

    @djc_test(
        django_settings={
            "STATICFILES_DIRS": [
                Path(__file__).resolve().parent / "static_root",
            ],
        },
    )
    def test_html_js_css_filepath_rel_to_component(self):
        from tests.test_app.components.app_lvl_comp.app_lvl_comp import AppLvlCompComponent

        class TestComponent(AppLvlCompComponent):
            pass

        registry.register("test", TestComponent)

        assert ".html-css-only {\n  color: blue;\n}" in TestComponent.css  # type: ignore[operator]
        assert 'console.log("JS file");' in TestComponent.js  # type: ignore[operator]

        rendered = Template(
            """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component "test" variable="test" / %}
            """,
        ).render(Context())

        assertInHTML(
            """
            <form data-djc-id-ca1bc41 method="post">
                <input name="variable" type="text" value="test"/>
                <input type="submit"/>
            </form>
            """,
            rendered,
        )
        assertInHTML(
            "<style>.html-css-only {  color: blue;  }</style>",
            rendered,
        )
        assertInHTML(
            '<script>console.log("JS file");</script>',
            rendered,
        )

        # Check that the HTML / JS / CSS can be accessed on the component class
        assert TestComponent.template == (
            '<form method="post">\n'
            "  {% csrf_token %}\n"
            '  <input type="text" name="variable" value="{{ variable }}">\n'
            '  <input type="submit">\n'
            "</form>\n"
        )

        assert TestComponent.css == ".html-css-only {\n  color: blue;\n}\n"
        assert TestComponent.js == 'console.log("JS file");\n'

        assert isinstance(TestComponent._template, Template)
        assert TestComponent._template.origin.component_cls is TestComponent

    @djc_test(
        django_settings={
            "STATICFILES_DIRS": [
                Path(__file__).resolve().parent / "static_root",
            ],
        },
    )
    def test_html_js_css_filepath_from_static(self):
        class TestComponent(Component):
            template_file = "test_app_simple_template.html"
            css_file = "style.css"
            js_file = "script.js"

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs["variable"],
                }

        registry.register("test", TestComponent)

        assert "Variable: <strong>{{ variable }}</strong>" in TestComponent.template  # type: ignore[operator]
        assert ".html-css-only {\n    color: blue;\n}" in TestComponent.css  # type: ignore[operator]
        assert 'console.log("HTML and JS only");' in TestComponent.js  # type: ignore[operator]

        assert isinstance(TestComponent._template, Template)
        assert TestComponent._template.origin.component_cls is TestComponent

        rendered = Template(
            """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component "test" variable="test" / %}
            """,
        ).render(Context())

        assert 'Variable: <strong data-djc-id-ca1bc41="">test</strong>' in rendered
        assertInHTML(
            "<style>/* Used in `MainMediaTest` tests in `test_component_media.py` */\n.html-css-only {\n    color: blue;\n}</style>",
            rendered,
        )
        assertInHTML(
            '<script>/* Used in `MainMediaTest` tests in `test_component_media.py` */\nconsole.log("HTML and JS only");</script>',
            rendered,
        )

        # Check that the HTML / JS / CSS can be accessed on the component class
        assert TestComponent.template == "Variable: <strong>{{ variable }}</strong>\n"
        # fmt: off
        assert TestComponent.css == (
            "/* Used in `MainMediaTest` tests in `test_component_media.py` */\n"
            ".html-css-only {\n"
            "    color: blue;\n"
            "}"
        )
        # fmt: on
        assert TestComponent.js == (
            '/* Used in `MainMediaTest` tests in `test_component_media.py` */\nconsole.log("HTML and JS only");\n'
        )

    @djc_test(
        django_settings={
            "STATICFILES_DIRS": [
                Path(__file__).resolve().parent / "static_root",
            ],
        },
    )
    def test_html_js_css_filepath_lazy_loaded(self):
        from tests.test_app.components.app_lvl_comp.app_lvl_comp import AppLvlCompComponent

        class TestComponent(AppLvlCompComponent):
            pass

        # NOTE: Currently the components' JS/CSS are loaded eagerly, to make the JS/CSS
        #       files available via endpoints. If that is no longer true, uncomment the
        #       following lines to test the lazy loading of the CSS.
        #
        # # Since this is a subclass, actual CSS is defined on the parent class, and thus
        # # the corresponding ComponentMedia instance is also on the parent class.
        # assert AppLvlCompComponent._component_media.css is UNSET  # type: ignore[attr-defined]
        # assert AppLvlCompComponent._component_media.css_file == "app_lvl_comp.css"  # type: ignore[attr-defined]
        # assert AppLvlCompComponent._component_media._template is UNSET  # type: ignore[attr-defined]
        #
        # # Access the property to load the CSS
        # _ = TestComponent.css

        media_obj: ComponentMedia = AppLvlCompComponent._component_media  # type: ignore[attr-defined]
        assert media_obj.css == (".html-css-only {\n  color: blue;\n}\n")
        assert media_obj.css_file == "app_lvl_comp/app_lvl_comp.css"
        assert media_obj.js == 'console.log("JS file");\n'
        assert media_obj.js_file == "app_lvl_comp/app_lvl_comp.js"

        # However, templates are loaded SEPARATELY from JS/CSS files, so they are not resolved yet
        assert media_obj.template is UNSET
        assert media_obj.template_file == "app_lvl_comp/app_lvl_comp.html"
        assert media_obj._template is UNSET

        # Because JS/CSS files were already loaded, that means we also already resolved relative file paths
        assert media_obj.resolved_relative_paths

        # Only now, when we access the template, it is resolved
        _ = TestComponent.template

        assert media_obj.template == (
            '<form method="post">\n'
            "  {% csrf_token %}\n"
            '  <input type="text" name="variable" value="{{ variable }}">\n'
            '  <input type="submit">\n'
            "</form>\n"
        )
        assert media_obj.template_file == "app_lvl_comp/app_lvl_comp.html"
        assert isinstance(media_obj._template, Template)
        assert media_obj._template.origin.component_cls is AppLvlCompComponent

    def test_html_variable_filtered(self):
        class FilteredComponent(Component):
            template: types.django_html = """
                Var1: <strong>{{ var1 }}</strong>
                Var2 (uppercased): <strong>{{ var2|upper }}</strong>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "var1": kwargs["var1"],
                    "var2": kwargs["var2"],
                }

        rendered = FilteredComponent.render(kwargs={"var1": "test1", "var2": "test2"})
        assertHTMLEqual(
            rendered,
            """
            Var1: <strong data-djc-id-ca1bc3e>test1</strong>
            Var2 (uppercased): <strong data-djc-id-ca1bc3e>TEST2</strong>
            """,
        )


@djc_test
class TestComponentMedia:
    def test_empty_media(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
                Variable: <strong>{{ variable }}</strong>
            """

            class Media:
                pass

        rendered = SimpleComponent.render()

        assert rendered.count("<style") == 0
        assert rendered.count("<link") == 0

        assert rendered.count("<script") == 1  # 1 Boilerplate script

    def test_css_js_as_lists(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = ["path/to/style.css", "path/to/style2.css"]
                js = ["path/to/script.js"]

        rendered = SimpleComponent.render()

        assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script src="path/to/script.js"></script>', rendered)

    def test_css_js_as_string(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "path/to/style.css"
                js = "path/to/script.js"

        rendered = SimpleComponent.render()

        assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<script src="path/to/script.js"></script>', rendered)

    def test_css_as_dict(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": "path/to/style.css",
                    "print": ["path/to/style2.css"],
                    "screen": "path/to/style3.css",
                }
                js = ["path/to/script.js"]

        rendered = SimpleComponent.render()

        assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style2.css" media="print" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style3.css" media="screen" rel="stylesheet">', rendered)

        assertInHTML('<script src="path/to/script.js"></script>', rendered)

    def test_media_custom_render_js(self):
        class MyMedia(Media):
            def render_js(self):
                tags: list[str] = []
                for path in self._js:  # type: ignore[attr-defined]
                    abs_path = self.absolute_path(path)  # type: ignore[attr-defined]
                    tags.append(f'<script defer src="{abs_path}"></script>')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                js = ["path/to/script.js", "path/to/script2.js"]

        rendered = SimpleComponent.render()

        assert '<script defer src="path/to/script.js"></script>' in rendered
        assert '<script defer src="path/to/script2.js"></script>' in rendered

    def test_media_custom_render_css(self):
        class MyMedia(Media):
            def render_css(self):
                tags: list[str] = []
                media = sorted(self._css)  # type: ignore[attr-defined]
                for medium in media:
                    for path in self._css[medium]:  # type: ignore[attr-defined]
                        tags.append(f'<link abc href="{path}" media="{medium}" rel="stylesheet" />')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                css = {
                    "all": "path/to/style.css",
                    "print": ["path/to/style2.css"],
                    "screen": "path/to/style3.css",
                }

        rendered = SimpleComponent.render()

        assertInHTML('<link abc href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link abc href="path/to/style2.css" media="print" rel="stylesheet">', rendered)
        assertInHTML('<link abc href="path/to/style3.css" media="screen" rel="stylesheet">', rendered)

    @djc_test(
        django_settings={
            "INSTALLED_APPS": ("django_components", "tests"),
        },
    )
    def test_glob_pattern_relative_to_component(self):
        from tests.components.glob.glob import GlobComponent

        rendered = GlobComponent.render()

        assertInHTML('<link href="glob/glob_1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="glob/glob_2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<script src="glob/glob_1.js"></script>', rendered)
        assertInHTML('<script src="glob/glob_2.js"></script>', rendered)

    @djc_test(
        django_settings={
            "INSTALLED_APPS": ("django_components", "tests"),
        },
    )
    def test_glob_pattern_relative_to_root_dir(self):
        from tests.components.glob.glob import GlobComponentRootDir

        rendered = GlobComponentRootDir.render()

        assertInHTML('<link href="glob/glob_1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="glob/glob_2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<script src="glob/glob_1.js"></script>', rendered)
        assertInHTML('<script src="glob/glob_2.js"></script>', rendered)

    @djc_test(
        django_settings={
            "INSTALLED_APPS": ("django_components", "tests"),
        },
    )
    def test_non_globs_not_modified(self):
        from tests.components.glob.glob import NonGlobComponentRootDir

        rendered = NonGlobComponentRootDir.render()

        assertInHTML('<link href="glob/glob_1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<script src="glob/glob_1.js"></script>', rendered)

    @djc_test(
        django_settings={
            "INSTALLED_APPS": ("django_components", "tests"),
        },
    )
    def test_non_globs_not_modified_nonexist(self):
        from tests.components.glob.glob import NonGlobNonexistComponentRootDir

        rendered = NonGlobNonexistComponentRootDir.render()

        assertInHTML('<link href="glob/glob_nonexist.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<script src="glob/glob_nonexist.js"></script>', rendered)

    def test_glob_pattern_does_not_break_urls(self):
        from tests.components.glob.glob import UrlComponent

        rendered = UrlComponent.render()

        assertInHTML('<link href="https://example.com/example/style.min.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="http://example.com/example/style.min.css" media="all" rel="stylesheet">', rendered)
        # `://` is escaped because Django's `Media.absolute_path()` doesn't consider `://` a valid URL
        assertInHTML('<link href="%3A//example.com/example/style.min.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="/path/to/style.css" media="all" rel="stylesheet">', rendered)

        assertInHTML(
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.0.2/chart.min.js"></script>',
            rendered,
        )
        assertInHTML(
            '<script src="http://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.0.2/chart.min.js"></script>',
            rendered,
        )
        # `://` is escaped because Django's `Media.absolute_path()` doesn't consider `://` a valid URL
        assertInHTML(
            '<script src="%3A//cdnjs.cloudflare.com/ajax/libs/Chart.js/3.0.2/chart.min.js"></script>',
            rendered,
        )
        assertInHTML('<script src="/path/to/script.js"></script>', rendered)


@djc_test
class TestMediaPathAsObject:
    def test_safestring(self):
        """
        Test that media work with paths defined as instances of classes that define
        the `__html__` method.

        See https://docs.djangoproject.com/en/5.2/topics/forms/media/#paths-as-objects
        """

        # NOTE: @html_safe adds __html__ method from __str__
        @html_safe
        class JSTag:
            def __init__(self, path: str) -> None:
                self.path = path

            def __str__(self):
                return f'<script js_tag src="{self.path}" type="module"></script>'

        @html_safe
        class CSSTag:
            def __init__(self, path: str) -> None:
                self.path = path

            def __str__(self):
                return f'<link css_tag href="{self.path}" rel="stylesheet" />'

        # Format as mentioned in https://github.com/django-components/django-components/issues/522#issuecomment-2173577094
        @html_safe
        class PathObj:
            def __init__(self, static_path: str) -> None:
                self.static_path = static_path

            def __str__(self):
                return format_html('<script type="module" src="{}"></script>', static(self.static_path))

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        CSSTag("path/to/style.css"),  # Formatted by CSSTag
                        mark_safe('<link hi href="path/to/style2.css" rel="stylesheet" />'),  # Literal
                    ],
                    "print": [
                        CSSTag("path/to/style3.css"),  # Formatted by CSSTag
                    ],
                    "screen": "path/to/style4.css",  # Formatted by Media.render_css
                }
                js = [
                    JSTag("path/to/script.js"),  # Formatted by JSTag
                    mark_safe('<script hi src="path/to/script2.js"></script>'),  # Literal
                    PathObj("path/to/script3.js"),  # Literal
                    "path/to/script4.js",  # Formatted by Media.render_js
                ]

        rendered = SimpleComponent.render()

        assertInHTML('<link css_tag href="path/to/style.css" rel="stylesheet" />', rendered)
        assertInHTML('<link hi href="path/to/style2.css" rel="stylesheet" />', rendered)
        assertInHTML('<link css_tag href="path/to/style3.css" rel="stylesheet" />', rendered)
        assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        assertInHTML('<script js_tag src="path/to/script.js" type="module"></script>', rendered)
        assertInHTML('<script hi src="path/to/script2.js"></script>', rendered)
        assertInHTML('<script type="module" src="path/to/script3.js"></script>', rendered)
        assertInHTML('<script src="path/to/script4.js"></script>', rendered)

    def test_pathlike(self):
        """
        Test that media work with paths defined as instances of classes that define
        the `__fspath__` method.
        """

        class MyPath(os.PathLike):
            def __init__(self, path: str) -> None:
                self.path = path

            def __fspath__(self):
                return self.path

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        MyPath("path/to/style.css"),
                        Path("path/to/style2.css"),
                    ],
                    "print": [
                        MyPath("path/to/style3.css"),
                    ],
                    "screen": "path/to/style4.css",
                }
                js = [
                    MyPath("path/to/script.js"),
                    Path("path/to/script2.js"),
                    "path/to/script3.js",
                ]

        rendered = SimpleComponent.render()

        assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style3.css" media="print" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        assertInHTML('<script src="path/to/script.js"></script>', rendered)
        assertInHTML('<script src="path/to/script2.js"></script>', rendered)
        assertInHTML('<script src="path/to/script3.js"></script>', rendered)

    def test_str(self):
        """
        Test that media work with paths defined as instances of classes that
        subclass 'str'.
        """

        class MyStr(str):
            __slots__ = ()

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        MyStr("path/to/style.css"),
                        "path/to/style2.css",
                    ],
                    "print": [
                        MyStr("path/to/style3.css"),
                    ],
                    "screen": "path/to/style4.css",
                }
                js = [
                    MyStr("path/to/script.js"),
                    "path/to/script2.js",
                ]

        rendered = SimpleComponent.render()

        assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style3.css" media="print" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        assertInHTML('<script src="path/to/script.js"></script>', rendered)
        assertInHTML('<script src="path/to/script2.js"></script>', rendered)

    def test_bytes(self):
        """
        Test that media work with paths defined as instances of classes that
        subclass 'bytes'.
        """

        class MyBytes(bytes):
            pass

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = {
                    "all": [
                        MyBytes(b"path/to/style.css"),
                        b"path/to/style2.css",
                    ],
                    "print": [
                        MyBytes(b"path/to/style3.css"),
                    ],
                    "screen": b"path/to/style4.css",
                }
                js = [
                    MyBytes(b"path/to/script.js"),
                    "path/to/script2.js",
                ]

        rendered = SimpleComponent.render()

        assertInHTML('<link href="path/to/style.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style3.css" media="print" rel="stylesheet">', rendered)
        assertInHTML('<link href="path/to/style4.css" media="screen" rel="stylesheet">', rendered)

        assertInHTML('<script src="path/to/script.js"></script>', rendered)
        assertInHTML('<script src="path/to/script2.js"></script>', rendered)

    def test_function(self):
        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = [
                    lambda: mark_safe('<link hi href="calendar/style.css" rel="stylesheet" />'),  # Literal
                    lambda: Path("calendar/style1.css"),
                    lambda: "calendar/style2.css",
                    lambda: b"calendar/style3.css",
                ]
                js = [
                    lambda: mark_safe('<script hi src="calendar/script.js"></script>'),  # Literal
                    lambda: Path("calendar/script1.js"),
                    lambda: "calendar/script2.js",
                    lambda: b"calendar/script3.js",
                ]

        rendered = SimpleComponent.render()

        assertInHTML('<link hi href="calendar/style.css" rel="stylesheet" />', rendered)
        assertInHTML('<link href="calendar/style1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="calendar/style2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="calendar/style3.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script hi src="calendar/script.js"></script>', rendered)
        assertInHTML('<script src="calendar/script1.js"></script>', rendered)
        assertInHTML('<script src="calendar/script2.js"></script>', rendered)
        assertInHTML('<script src="calendar/script3.js"></script>', rendered)

    @djc_test(
        django_settings={
            "STATIC_URL": "static/",
        },
    )
    def test_works_with_static(self):
        """Test that all the different ways of defining media files works with Django's staticfiles"""

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = [
                    mark_safe(f'<link hi href="{static("calendar/style.css")}" rel="stylesheet" />'),  # Literal
                    Path("calendar/style1.css"),
                    "calendar/style2.css",
                    b"calendar/style3.css",
                    lambda: "calendar/style4.css",
                ]
                js = [
                    mark_safe(f'<script hi src="{static("calendar/script.js")}"></script>'),  # Literal
                    Path("calendar/script1.js"),
                    "calendar/script2.js",
                    b"calendar/script3.js",
                    lambda: "calendar/script4.js",
                ]

        rendered = SimpleComponent.render()

        assertInHTML('<link hi href="/static/calendar/style.css" rel="stylesheet" />', rendered)
        assertInHTML('<link href="/static/calendar/style1.css" media="all" rel="stylesheet" />', rendered)
        assertInHTML('<link href="/static/calendar/style1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="/static/calendar/style2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="/static/calendar/style3.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script hi src="/static/calendar/script.js"></script>', rendered)
        assertInHTML('<script src="/static/calendar/script1.js"></script>', rendered)
        assertInHTML('<script src="/static/calendar/script2.js"></script>', rendered)
        assertInHTML('<script src="/static/calendar/script3.js"></script>', rendered)


@djc_test
class TestMediaStaticfiles:
    # For context see https://github.com/django-components/django-components/issues/522
    @djc_test(
        django_settings={
            # Configure static files. The dummy files are set up in the `./static_root` dir.
            # The URL should have path prefix /static/.
            # NOTE: We don't need STATICFILES_DIRS, because we don't run collectstatic
            #       See https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STATICFILES_DIRS
            "STATIC_URL": "static/",
            "STATIC_ROOT": Path(__file__).resolve().parent / "static_root",
            # `django.contrib.staticfiles` MUST be installed for staticfiles resolution to work.
            "INSTALLED_APPS": [
                "django.contrib.staticfiles",
                "django_components",
            ],
        },
    )
    def test_default_static_files_storage(self):
        """Test integration with Django's staticfiles app"""

        class MyMedia(Media):
            def render_js(self):
                tags: list[str] = []
                for path in self._js:  # type: ignore[attr-defined]
                    abs_path = self.absolute_path(path)  # type: ignore[attr-defined]
                    tags.append(f'<script defer src="{abs_path}"></script>')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                css = "calendar/style.css"
                js = "calendar/script.js"

        rendered = SimpleComponent.render()

        # NOTE: Since we're using the default storage class for staticfiles, the files should
        # be searched as specified above (e.g. `calendar/script.js`) inside `static_root` dir.
        assertInHTML('<link href="/static/calendar/style.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script defer src="/static/calendar/script.js"></script>', rendered)

    # For context see https://github.com/django-components/django-components/issues/522
    @djc_test(
        django_settings={
            # Configure static files. The dummy files are set up in the `./static_root` dir.
            # The URL should have path prefix /static/.
            # NOTE: We don't need STATICFILES_DIRS, because we don't run collectstatic
            #       See https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STATICFILES_DIRS
            "STATIC_URL": "static/",
            "STATIC_ROOT": Path(__file__).resolve().parent / "static_root",
            # NOTE: STATICFILES_STORAGE is deprecated since 5.1, use STORAGES instead
            #       See https://docs.djangoproject.com/en/5.2/ref/settings/#storages
            "STORAGES": {
                # This was NOT changed
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                },
                # This WAS changed so that static files are looked up by the `staticfiles.json`
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
                },
            },
            # `django.contrib.staticfiles` MUST be installed for staticfiles resolution to work.
            "INSTALLED_APPS": [
                "django.contrib.staticfiles",
                "django_components",
            ],
        },
    )
    def test_manifest_static_files_storage(self):
        """Test integration with Django's staticfiles app and ManifestStaticFilesStorage"""

        class MyMedia(Media):
            def render_js(self):
                tags: list[str] = []
                for path in self._js:  # type: ignore[attr-defined]
                    abs_path = self.absolute_path(path)  # type: ignore[attr-defined]
                    tags.append(f'<script defer src="{abs_path}"></script>')
                return tags

        class SimpleComponent(Component):
            template = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            media_class = MyMedia

            class Media:
                css = "calendar/style.css"
                js = "calendar/script.js"

        rendered = SimpleComponent.render()

        # NOTE: Since we're using ManifestStaticFilesStorage, we expect the rendered media to link
        # to the files as defined in staticfiles.json
        assertInHTML('<link href="/static/calendar/style.0eeb72042b59.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script defer src="/static/calendar/script.e1815e23e0ec.js"></script>', rendered)


@djc_test
class TestMediaRelativePath:
    def _gen_parent_component(self):
        class ParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    <h1>Parent content</h1>
                    {% component "variable_display" shadowing_variable='override' new_variable='unique_val' %}
                    {% endcomponent %}
                </div>
                <div>
                    {% slot 'content' %}
                        <h2>Slot content</h2>
                        {% component "variable_display" shadowing_variable='slot_default_override' new_variable='slot_default_unique' %}
                        {% endcomponent %}
                    {% endslot %}
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"shadowing_variable": "NOT SHADOWED"}

        return ParentComponent

    def _gen_variable_display_component(self):
        class VariableDisplay(Component):
            template: types.django_html = """
                {% load component_tags %}
                <h1>Shadowing variable = {{ shadowing_variable }}</h1>
                <h1>Uniquely named variable = {{ unique_variable }}</h1>
            """

            def get_template_data(self, args, kwargs, slots, context):
                context = {}
                if kwargs["shadowing_variable"] is not None:
                    context["shadowing_variable"] = kwargs["shadowing_variable"]
                if kwargs["new_variable"] is not None:
                    context["unique_variable"] = kwargs["new_variable"]
                return context

        return VariableDisplay

    # Settings required for autodiscover to work
    @djc_test(
        django_settings={
            "BASE_DIR": Path(__file__).resolve().parent,
            "STATICFILES_DIRS": [
                Path(__file__).resolve().parent / "components",
            ],
        },
    )
    def test_component_with_relative_media_paths(self):
        registry.register(name="parent_component", component=self._gen_parent_component())
        registry.register(name="variable_display", component=self._gen_variable_display_component())

        # Ensure that the module is executed again after import in autodiscovery
        if "tests.components.relative_file.relative_file" in sys.modules:
            del sys.modules["tests.components.relative_file.relative_file"]

        # Fix the paths, since the "components" dir is nested
        autodiscover(map_module=lambda p: f"tests.{p}" if p.startswith("components") else p)

        # Make sure that only relevant components are registered:
        comps_to_remove = [
            comp_name
            for comp_name in registry.all()
            if comp_name not in ["relative_file_component", "parent_component", "variable_display"]
        ]
        for comp_name in comps_to_remove:
            registry.unregister(comp_name)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'relative_file_component' variable=variable / %}
        """
        template = Template(template_str)
        rendered = render_dependencies(template.render(Context({"variable": "test"})))

        assertInHTML('<link href="relative_file/relative_file.css" media="all" rel="stylesheet">', rendered)

        assertInHTML(
            """
            <form data-djc-id-ca1bc41 method="post">
                <input type="text" name="variable" value="test">
                <input type="submit">
            </form>
            """,
            rendered,
        )

        assertInHTML('<link href="relative_file/relative_file.css" media="all" rel="stylesheet">', rendered)

    # Settings required for autodiscover to work
    @djc_test(
        django_settings={
            "BASE_DIR": Path(__file__).resolve().parent,
            "STATICFILES_DIRS": [
                Path(__file__).resolve().parent / "components",
            ],
        },
    )
    def test_component_with_relative_media_paths_as_subcomponent(self):
        registry.register(name="parent_component", component=self._gen_parent_component())
        registry.register(name="variable_display", component=self._gen_variable_display_component())

        # Ensure that the module is executed again after import in autodiscovery
        if "tests.components.relative_file.relative_file" in sys.modules:
            del sys.modules["tests.components.relative_file.relative_file"]

        # Fix the paths, since the "components" dir is nested
        autodiscover(map_module=lambda p: f"tests.{p}" if p.startswith("components") else p)

        registry.unregister("relative_file_pathobj_component")

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component 'relative_file_component' variable='hello' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assertInHTML('<input type="text" name="variable" value="hello">', rendered)

    # Settings required for autodiscover to work
    @djc_test(
        django_settings={
            "BASE_DIR": Path(__file__).resolve().parent,
            "STATICFILES_DIRS": [
                Path(__file__).resolve().parent / "components",
            ],
        },
    )
    def test_component_with_relative_media_does_not_trigger_safestring_path_at__new__(self):
        """
        Test that, for the __html__ objects are not coerced into string throughout
        the class creation. This is important to allow to call `collectstatic` command.
        Because some users use `static` inside the `__html__` or `__str__` methods.
        So if we "render" the safestring using str() during component class creation (__new__),
        then we force to call `static`. And if this happens during `collectstatic` run,
        then this triggers an error, because `static` is called before the static files exist.

        https://github.com/django-components/django-components/issues/522#issuecomment-2173577094
        """
        registry.register(name="parent_component", component=self._gen_parent_component())
        registry.register(name="variable_display", component=self._gen_variable_display_component())

        # Ensure that the module is executed again after import in autodiscovery
        if "tests.components.relative_file_pathobj.relative_file_pathobj" in sys.modules:
            del sys.modules["tests.components.relative_file_pathobj.relative_file_pathobj"]

        # Fix the paths, since the "components" dir is nested
        autodiscover(map_module=lambda p: f"tests.{p}" if p.startswith("components") else p)

        # Mark the PathObj instances of 'relative_file_pathobj_component' so they won't raise
        # error if PathObj.__str__ is triggered.
        CompCls = registry.get("relative_file_pathobj_component")
        CompCls.Media.js[0].throw_on_calling_str = False  # type: ignore  # noqa: PGH003
        CompCls.Media.css["all"][0].throw_on_calling_str = False  # type: ignore  # noqa: PGH003

        rendered = CompCls.render(kwargs={"variable": "abc"})

        assertInHTML('<input type="text" name="variable" value="abc">', rendered)
        assertInHTML('<link href="relative_file_pathobj.css" rel="stylesheet">', rendered)

        assertInHTML('<script type="module" src="relative_file_pathobj.js"></script>', rendered)


@djc_test
class TestSubclassingAttributes:
    def test_both_js_and_js_file_none(self):
        class TestComp(Component):
            js = None
            js_file = None
            template = None
            template_file = None

        assert TestComp.js is None
        assert TestComp.js_file is None
        assert TestComp.template is None
        assert TestComp.template_file is None

    def test_mixing_none_and_non_none_raises(self):
        with pytest.raises(
            ImproperlyConfigured,
            match=re.escape("Received non-empty value from both 'template' and 'template_file' in Component TestComp"),
        ):

            class TestComp(Component):
                js = "console.log('hi')"
                js_file = None
                template = "<h1>hi</h1>"
                template_file = None

    def test_both_non_none_raises(self):
        with pytest.raises(
            ImproperlyConfigured,
            match=re.escape("Received non-empty value from both 'template' and 'template_file' in Component TestComp"),
        ):

            class TestComp(Component):
                js = "console.log('hi')"
                js_file = "file.js"
                template = "<h1>hi</h1>"
                template_file = "file.html"

    def test_parent_non_null_child_non_null(self):
        class ParentComp(Component):
            js = "console.log('parent')"
            template = "<h1>parent</h1>"

        class TestComp(ParentComp):
            js = "console.log('child')"
            template = "<h1>child</h1>"

        assert TestComp.js == "console.log('child')"
        assert TestComp.js_file is None
        assert TestComp.template == "<h1>child</h1>"
        assert TestComp.template_file is None

        assert isinstance(ParentComp._template, Template)
        assert ParentComp._template.source == "<h1>parent</h1>"
        assert ParentComp._template.origin.component_cls == ParentComp

        assert isinstance(TestComp._template, Template)
        assert TestComp._template.source == "<h1>child</h1>"
        assert TestComp._template.origin.component_cls == TestComp

    def test_parent_null_child_non_null(self):
        class ParentComp(Component):
            js = None
            template = None

        class TestComp(ParentComp):
            js = "console.log('child')"
            template = "<h1>child</h1>"

        assert TestComp.js == "console.log('child')"
        assert TestComp.js_file is None
        assert TestComp.template == "<h1>child</h1>"
        assert TestComp.template_file is None

        assert ParentComp._template is None

        assert isinstance(TestComp._template, Template)
        assert TestComp._template.source == "<h1>child</h1>"
        assert TestComp._template.origin.component_cls == TestComp

    def test_parent_non_null_child_null(self):
        class ParentComp(Component):
            js: str | None = "console.log('parent')"
            template: str | None = "<h1>parent</h1>"

        class TestComp(ParentComp):
            js = None
            template = None

        assert TestComp.js is None
        assert TestComp.js_file is None
        assert TestComp.template is None
        assert TestComp.template_file is None

        assert TestComp._template is None

        assert isinstance(ParentComp._template, Template)
        assert ParentComp._template.source == "<h1>parent</h1>"
        assert ParentComp._template.origin.component_cls == ParentComp

    def test_parent_null_child_null(self):
        class ParentComp(Component):
            js = None
            template = None

        class TestComp(ParentComp):
            js = None
            template = None

        assert TestComp.js is None
        assert TestComp.js_file is None
        assert TestComp.template is None
        assert TestComp.template_file is None

        assert TestComp._template is None
        assert ParentComp._template is None

    def test_grandparent_non_null_parent_pass_child_pass(self):
        class GrandParentComp(Component):
            js = "console.log('grandparent')"
            template = "<h1>grandparent</h1>"

        class ParentComp(GrandParentComp):
            pass

        class TestComp(ParentComp):
            pass

        assert TestComp.js == "console.log('grandparent')"
        assert TestComp.js_file is None
        assert TestComp.template == "<h1>grandparent</h1>"
        assert TestComp.template_file is None

        assert isinstance(GrandParentComp._template, Template)
        assert GrandParentComp._template.source == "<h1>grandparent</h1>"
        assert GrandParentComp._template.origin.component_cls == GrandParentComp

        assert isinstance(ParentComp._template, Template)
        assert ParentComp._template.source == "<h1>grandparent</h1>"
        assert ParentComp._template.origin.component_cls == ParentComp

        assert isinstance(TestComp._template, Template)
        assert TestComp._template.source == "<h1>grandparent</h1>"
        assert TestComp._template.origin.component_cls == TestComp

    def test_grandparent_non_null_parent_null_child_pass(self):
        class GrandParentComp(Component):
            js: str | None = "console.log('grandparent')"
            template: str | None = "<h1>grandparent</h1>"

        class ParentComp(GrandParentComp):
            js = None
            template = None

        class TestComp(ParentComp):
            pass

        assert TestComp.js is None
        assert TestComp.js_file is None
        assert TestComp.template is None
        assert TestComp.template_file is None

        assert isinstance(GrandParentComp._template, Template)
        assert GrandParentComp._template.source == "<h1>grandparent</h1>"
        assert GrandParentComp._template.origin.component_cls == GrandParentComp

        assert ParentComp._template is None
        assert TestComp._template is None

    def test_grandparent_non_null_parent_pass_child_non_null(self):
        class GrandParentComp(Component):
            js = "console.log('grandparent')"
            template = "<h1>grandparent</h1>"

        class ParentComp(GrandParentComp):
            pass

        class TestComp(ParentComp):
            js = "console.log('child')"
            template = "<h1>child</h1>"

        assert TestComp.js == "console.log('child')"
        assert TestComp.js_file is None
        assert TestComp.template == "<h1>child</h1>"
        assert TestComp.template_file is None

        assert isinstance(GrandParentComp._template, Template)
        assert GrandParentComp._template.source == "<h1>grandparent</h1>"
        assert GrandParentComp._template.origin.component_cls == GrandParentComp

        assert isinstance(ParentComp._template, Template)
        assert ParentComp._template.source == "<h1>grandparent</h1>"
        assert ParentComp._template.origin.component_cls == ParentComp

        assert isinstance(TestComp._template, Template)
        assert TestComp._template.source == "<h1>child</h1>"
        assert TestComp._template.origin.component_cls == TestComp

    def test_grandparent_null_parent_pass_child_non_null(self):
        class GrandParentComp(Component):
            js = None
            template = None

        class ParentComp(GrandParentComp):
            pass

        class TestComp(ParentComp):
            js = "console.log('child')"
            template = "<h1>child</h1>"

        assert TestComp.js == "console.log('child')"
        assert TestComp.js_file is None
        assert TestComp.template == "<h1>child</h1>"
        assert TestComp.template_file is None

        assert GrandParentComp._template is None
        assert ParentComp._template is None

        assert isinstance(TestComp._template, Template)
        assert TestComp._template.source == "<h1>child</h1>"
        assert TestComp._template.origin.component_cls == TestComp


@djc_test
class TestSubclassingMedia:
    def test_media_in_child_and_parent(self):
        class ParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "parent.css"
                js = "parent.js"

        class ChildComponent(ParentComponent):
            class Media:
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="parent.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script src="child.js"></script>', rendered)
        assertInHTML('<script src="parent.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n'
            '<link href="parent.css" media="all" rel="stylesheet">\n'
            '<script src="child.js"></script>\n'
            '<script src="parent.js"></script>'
        )

    def test_media_in_child_and_grandparent(self):
        class GrandParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "grandparent.css"
                js = "grandparent.js"

        # `pass` means that we inherit `Media` from `GrandParentComponent`
        class ParentComponent(GrandParentComponent):
            pass

        class ChildComponent(ParentComponent):
            class Media:
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="grandparent.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script src="child.js"></script>', rendered)
        assertInHTML('<script src="grandparent.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n'
            '<link href="grandparent.css" media="all" rel="stylesheet">\n'
            '<script src="child.js"></script>\n'
            '<script src="grandparent.js"></script>'
        )

    # Check that setting `Media = None` on a child class means that we will NOT inherit `Media` from the parent class
    def test_media_in_child_and_grandparent__inheritance_off(self):
        class GrandParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "grandparent.css"
                js = "grandparent.js"

        # `None` means that we will NOT inherit `Media` from `GrandParentComponent`
        class ParentComponent(GrandParentComponent):
            Media = None  # type: ignore[assignment]

        class ChildComponent(ParentComponent):
            class Media:
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<script src="child.js"></script>', rendered)

        assert "grandparent.css" not in rendered
        assert "grandparent.js" not in rendered

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n<script src="child.js"></script>'
        )

    def test_media_in_parent_and_grandparent(self):
        class GrandParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "grandparent.css"
                js = "grandparent.js"

        class ParentComponent(GrandParentComponent):
            class Media:
                css = "parent.css"
                js = "parent.js"

        class ChildComponent(ParentComponent):
            pass

        rendered = ChildComponent.render()

        assertInHTML('<link href="parent.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="grandparent.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script src="parent.js"></script>', rendered)
        assertInHTML('<script src="grandparent.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="parent.css" media="all" rel="stylesheet">\n'
            '<link href="grandparent.css" media="all" rel="stylesheet">\n'
            '<script src="parent.js"></script>\n'
            '<script src="grandparent.js"></script>'
        )

    def test_media_in_multiple_bases(self):
        class GrandParent1Component(Component):
            class Media:
                css = "grandparent1.css"
                js = "grandparent1.js"

        class GrandParent2Component(Component):
            pass

        # NOTE: The bases don't even have to be Component classes,
        # as long as they have the nested `Media` class.
        class GrandParent3Component:
            # NOTE: When we don't subclass `Component`, we have to correctly format the `Media` class
            class Media:
                css = {"all": ["grandparent3.css"]}
                js = ["grandparent3.js"]

        class GrandParent4Component:
            pass

        class Parent1Component(GrandParent1Component, GrandParent2Component):
            class Media:
                css = "parent1.css"
                js = "parent1.js"

        # `pass` means that we inherit `Media` from `GrandParent3Component` and `GrandParent4Component`
        class Parent2Component(GrandParent3Component, GrandParent4Component):
            pass

        class ChildComponent(Parent1Component, Parent2Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="parent1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="grandparent1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="grandparent3.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script src="child.js"></script>', rendered)
        assertInHTML('<script src="parent1.js"></script>', rendered)
        assertInHTML('<script src="grandparent1.js"></script>', rendered)
        assertInHTML('<script src="grandparent3.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n'
            '<link href="grandparent3.css" media="all" rel="stylesheet">\n'
            '<link href="parent1.css" media="all" rel="stylesheet">\n'
            '<link href="grandparent1.css" media="all" rel="stylesheet">\n'
            '<script src="child.js"></script>\n'
            '<script src="grandparent3.js"></script>\n'
            '<script src="parent1.js"></script>\n'
            '<script src="grandparent1.js"></script>'
        )

    # Check that setting `Media = None` on a child class means that we will NOT inherit `Media` from the parent class
    def test_media_in_multiple_bases__inheritance_off(self):
        class GrandParent1Component(Component):
            class Media:
                css = "grandparent1.css"
                js = "grandparent1.js"

        class GrandParent2Component(Component):
            pass

        # NOTE: The bases don't even have to be Component classes,
        # as long as they have the nested `Media` class.
        class GrandParent3Component:
            # NOTE: When we don't subclass `Component`, we have to correctly format the `Media` class
            class Media:
                css = {"all": ["grandparent3.css"]}
                js = ["grandparent3.js"]

        class GrandParent4Component:
            pass

        class Parent1Component(GrandParent1Component, GrandParent2Component):
            class Media:
                css = "parent1.css"
                js = "parent1.js"

        # `None` means that we will NOT inherit `Media` from `GrandParent3Component` and `GrandParent4Component`
        class Parent2Component(GrandParent3Component, GrandParent4Component):
            Media = None  # type: ignore[assignment]

        class ChildComponent(Parent1Component, Parent2Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="parent1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="grandparent1.css" media="all" rel="stylesheet">', rendered)

        assertInHTML('<script src="child.js"></script>', rendered)
        assertInHTML('<script src="parent1.js"></script>', rendered)
        assertInHTML('<script src="grandparent1.js"></script>', rendered)

        assert "grandparent3.css" not in rendered
        assert "grandparent3.js" not in rendered

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n'
            '<link href="parent1.css" media="all" rel="stylesheet">\n'
            '<link href="grandparent1.css" media="all" rel="stylesheet">\n'
            '<script src="child.js"></script>\n'
            '<script src="parent1.js"></script>\n'
            '<script src="grandparent1.js"></script>'
        )

    def test_extend_false_in_child(self):
        class Parent1Component(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "parent1.css"
                js = "parent1.js"

        class Parent2Component(Component):
            class Media:
                css = "parent2.css"
                js = "parent2.js"

        class ChildComponent(Parent1Component, Parent2Component):
            class Media:
                extend = False
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assert "parent1.css" not in rendered
        assert "parent2.css" not in rendered
        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)

        assert "parent1.js" not in rendered
        assert "parent2.js" not in rendered
        assertInHTML('<script src="child.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n<script src="child.js"></script>'
        )

    def test_extend_false_in_parent(self):
        class GrandParentComponent(Component):
            class Media:
                css = "grandparent.css"
                js = "grandparent.js"

        class Parent1Component(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "parent1.css"
                js = "parent1.js"

        class Parent2Component(GrandParentComponent):
            class Media:
                extend = False
                css = "parent2.css"
                js = "parent2.js"

        class ChildComponent(Parent1Component, Parent2Component):
            class Media:
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assert "grandparent.css" not in rendered
        assertInHTML('<link href="parent1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="parent2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)

        assert "grandparent.js" not in rendered
        assertInHTML('<script src="parent1.js"></script>', rendered)
        assertInHTML('<script src="parent2.js"></script>', rendered)
        assertInHTML('<script src="child.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n'
            '<link href="parent2.css" media="all" rel="stylesheet">\n'
            '<link href="parent1.css" media="all" rel="stylesheet">\n'
            '<script src="child.js"></script>\n'
            '<script src="parent2.js"></script>\n'
            '<script src="parent1.js"></script>'
        )

    def test_extend_list_in_child(self):
        class Parent1Component(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "parent1.css"
                js = "parent1.js"

        class Parent2Component(Component):
            class Media:
                css = "parent2.css"
                js = "parent2.js"

        class Other1Component(Component):
            class Media:
                css = "other1.css"
                js = "other1.js"

        class Other2Component:
            class Media:
                css = {"all": ["other2.css"]}
                js = ["other2.js"]

        class ChildComponent(Parent1Component, Parent2Component):
            class Media:
                extend = [Other1Component, Other2Component]
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assert "parent1.css" not in rendered
        assert "parent2.css" not in rendered
        assertInHTML('<link href="other1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="other2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)

        assert "parent1.js" not in rendered
        assert "parent2.js" not in rendered
        assertInHTML('<script src="other1.js"></script>', rendered)
        assertInHTML('<script src="other2.js"></script>', rendered)
        assertInHTML('<script src="child.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n'
            '<link href="other2.css" media="all" rel="stylesheet">\n'
            '<link href="other1.css" media="all" rel="stylesheet">\n'
            '<script src="child.js"></script>\n'
            '<script src="other2.js"></script>\n'
            '<script src="other1.js"></script>'
        )

    def test_extend_list_in_parent(self):
        class Other1Component(Component):
            class Media:
                css = "other1.css"
                js = "other1.js"

        class Other2Component:
            class Media:
                css = {"all": ["other2.css"]}
                js = ["other2.js"]

        class GrandParentComponent(Component):
            class Media:
                css = "grandparent.css"
                js = "grandparent.js"

        class Parent1Component(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component_js_dependencies %}
                {% component_css_dependencies %}
            """

            class Media:
                css = "parent1.css"
                js = "parent1.js"

        class Parent2Component(GrandParentComponent):
            class Media:
                extend = [Other1Component, Other2Component]
                css = "parent2.css"
                js = "parent2.js"

        class ChildComponent(Parent1Component, Parent2Component):
            class Media:
                css = "child.css"
                js = "child.js"

        rendered = ChildComponent.render()

        assert "grandparent.css" not in rendered
        assertInHTML('<link href="other1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="other2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="parent1.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="parent2.css" media="all" rel="stylesheet">', rendered)
        assertInHTML('<link href="child.css" media="all" rel="stylesheet">', rendered)

        assert "grandparent.js" not in rendered
        assertInHTML('<script src="other1.js"></script>', rendered)
        assertInHTML('<script src="other2.js"></script>', rendered)
        assertInHTML('<script src="parent1.js"></script>', rendered)
        assertInHTML('<script src="parent2.js"></script>', rendered)
        assertInHTML('<script src="child.js"></script>', rendered)

        assert str(ChildComponent.media) == (
            '<link href="child.css" media="all" rel="stylesheet">\n'
            '<link href="parent2.css" media="all" rel="stylesheet">\n'
            '<link href="parent1.css" media="all" rel="stylesheet">\n'
            '<link href="other2.css" media="all" rel="stylesheet">\n'
            '<link href="other1.css" media="all" rel="stylesheet">\n'
            '<script src="child.js"></script>\n'
            '<script src="parent2.js"></script>\n'
            '<script src="parent1.js"></script>\n'
            '<script src="other2.js"></script>\n'
            '<script src="other1.js"></script>'
        )
