"""
These tests check the public API side of managing dependencies - We check
if calling `Component.render()` or `render_dependencies()` behave as expected.

For checking the OUTPUT of the dependencies, see `test_dependency_rendering.py`.
"""

import re
from unittest.mock import Mock

import pytest
from django.http import HttpResponseNotModified
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import Component, registry, render_dependencies, types
from django_components.components.dynamic import DynamicComponent
from django_components.middleware import ComponentDependencyMiddleware

from django_components.testing import djc_test
from .testutils import create_and_process_template_response, setup_test_config

setup_test_config({"autodiscover": False})


class SimpleComponent(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    css: types.css = """
        .xyz {
            color: red;
        }
    """

    js: types.js = """
        console.log("xyz");
    """

    def get_context_data(self, variable, variable2="default"):
        return {
            "variable": variable,
            "variable2": variable2,
        }

    class Media:
        css = "style.css"
        js = "script.js"


@djc_test
class TestDependenciesLegacy:
    # TODO_v1 - Remove
    def test_render_with_type_arg(self):
        rendered = SimpleComponent.render(kwargs={"variable": "foo"}, type="append")

        # Dependency manager script NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        # Check that it contains inlined JS and CSS, and Media.css
        assert rendered.strip() == (
            'Variable: <strong data-djc-id-ca1bc3e="">foo</strong>\n'
            '    <script src="script.js"></script><script>console.log("xyz");</script><style>.xyz {\n'
            "            color: red;\n"
            '        }</style><link href="style.css" media="all" rel="stylesheet">'
        )


@djc_test
class TestRenderDependencies:
    def test_standalone_render_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({}))

        # Placeholders
        assert rendered_raw.count('<link name="CSS_PLACEHOLDER">') == 1
        assert rendered_raw.count('<script name="JS_PLACEHOLDER"></script>') == 1

        assert rendered_raw.count("<script") == 1
        assert rendered_raw.count("<style") == 0
        assert rendered_raw.count("<link") == 1
        assert rendered_raw.count("_RENDERED") == 1

        rendered = render_dependencies(rendered_raw)

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        assertInHTML('<script>console.log("xyz");</script>', rendered, count=1)  # Inlined JS

        assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css

    def test_middleware_renders_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = create_and_process_template_response(template, use_middleware=True)

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        assertInHTML('<script>console.log("xyz");</script>', rendered, count=1)  # Inlined JS

        assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 1

    def test_component_render_renders_dependencies(self):
        class SimpleComponentWithDeps(SimpleComponent):
            template: types.django_html = (
                """
                    {% load component_tags %}
                    {% component_js_dependencies %}
                    {% component_css_dependencies %}
                """
                + SimpleComponent.template
            )

        registry.register(name="test", component=SimpleComponentWithDeps)

        rendered = SimpleComponentWithDeps.render(
            kwargs={"variable": "foo"},
        )

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        assertInHTML('<script>console.log("xyz");</script>', rendered, count=1)  # Inlined JS

        assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 1

    def test_component_render_renders_dependencies_opt_out(self):
        class SimpleComponentWithDeps(SimpleComponent):
            template: types.django_html = (
                """
                    {% load component_tags %}
                    {% component_js_dependencies %}
                    {% component_css_dependencies %}
                """
                + SimpleComponent.template
            )

        registry.register(name="test", component=SimpleComponentWithDeps)

        rendered_raw = SimpleComponentWithDeps.render(
            kwargs={"variable": "foo"},
            render_dependencies=False,
        )

        assert rendered_raw.count("<script") == 1
        assert rendered_raw.count("<style") == 0
        assert rendered_raw.count("<link") == 1
        assert rendered_raw.count("_RENDERED") == 1

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered_raw, count=0)

        assertInHTML("<style>.xyz { color: red; }</style>", rendered_raw, count=0)  # Inlined CSS
        assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered_raw, count=0)  # Media.css

        assertInHTML(
            '<script>console.log("xyz");</script>',
            rendered_raw,
            count=0,
        )  # Inlined JS

    def test_component_render_to_response_renders_dependencies(self):
        class SimpleComponentWithDeps(SimpleComponent):
            template: types.django_html = (
                """
                    {% load component_tags %}
                    {% component_js_dependencies %}
                    {% component_css_dependencies %}
                """
                + SimpleComponent.template
            )

        registry.register(name="test", component=SimpleComponentWithDeps)

        response = SimpleComponentWithDeps.render_to_response(
            kwargs={"variable": "foo"},
        )
        rendered = response.content.decode()

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assertInHTML("<style>.xyz { color: red; }</style>", rendered, count=1)  # Inlined CSS
        assertInHTML('<script>console.log("xyz");</script>', rendered, count=1)  # Inlined JS

        assert rendered.count('<link href="style.css" media="all" rel="stylesheet">') == 1  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 1

    # NOTE: Some HTML parser libraries like selectolax or lxml try to "correct" the given HTML.
    #       We want to avoid this behavior, so user gets the exact same HTML back.
    def test_does_not_try_to_add_close_tags(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            <thead>
        """

        rendered_raw = Template(template_str).render(Context({"formset": [1]}))
        rendered = render_dependencies(rendered_raw, strategy="fragment")

        assertHTMLEqual(rendered, "<thead>")

    def test_does_not_modify_html_when_no_component_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    {% for form in formset %}
                        {% with row_number=forloop.counter %}
                            <tr class=" hover:bg-gray-200 py-0 {% cycle 'bg-white' 'bg-gray-50' %} divide-x "
                                aria-rowindex="{{ row_number }}">
                                <!-- row num -->
                                <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                                    aria-colindex="1">
                                    {{ row_number }}
                                </td>
                            </tr>
                        {% endwith %}
                    {% endfor %}
                </tbody>
            </table>
        """

        rendered_raw = Template(template_str).render(Context({"formset": [1]}))
        rendered = render_dependencies(rendered_raw, strategy="fragment")

        expected = """
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    <tr class=" hover:bg-gray-200 py-0 bg-white divide-x "
                        aria-rowindex="1">
                        <!-- row num -->
                        <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                            aria-colindex="1">
                            1
                        </td>
                    </tr>
                </tbody>
            </table>
        """

        assertHTMLEqual(expected, rendered)

    # Explanation: The component is used in the template, but the template doesn't use
    # {% component_js_dependencies %} or {% component_css_dependencies %} tags,
    # nor defines a `<head>` or `<body>` tag. In which case, the dependencies are not rendered.
    def test_does_not_modify_html_when_component_used_but_nowhere_to_insert(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    {% for form in formset %}
                        {% with row_number=forloop.counter %}
                            <tr class=" hover:bg-gray-200 py-0 {% cycle 'bg-white' 'bg-gray-50' %} divide-x "
                                aria-rowindex="{{ row_number }}">
                                <!-- row num -->
                                <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                                    aria-colindex="1">
                                    {{ row_number }}
                                    {% component "test" variable="hi" / %}
                                </td>
                            </tr>
                        {% endwith %}
                    {% endfor %}
                </tbody>
            </table>
        """

        rendered_raw = Template(template_str).render(Context({"formset": [1]}))
        rendered = render_dependencies(rendered_raw, strategy="fragment")

        # Base64 encodings:
        # `PGxpbmsgaHJlZj0ic3R5bGUuY3NzIiBtZWRpYT0iYWxsIiByZWw9InN0eWxlc2hlZXQiPg==` -> `<link href="style.css" media="all" rel="stylesheet">`  # noqa: E501
        # `PGxpbmsgaHJlZj0iL2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50XzMxMTA5Ny5jc3MiIG1lZGlhPSJhbGwiIHJlbD0ic3R5bGVzaGVldCI+` -> `<link href="/components/cache/SimpleComponent_311097.css" media="all" rel="stylesheet">`  # noqa: E501
        # `PHNjcmlwdCBzcmM9InNjcmlwdC5qcyI+PC9zY3JpcHQ+` -> `<script src="script.js"></script>`
        # `PHNjcmlwdCBzcmM9Ii9jb21wb25lbnRzL2NhY2hlL1NpbXBsZUNvbXBvbmVudF8zMTEwOTcuanMiPjwvc2NyaXB0Pg==` -> `<script src="/components/cache/SimpleComponent_311097.js"></script>`  # noqa: E501
        expected = """
            <table class="table-auto border-collapse divide-y divide-x divide-slate-300 w-full">
                <!-- Table head -->
                <thead>
                    <tr class="py-0 my-0 h-7">
                        <!-- Empty row -->
                        <th class="min-w-12">#</th>
                    </tr>
                </thead>
                <!-- Table body -->
                <tbody id="items" class="divide-y divide-slate-300">
                    <tr class=" hover:bg-gray-200 py-0 bg-white divide-x "
                        aria-rowindex="1">
                        <!-- row num -->
                        <td class="whitespace-nowrap w-fit text-center px-4 w-px"
                            aria-colindex="1">
                            1
                            Variable: <strong data-djc-id-ca1bc3f>hi</strong>
                        </td>
                    </tr>
                </tbody>
            </table>
            <script type="application/json" data-djc>
                {"loadedCssUrls": [],
                "loadedJsUrls": [],
                "toLoadCssTags": ["PGxpbmsgaHJlZj0ic3R5bGUuY3NzIiBtZWRpYT0iYWxsIiByZWw9InN0eWxlc2hlZXQiPg==",
                    "PGxpbmsgaHJlZj0iL2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50XzMxMTA5Ny5jc3MiIG1lZGlhPSJhbGwiIHJlbD0ic3R5bGVzaGVldCI+"],
                "toLoadJsTags": ["PHNjcmlwdCBzcmM9InNjcmlwdC5qcyI+PC9zY3JpcHQ+",
                "PHNjcmlwdCBzcmM9Ii9jb21wb25lbnRzL2NhY2hlL1NpbXBsZUNvbXBvbmVudF8zMTEwOTcuanMiPjwvc2NyaXB0Pg=="]}
            </script>
        """  # noqa: E501

        assertHTMLEqual(expected, rendered)

    def test_raises_if_script_end_tag_inside_component_js(self):
        class ComponentWithScript(SimpleComponent):
            js: types.js = """
                console.log("</script  >");
            """

        registry.register(name="test", component=ComponentWithScript)

        with pytest.raises(
            RuntimeError,
            match=re.escape("Content of `Component.js` for component 'ComponentWithScript' contains '</script>' end tag."),  # noqa: E501
        ):
            ComponentWithScript.render(kwargs={"variable": "foo"})

    def test_raises_if_script_end_tag_inside_component_css(self):
        class ComponentWithScript(SimpleComponent):
            css: types.css = """
                /* </style  > */
                .xyz {
                    color: red;
                }
            """

        registry.register(name="test", component=ComponentWithScript)

        with pytest.raises(
            RuntimeError,
            match=re.escape("Content of `Component.css` for component 'ComponentWithScript' contains '</style>' end tag."),  # noqa: E501
        ):
            ComponentWithScript.render(kwargs={"variable": "foo"})


@djc_test
class TestDependenciesStrategyDocument:
    def test_inserts_styles_and_script_to_default_places_if_not_overriden(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head></head>
                <body>
                    {% component "test" variable="foo" / %}
                </body>
            </html>
        """
        rendered_raw = Template(template_str).render(Context({}))
        rendered = render_dependencies(rendered_raw)

        assert rendered.count("<script") == 4
        assert rendered.count("<style") == 1
        assert rendered.count("<link") == 1
        assert rendered.count("_RENDERED") == 0

        assertInHTML(
            """
            <head>
                <style>.xyz { color: red; }</style>
                <link href="style.css" media="all" rel="stylesheet">
            </head>
            """,
            rendered,
            count=1,
        )

        body_re = re.compile(r"<body>(.*?)</body>", re.DOTALL)
        rendered_body = body_re.search(rendered).group(1)  # type: ignore[union-attr]

        assertInHTML(
            """<script src="django_components/django_components.min.js">""",
            rendered_body,
            count=1,
        )
        assertInHTML(
            '<script>console.log("xyz");</script>',
            rendered_body,
            count=1,
        )

    def test_does_not_insert_styles_and_script_to_default_places_if_overriden(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_js_dependencies %}
                </head>
                <body>
                    {% component "test" variable="foo" / %}
                    {% component_css_dependencies %}
                </body>
            </html>
        """
        rendered_raw = Template(template_str).render(Context({}))
        rendered = render_dependencies(rendered_raw)

        assert rendered.count("<script") == 4
        assert rendered.count("<style") == 1
        assert rendered.count("<link") == 1
        assert rendered.count("_RENDERED") == 0

        assertInHTML(
            """
            <body>
                Variable: <strong data-djc-id-ca1bc41>foo</strong>

                <style>.xyz { color: red; }</style>
                <link href="style.css" media="all" rel="stylesheet">
            </body>
            """,
            rendered,
            count=1,
        )

        head_re = re.compile(r"<head>(.*?)</head>", re.DOTALL)
        rendered_head = head_re.search(rendered).group(1)  # type: ignore[union-attr]

        assertInHTML(
            """<script src="django_components/django_components.min.js">""",
            rendered_head,
            count=1,
        )
        assertInHTML(
            '<script>console.log("xyz");</script>',
            rendered_head,
            count=1,
        )


@djc_test
class TestDependenciesStrategySimple:
    def test_single_component(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({}))

        # Placeholders
        assert rendered_raw.count('<link name="CSS_PLACEHOLDER">') == 1
        assert rendered_raw.count('<script name="JS_PLACEHOLDER"></script>') == 1

        assert rendered_raw.count("<script") == 1
        assert rendered_raw.count("<style") == 0
        assert rendered_raw.count("<link") == 1
        assert rendered_raw.count("_RENDERED") == 1

        rendered = render_dependencies(rendered_raw, strategy="simple")

        # Dependency manager script NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        # Check that it contains inlined JS and CSS, and Media.css
        assert rendered.strip() == (
            '<script src="script.js"></script><script>console.log("xyz");</script>\n'
            "            <style>.xyz {\n"
            "            color: red;\n"
            '        }</style><link href="style.css" media="all" rel="stylesheet">\n'
            "            \n"
            '        Variable: <strong data-djc-id-ca1bc41="">foo</strong>'
        )

    def test_multiple_components_dependencies(self):
        class SimpleComponentNested(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% component "inner" variable=variable / %}
                    {% slot "default" default / %}
                </div>
            """

            css: types.css = """
                .my-class {
                    color: red;
                }
            """

            js: types.js = """
                console.log("Hello");
            """

            def get_context_data(self, variable):
                return {}

            class Media:
                css = ["style.css", "style2.css"]
                js = "script2.js"

        class OtherComponent(Component):
            template: types.django_html = """
                XYZ: <strong>{{ variable }}</strong>
            """

            css: types.css = """
                .xyz {
                    color: red;
                }
            """

            js: types.js = """
                console.log("xyz");
            """

            def get_context_data(self, variable):
                return {}

            class Media:
                css = "xyz1.css"
                js = "xyz1.js"

        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)
        registry.register(name="other", component=OtherComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'outer' variable='variable' %}
                {% component 'other' variable='variable_inner' / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({}))

        rendered = render_dependencies(rendered_raw, strategy="simple")

        # Dependency manager script NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assert rendered.count("<script") == 6  # 3 Component.js and 3 Media.js
        assert rendered.count("<link") == 3  # Media.css
        assert rendered.count("<style") == 3  # Component.css

        # Components' inlined CSS
        # NOTE: Each of these should be present only ONCE!
        assertInHTML(
            """
            <style>.my-class { color: red; }</style>
            <style>.xyz { color: red; }</style>
            """,
            rendered,
            count=1,
        )

        # Components' Media.css
        # Order:
        # - "style.css", "style2.css" (from SimpleComponentNested)
        # - "style.css" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.css" (from OtherComponent inserted into SimpleComponentNested)
        assertInHTML(
            """
            <link href="style.css" media="all" rel="stylesheet">
            <link href="style2.css" media="all" rel="stylesheet">
            <link href="xyz1.css" media="all" rel="stylesheet">
            """,
            rendered,
            count=1,
        )

        # Components' Media.js followed by inlined JS
        # Order:
        # - "script2.js" (from SimpleComponentNested)
        # - "script.js" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.js" (from OtherComponent inserted into SimpleComponentNested)
        assertInHTML(
            """
            <script src="script2.js"></script>
            <script src="script.js"></script>
            <script src="xyz1.js"></script>
            <script>console.log("Hello");</script>
            <script>console.log("xyz");</script>
            """,
            rendered,
            count=1,
        )

        # Check that there's no payload like with "document" or "fragment" modes
        assert "application/json" not in rendered


@djc_test
class TestDependenciesStrategyPrepend:
    def test_single_component(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({}))

        # Placeholders
        assert rendered_raw.count('<link name="CSS_PLACEHOLDER">') == 1
        assert rendered_raw.count('<script name="JS_PLACEHOLDER"></script>') == 1

        assert rendered_raw.count("<script") == 1
        assert rendered_raw.count("<style") == 0
        assert rendered_raw.count("<link") == 1
        assert rendered_raw.count("_RENDERED") == 1

        rendered = render_dependencies(rendered_raw, strategy="prepend")

        # Dependency manager script NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        # Check that it contains inlined JS and CSS, and Media.css
        assert rendered.strip() == (
            '<script src="script.js"></script><script>console.log("xyz");</script><style>.xyz {\n'
            "            color: red;\n"
            '        }</style><link href="style.css" media="all" rel="stylesheet">\n'
            "            \n"
            "            \n"
            "            \n"
            "            \n"
            '        Variable: <strong data-djc-id-ca1bc41="">foo</strong>'
        )

    def test_multiple_components_dependencies(self):
        class SimpleComponentNested(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% component "inner" variable=variable / %}
                    {% slot "default" default / %}
                </div>
            """

            css: types.css = """
                .my-class {
                    color: red;
                }
            """

            js: types.js = """
                console.log("Hello");
            """

            def get_context_data(self, variable):
                return {}

            class Media:
                css = ["style.css", "style2.css"]
                js = "script2.js"

        class OtherComponent(Component):
            template: types.django_html = """
                XYZ: <strong>{{ variable }}</strong>
            """

            css: types.css = """
                .xyz {
                    color: red;
                }
            """

            js: types.js = """
                console.log("xyz");
            """

            def get_context_data(self, variable):
                return {}

            class Media:
                css = "xyz1.css"
                js = "xyz1.js"

        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)
        registry.register(name="other", component=OtherComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'outer' variable='variable' %}
                {% component 'other' variable='variable_inner' / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({}))

        rendered = render_dependencies(rendered_raw, strategy="prepend")

        # Dependency manager script NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assert rendered.count("<script") == 6  # 3 Component.js and 3 Media.js
        assert rendered.count("<link") == 3  # Media.css
        assert rendered.count("<style") == 3  # Component.css

        # Components' inlined CSS
        # NOTE: Each of these should be present only ONCE!
        assertInHTML(
            """
            <style>.my-class { color: red; }</style>
            <style>.xyz { color: red; }</style>
            """,
            rendered,
            count=1,
        )

        # Components' Media.css
        # Order:
        # - "style.css", "style2.css" (from SimpleComponentNested)
        # - "style.css" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.css" (from OtherComponent inserted into SimpleComponentNested)
        assertInHTML(
            """
            <link href="style.css" media="all" rel="stylesheet">
            <link href="style2.css" media="all" rel="stylesheet">
            <link href="xyz1.css" media="all" rel="stylesheet">
            """,
            rendered,
            count=1,
        )

        # Components' Media.js followed by inlined JS
        # Order:
        # - "script2.js" (from SimpleComponentNested)
        # - "script.js" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.js" (from OtherComponent inserted into SimpleComponentNested)
        assertInHTML(
            """
            <script src="script2.js"></script>
            <script src="script.js"></script>
            <script src="xyz1.js"></script>
            <script>console.log("Hello");</script>
            <script>console.log("xyz");</script>
            """,
            rendered,
            count=1,
        )

        # Check that there's no payload like with "document" or "fragment" modes
        assert "application/json" not in rendered


@djc_test
class TestDependenciesStrategyAppend:
    def test_single_component(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({}))

        # Placeholders
        assert rendered_raw.count('<link name="CSS_PLACEHOLDER">') == 1
        assert rendered_raw.count('<script name="JS_PLACEHOLDER"></script>') == 1

        assert rendered_raw.count("<script") == 1
        assert rendered_raw.count("<style") == 0
        assert rendered_raw.count("<link") == 1
        assert rendered_raw.count("_RENDERED") == 1

        rendered = render_dependencies(rendered_raw, strategy="append")

        # Dependency manager script NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        # Check that it contains inlined JS and CSS, and Media.css
        assert rendered.strip() == (
            'Variable: <strong data-djc-id-ca1bc41="">foo</strong>\n'
            "    \n"
            '        <script src="script.js"></script><script>console.log("xyz");</script><style>.xyz {\n'
            "            color: red;\n"
            '        }</style><link href="style.css" media="all" rel="stylesheet">'
        )

    def test_multiple_components_dependencies(self):
        class SimpleComponentNested(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% component "inner" variable=variable / %}
                    {% slot "default" default / %}
                </div>
            """

            css: types.css = """
                .my-class {
                    color: red;
                }
            """

            js: types.js = """
                console.log("Hello");
            """

            def get_context_data(self, variable):
                return {}

            class Media:
                css = ["style.css", "style2.css"]
                js = "script2.js"

        class OtherComponent(Component):
            template: types.django_html = """
                XYZ: <strong>{{ variable }}</strong>
            """

            css: types.css = """
                .xyz {
                    color: red;
                }
            """

            js: types.js = """
                console.log("xyz");
            """

            def get_context_data(self, variable):
                return {}

            class Media:
                css = "xyz1.css"
                js = "xyz1.js"

        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)
        registry.register(name="other", component=OtherComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'outer' variable='variable' %}
                {% component 'other' variable='variable_inner' / %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({}))

        rendered = render_dependencies(rendered_raw, strategy="append")

        # Dependency manager script NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assert rendered.count("<script") == 6  # 3 Component.js and 3 Media.js
        assert rendered.count("<link") == 3  # Media.css
        assert rendered.count("<style") == 3  # Component.css

        # Components' inlined CSS
        # NOTE: Each of these should be present only ONCE!
        assertInHTML(
            """
            <style>.my-class { color: red; }</style>
            <style>.xyz { color: red; }</style>
            """,
            rendered,
            count=1,
        )

        # Components' Media.css
        # Order:
        # - "style.css", "style2.css" (from SimpleComponentNested)
        # - "style.css" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.css" (from OtherComponent inserted into SimpleComponentNested)
        assertInHTML(
            """
            <link href="style.css" media="all" rel="stylesheet">
            <link href="style2.css" media="all" rel="stylesheet">
            <link href="xyz1.css" media="all" rel="stylesheet">
            """,
            rendered,
            count=1,
        )

        # Components' Media.js followed by inlined JS
        # Order:
        # - "script2.js" (from SimpleComponentNested)
        # - "script.js" (from SimpleComponent inside SimpleComponentNested)
        # - "xyz1.js" (from OtherComponent inserted into SimpleComponentNested)
        assertInHTML(
            """
            <script src="script2.js"></script>
            <script src="script.js"></script>
            <script src="xyz1.js"></script>
            <script>console.log("Hello");</script>
            <script>console.log("xyz");</script>
            """,
            rendered,
            count=1,
        )

        # Check that there's no payload like with "document" or "fragment" modes
        assert "application/json" not in rendered


