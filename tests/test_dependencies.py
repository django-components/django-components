"""
These tests check the public API side of managing dependencies - We check
if calling `Component.render()` or `render_dependencies()` behave as expected.

For checking the OUTPUT of the dependencies, see `test_dependency_rendering.py`.
"""

import re

import pytest
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import Component, registry, render_dependencies, types
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


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

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "variable": kwargs["variable"],
            "variable2": kwargs.get("variable2", "default"),
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
            '    <script src="script.js"></script><script>\n'
            '        console.log("xyz");\n'
            "    </script><style>\n"
            "        .xyz {\n"
            "            color: red;\n"
            "        }\n"
            '    </style><link media="all" rel="stylesheet" href="style.css">'
        )


@djc_test
class TestRenderDependencies:
    # Check that `render_dependencies()` works when called directly
    def test_render_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        # NOTE: `"ignore"` is a special value that means "do not render dependencies"
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

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

    # Check that instead of `render_dependencies()`, we can simply call `Template.render()`
    def test_template_render(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assertInHTML(
            "<style>.xyz { color: red; }</style>",
            rendered,
            count=1,
        )  # Inlined CSS
        assertInHTML('<script>console.log("xyz");</script>', rendered, count=1)  # Inlined JS

        assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 1

    # Check that we can change the dependencies strategy via `DJC_DEPS_STRATEGY` context key
    def test_template_render_deps_strategy(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered: str = template.render(Context({"DJC_DEPS_STRATEGY": "append"}))

        # Dependency manager script NOT included
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assertInHTML(
            "<style>.xyz { color: red; }</style>",
            rendered,
            count=1,
        )  # Inlined CSS
        assertInHTML('<script>console.log("xyz");</script>', rendered, count=1)  # Inlined JS

        assertInHTML('<link href="style.css" media="all" rel="stylesheet">', rendered, count=1)  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 1

        # Check that the order is correct (dependencies are appended)
        assert rendered.strip() == (
            'Variable: <strong data-djc-id-ca1bc41="">foo</strong>\n'
            "    \n"
            '        <script src="script.js"></script><script>\n'
            '        console.log("xyz");\n'
            "    </script><style>\n"
            "        .xyz {\n"
            "            color: red;\n"
            "        }\n"
            '    </style><link media="all" rel="stylesheet" href="style.css">'
        )

    # Check that `Component.render()` renders dependencies
    def test_component_render(self):
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

    def test_component_render_opt_out(self):
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
            deps_strategy="ignore",
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

    # Check that `Component.render_to_response()` renders dependencies
    def test_component_render_to_response(self):
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

        assert rendered.count('<link media="all" rel="stylesheet" href="style.css">') == 1  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 1

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
        rendered_raw = Template(template_str).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
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
        rendered_raw = Template(template_str).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        rendered: str = render_dependencies(rendered_raw)

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

    # NOTE: Some HTML parser libraries like selectolax or lxml try to "correct" the given HTML.
    #       We want to avoid this behavior, so user gets the exact same HTML back.
    def test_does_not_try_to_add_close_tags(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            <thead>
        """

        rendered_raw = Template(template_str).render(Context({"formset": [1], "DJC_DEPS_STRATEGY": "ignore"}))
        rendered = render_dependencies(rendered_raw, strategy="fragment")

        # NOTE: Fragments adds a script to optionally load the component manager script.
        assertHTMLEqual(
            rendered,
            """
            <thead>
            <script>
                (() => {
                    if (!globalThis.DjangoComponents) {
                        const s = document.createElement('script');
                        s.src = "django_components/django_components.min.js";
                        document.head.appendChild(s);
                    }
                    // Remove this loader script
                    if (document.currentScript) document.currentScript.remove();
                })();
            </script>
            """,
        )

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

        rendered_raw = Template(template_str).render(Context({"formset": [1], "DJC_DEPS_STRATEGY": "ignore"}))
        rendered = render_dependencies(rendered_raw, strategy="fragment")

        # NOTE: Fragments adds a script to optionally load the component manager script.
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
            <script>
                (() => {
                    if (!globalThis.DjangoComponents) {
                        const s = document.createElement('script');
                        s.src = "django_components/django_components.min.js";
                        document.head.appendChild(s);
                    }
                    // Remove this loader script
                    if (document.currentScript) document.currentScript.remove();
                })();
            </script>
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

        rendered_raw = Template(template_str).render(Context({"formset": [1], "DJC_DEPS_STRATEGY": "ignore"}))
        rendered = render_dependencies(rendered_raw, strategy="fragment")

        # Base64 encodings:
        # `PGxpbmsgaHJlZj0ic3R5bGUuY3NzIiBtZWRpYT0iYWxsIiByZWw9InN0eWxlc2hlZXQiPg==` -> `<link href="style.css" media="all" rel="stylesheet">`  # noqa: E501
        # `PGxpbmsgaHJlZj0iL2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50XzMxMTA5Ny5jc3MiIG1lZGlhPSJhbGwiIHJlbD0ic3R5bGVzaGVldCI+` -> `<link href="/components/cache/SimpleComponent_311097.css" media="all" rel="stylesheet">`  # noqa: E501
        # `PHNjcmlwdCBzcmM9InNjcmlwdC5qcyI+PC9zY3JpcHQ+` -> `<script src="script.js"></script>`
        # `PHNjcmlwdCBzcmM9Ii9jb21wb25lbnRzL2NhY2hlL1NpbXBsZUNvbXBvbmVudF8zMTEwOTcuanMiPjwvc2NyaXB0Pg==` -> `<script src="/components/cache/SimpleComponent_311097.js"></script>`  # noqa: E501
        #
        # NOTE: Fragments adds a script to optionally load the component manager script.
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
                            Variable: <strong data-djc-id-ca1bc3f="">hi</strong>
                        </td>
                    </tr>
                </tbody>
            </table>
            <script>
            (() => {
                if (!globalThis.DjangoComponents) {
                    const s = document.createElement('script');
                    s.src = "django_components/django_components.min.js";
                    document.head.appendChild(s);
                }
                // Remove this loader script
                if (document.currentScript) document.currentScript.remove();
            })();
        </script>
        <script type="application/json" data-djc>{"cssUrls__markAsLoaded": [],
            "jsUrls__markAsLoaded": [],
            "cssTags__toFetch": ["eyJ0YWciOiAibGluayIsICJhdHRycyI6IHsibWVkaWEiOiAiYWxsIiwgInJlbCI6ICJzdHlsZXNoZWV0IiwgImhyZWYiOiAic3R5bGUuY3NzIn0sICJjb250ZW50IjogIiJ9",
                "eyJ0YWciOiAibGluayIsICJhdHRycyI6IHsibWVkaWEiOiAiYWxsIiwgInJlbCI6ICJzdHlsZXNoZWV0IiwgImhyZWYiOiAiL2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50XzMxMTA5Ny5jc3MifSwgImNvbnRlbnQiOiAiIn0="],
            "jsTags__toFetch": ["eyJ0YWciOiAic2NyaXB0IiwgImF0dHJzIjogeyJzcmMiOiAic2NyaXB0LmpzIn0sICJjb250ZW50IjogIiJ9",
                "eyJ0YWciOiAic2NyaXB0IiwgImF0dHJzIjogeyJzcmMiOiAiL2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50XzMxMTA5Ny5qcyJ9LCAiY29udGVudCI6ICIifQ=="],
            "componentJsVars": [],
            "componentJsCalls": []}</script>
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
            match=re.escape(
                "Script for component 'ComponentWithScript_ab2b78' contains '<script>' end tag.",
            ),
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
            match=re.escape(
                "Style for component 'ComponentWithScript_a51788' contains '<style>' end tag.",
            ),
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
        rendered_raw = Template(template_str).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        rendered = render_dependencies(rendered_raw, strategy="document")

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
        rendered_raw = Template(template_str).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        rendered = render_dependencies(rendered_raw, strategy="document")

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
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

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
            '<script src="script.js"></script><script>\n'
            '        console.log("xyz");\n'
            "    </script>\n"
            "            <style>\n"
            "        .xyz {\n"
            "            color: red;\n"
            "        }\n"
            '    </style><link media="all" rel="stylesheet" href="style.css">\n'
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
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

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
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

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
            '<script src="script.js"></script><script>\n'
            '        console.log("xyz");\n'
            "    </script><style>\n"
            "        .xyz {\n"
            "            color: red;\n"
            "        }\n"
            '    </style><link media="all" rel="stylesheet" href="style.css">\n'
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
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

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
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

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
            '        <script src="script.js"></script><script>\n'
            '        console.log("xyz");\n'
            "    </script><style>\n"
            "        .xyz {\n"
            "            color: red;\n"
            "        }\n"
            '    </style><link media="all" rel="stylesheet" href="style.css">'
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
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

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
class TestDependenciesStrategyRaw:
    def test_single_component(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered_raw: str = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        # Placeholders
        assert rendered_raw.count('<link name="CSS_PLACEHOLDER">') == 1
        assert rendered_raw.count('<script name="JS_PLACEHOLDER"></script>') == 1

        assert rendered_raw.count("<script") == 1
        assert rendered_raw.count("<style") == 0
        assert rendered_raw.count("<link") == 1
        assert rendered_raw.count("_RENDERED") == 1

        # Check that it contains inlined JS and CSS, and Media.css
        assert rendered_raw.strip() == (
            '<script name="JS_PLACEHOLDER"></script>\n'
            '            <link name="CSS_PLACEHOLDER">\n'
            "            <!-- _RENDERED SimpleComponent_311097,ca1bc41,, -->\n"
            '        Variable: <strong data-djc-id-ca1bc41="">foo</strong>'
        )