@djc_test
class TestMiddleware:
    def test_middleware_response_without_content_type(self):
        response = HttpResponseNotModified()
        middleware = ComponentDependencyMiddleware(get_response=lambda _: response)
        request = Mock()
        assert response == middleware(request=request)

    def test_middleware_response_with_components_with_slash_dash_and_underscore(self):
        registry.register("dynamic", DynamicComponent)
        registry.register("test-component", component=SimpleComponent)
        registry.register("test/component", component=SimpleComponent)
        registry.register("test_component", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_css_dependencies %}
            {% component_js_dependencies %}
            {% component "dynamic" is=component_name variable='value' / %}
        """
        template = Template(template_str)

        def assert_dependencies(content: str):
            # Dependency manager script (empty)
            assertInHTML('<script src="django_components/django_components.min.js"></script>', content, count=1)

            # Inlined JS
            assertInHTML('<script>console.log("xyz");</script>', content, count=1)
            # Inlined CSS
            assertInHTML("<style>.xyz { color: red; }</style>", content, count=1)
            # Media.css
            assertInHTML('<link href="style.css" media="all" rel="stylesheet">', content, count=1)

        rendered1 = create_and_process_template_response(
            template,
            context=Context({"component_name": "test-component"}),
        )

        assert_dependencies(rendered1)
        assert rendered1.count('Variable: <strong data-djc-id-ca1bc42="" data-djc-id-ca1bc41="">value</strong>') == 1

        rendered2 = create_and_process_template_response(
            template,
            context=Context({"component_name": "test-component"}),
        )

        assert_dependencies(rendered2)
        assert rendered2.count('Variable: <strong data-djc-id-ca1bc44="" data-djc-id-ca1bc43="">value</strong>') == 1

        rendered3 = create_and_process_template_response(
            template,
            context=Context({"component_name": "test_component"}),
        )

        assert_dependencies(rendered3)
        assert rendered3.count('Variable: <strong data-djc-id-ca1bc46="" data-djc-id-ca1bc45="">value</strong>') == 1
