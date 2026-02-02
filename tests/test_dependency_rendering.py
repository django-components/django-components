"""
Here we check that the logic around dependency rendering outputs correct HTML.
During actual rendering, the HTML is then picked up by the JS-side dependency manager.
"""

# ruff: noqa: E501

import re

from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import Component, registry, types
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


def to_spaces(s: str):
    return re.compile(r"\s+").sub(" ", s)


class SimpleComponent(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "variable": kwargs["variable"],
            "variable2": kwargs.get("variable2", "default"),
        }

    class Media:
        css = "style.css"
        js = "script.js"


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


class SimpleComponentWithSharedDependency(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    class Media:
        css = ["style.css", "style2.css"]
        js = ["script.js", "script2.js"]


class MultistyleComponent(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    class Media:
        css = ["style.css", "style2.css"]
        js = ["script.js", "script2.js"]


@djc_test
class TestDependencyRendering:
    def test_no_dependencies_when_no_components_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
        """
        template = Template(template_str)
        rendered: str = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assert rendered.count("<script") == 1  # 1 placeholder script
        assert rendered.count("<link") == 1  # 1 placeholder link
        assert rendered.count("<style") == 0

        assert "jsUrls__markAsLoaded" not in rendered
        assert "cssUrls__markAsLoaded" not in rendered
        assert "jsTags__toFetch" not in rendered
        assert "cssTags__toFetch" not in rendered

        assert rendered.strip() == (
            '<script name="JS_PLACEHOLDER"></script>\n            <link name="CSS_PLACEHOLDER">'
        )

    def test_no_js_dependencies_when_no_components_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_js_dependencies %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assert rendered.count("<script") == 1  # 1 placeholder script
        assert rendered.count("<link") == 0  # No CSS
        assert rendered.count("<style") == 0

        assert "jsUrls__markAsLoaded" not in rendered
        assert "cssUrls__markAsLoaded" not in rendered
        assert "jsTags__toFetch" not in rendered
        assert "cssTags__toFetch" not in rendered

        assert rendered.strip() == '<script name="JS_PLACEHOLDER"></script>'

    def test_no_css_dependencies_when_no_components_used(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_css_dependencies %}
        """
        template = Template(template_str)
        rendered: str = template.render(Context({}))

        assert rendered.count("<script") == 0  # No JS
        assert rendered.count("<link") == 1  # 1 placeholder link
        assert rendered.count("<style") == 0

        assert rendered.strip() == '<link name="CSS_PLACEHOLDER">'

    def test_single_component_dependencies(self):
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

        assert rendered.count('<link media="all" rel="stylesheet" href="style.css">') == 1  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 0
        assert rendered.count("<script") == 3

        # `c3R5bGUuY3Nz` is base64 encoded `style.css`
        # `c2NyaXB0Lmpz` is base64 encoded `style.js`
        assertInHTML(
            """
            <script type="application/json" data-djc>
                {"cssUrls__markAsLoaded": ["c3R5bGUuY3Nz"],
                "jsUrls__markAsLoaded": ["c2NyaXB0Lmpz"],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_single_component_with_dash_or_slash_in_name(self):
        registry.register(name="te-s/t", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'te-s/t' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assert rendered.count('<link media="all" rel="stylesheet" href="style.css">') == 1  # Media.css
        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 0
        assert rendered.count("<script") == 3

        # `c3R5bGUuY3Nz` is base64 encoded `style.css`
        # `c2NyaXB0Lmpz` is base64 encoded `style.js`
        assertInHTML(
            """
            <script type="application/json" data-djc>
                {"cssUrls__markAsLoaded": ["c3R5bGUuY3Nz"],
                "jsUrls__markAsLoaded": ["c2NyaXB0Lmpz"],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_single_component_placeholder_removed(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "_RENDERED" not in rendered

    def test_single_component_css_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_css_dependencies %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # Dependency manager script - NOT present
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assert rendered.count("<link") == 1
        assert rendered.count("<style") == 0
        assert rendered.count("<script") == 0  # No JS scripts

        assert rendered.count('<link media="all" rel="stylesheet" href="style.css">') == 1  # Media.css

    def test_single_component_js_dependencies(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}{% component_js_dependencies %}
            {% component 'test' variable='foo' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        # CSS NOT included
        assert rendered.count("<link") == 0
        assert rendered.count("<style") == 0
        assert rendered.count("<script") == 3

        # `c3R5bGUuY3Nz` is base64 encoded `style.css`
        # `c2NyaXB0Lmpz` is base64 encoded `style.js`
        assertInHTML(
            """
            <script type="application/json" data-djc>
                {"cssUrls__markAsLoaded": ["c3R5bGUuY3Nz"],
                "jsUrls__markAsLoaded": ["c2NyaXB0Lmpz"],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_all_dependencies_are_rendered_for_component_with_multiple_dependencies(
        self,
    ):
        registry.register(name="test", component=MultistyleComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'test' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assert rendered.count("<link") == 2
        assert rendered.count("<style") == 0
        assert rendered.count("<script") == 4  # 2 scripts belong to the boilerplate

        # Media.css
        assertInHTML(
            """
            <link href="style.css" media="all" rel="stylesheet">
            <link href="style2.css" media="all" rel="stylesheet">
            """,
            rendered,
            count=1,
        )

        # Media.js
        assertInHTML(
            """
            <script src="script.js"></script>
            <script src="script2.js"></script>
            """,
            rendered,
            count=1,
        )

        # Base64 encoding:
        # `c3R5bGUuY3Nz` -> `style.css`
        # `c3R5bGUyLmNzcw==` -> `style2.css`
        # `c2NyaXB0Lmpz` -> `script.js`
        # `c2NyaXB0Mi5qcw==` -> `script2.js`
        assertInHTML(
            """
            <script type="application/json" data-djc>
                {"cssUrls__markAsLoaded": ["c3R5bGUuY3Nz", "c3R5bGUyLmNzcw=="],
                "jsUrls__markAsLoaded": ["c2NyaXB0Lmpz", "c2NyaXB0Mi5qcw=="],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_no_dependencies_with_multiple_unused_components(self):
        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
        """
        template = Template(template_str)
        rendered: str = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=0)

        assert rendered.count("<script") == 1  # 1 placeholder script
        assert rendered.count("<link") == 1  # 1 placeholder link
        assert rendered.count("<style") == 0

        assert "jsUrls__markAsLoaded" not in rendered
        assert "cssUrls__markAsLoaded" not in rendered
        assert "jsTags__toFetch" not in rendered
        assert "cssTags__toFetch" not in rendered

        assert rendered.strip() == (
            '<script name="JS_PLACEHOLDER"></script>\n            <link name="CSS_PLACEHOLDER">'
        )

    def test_multiple_components_dependencies(self):
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
        rendered: str = template.render(Context({}))

        # Dependency manager script
        # NOTE: Should be present only ONCE!
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)

        assert rendered.count("<script") == 7  # 2 scripts belong to the boilerplate
        assert rendered.count("<link") == 3
        assert rendered.count("<style") == 2

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
            <script>(function() { console.log("Hello"); })();</script>
            <script>(function() { console.log("xyz"); })();</script>
            """,
            rendered,
            count=1,
        )

        # Base64 encoding:
        # `c3R5bGUuY3Nz` -> `style.css`
        # `c3R5bGUyLmNzcw==` -> `style2.css`
        # `eHl6MS5jc3M=` -> `xyz1.css`
        # `L2NvbXBvbmVudHMvY2FjaGUvT3RoZXJDb21wb25lbnRfNjMyOWFlLmNzcw==` -> `/components/cache/OtherComponent_6329ae.css`
        # `L2NvbXBvbmVudHMvY2FjaGUvT3RoZXJDb21wb25lbnRfNjMyOWFlLmpz` -> `/components/cache/OtherComponent_6329ae.js`
        # `L2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50TmVzdGVkX2YwMmQzMi5jc3M=` -> `/components/cache/SimpleComponentNested_f02d32.css`
        # `L2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50TmVzdGVkX2YwMmQzMi5qcw==` -> `/components/cache/SimpleComponentNested_f02d32.js`
        # `c2NyaXB0Lmpz` -> `script.js`
        # `c2NyaXB0Mi5qcw==` -> `script2.js`
        # `eHl6MS5qcw==` -> `xyz1.js`
        assertInHTML(
            """
            <script type="application/json" data-djc>
                {"cssUrls__markAsLoaded": ["L2NvbXBvbmVudHMvY2FjaGUvT3RoZXJDb21wb25lbnRfNjMyOWFlLmNzcw==",
                    "L2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50TmVzdGVkX2YwMmQzMi5jc3M=",
                    "c3R5bGUuY3Nz",
                    "c3R5bGUyLmNzcw==",
                    "eHl6MS5jc3M="],
                "jsUrls__markAsLoaded": ["L2NvbXBvbmVudHMvY2FjaGUvT3RoZXJDb21wb25lbnRfNjMyOWFlLmpz",
                    "L2NvbXBvbmVudHMvY2FjaGUvU2ltcGxlQ29tcG9uZW50TmVzdGVkX2YwMmQzMi5qcw==",
                    "c2NyaXB0Lmpz",
                    "c2NyaXB0Mi5qcw==",
                    "eHl6MS5qcw=="],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": []}
            </script>
            """,
            rendered,
            count=1,
        )

    def test_multiple_components_all_placeholders_removed(self):
        registry.register(name="inner", component=SimpleComponent)
        registry.register(name="outer", component=SimpleComponentNested)
        registry.register(name="test", component=SimpleComponentWithSharedDependency)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% component 'inner' variable='variable' / %}
            {% component 'outer' variable='variable' / %}
            {% component 'test' variable='variable' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assert "_RENDERED" not in rendered

    def test_adds_component_id_html_attr_single(self):
        registry.register(name="test", component=SimpleComponent)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f>foo</strong>")

    def test_adds_component_id_html_attr_single_multiroot(self):
        class SimpleMultiroot(SimpleComponent):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
                Variable2: <div>{{ variable }}</div>
                Variable3: <span>{{ variable }}</span>
            """

        registry.register(name="test", component=SimpleMultiroot)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3f>foo</strong>
            Variable2: <div data-djc-id-ca1bc3f>foo</div>
            Variable3: <span data-djc-id-ca1bc3f>foo</span>
            """,
        )

    # Test that, if multiple components share the same root HTML elements,
    # then those elemens will have the `data-djc-id-` attribute added for each component.
    def test_adds_component_id_html_attr_nested(self):
        class SimpleMultiroot(SimpleComponent):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
                Variable2: <div>{{ variable }}</div>
                Variable3: <span>{{ variable }}</span>
            """

        class SimpleOuter(SimpleComponent):
            template: types.django_html = """
                {% load component_tags %}
                {% component 'multiroot' variable='foo' / %}
                <div>Another</div>
            """

        registry.register(name="multiroot", component=SimpleMultiroot)
        registry.register(name="outer", component=SimpleOuter)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'outer' variable='foo' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc41>foo</strong>
            Variable2: <div data-djc-id-ca1bc3f data-djc-id-ca1bc41>foo</div>
            Variable3: <span data-djc-id-ca1bc3f data-djc-id-ca1bc41>foo</span>
            <div data-djc-id-ca1bc3f>Another</div>
            """,
        )

    # `data-djc-id-` attribute should be added on each instance in the RESULTING HTML.
    # So if in a loop, each iteration creates a new component, and each of those should
    # have a unique `data-djc-id-` attribute.
    def test_adds_component_id_html_attr_loops(self):
        class SimpleMultiroot(SimpleComponent):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
                Variable2: <div>{{ variable }}</div>
                Variable3: <span>{{ variable }}</span>
            """

        class SimpleOuter(SimpleComponent):
            template: types.django_html = """
                {% load component_tags %}
                {% component 'multiroot' variable='foo' / %}
                <div>Another</div>
            """

        registry.register(name="multiroot", component=SimpleMultiroot)
        registry.register(name="outer", component=SimpleOuter)

        template_str: types.django_html = """
            {% load component_tags %}
            {% for i in lst %}
                {% component 'outer' variable='foo' / %}
            {% endfor %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"lst": range(3)}))

        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc41>foo</strong>
            Variable2: <div data-djc-id-ca1bc3f data-djc-id-ca1bc41>foo</div>
            Variable3: <span data-djc-id-ca1bc3f data-djc-id-ca1bc41>foo</span>
            <div data-djc-id-ca1bc3f>Another</div>

            Variable: <strong data-djc-id-ca1bc42 data-djc-id-ca1bc43>foo</strong>
            Variable2: <div data-djc-id-ca1bc42 data-djc-id-ca1bc43>foo</div>
            Variable3: <span data-djc-id-ca1bc42 data-djc-id-ca1bc43>foo</span>
            <div data-djc-id-ca1bc42>Another</div>

            Variable: <strong data-djc-id-ca1bc44 data-djc-id-ca1bc45>foo</strong>
            Variable2: <div data-djc-id-ca1bc44 data-djc-id-ca1bc45>foo</div>
            Variable3: <span data-djc-id-ca1bc44 data-djc-id-ca1bc45>foo</span>
            <div data-djc-id-ca1bc44>Another</div>
            """,
        )

    # See https://github.com/django-components/django-components/pull/1390
    def test_dependencies_with_component_in_inclusion_tag(self):
        registry.register(name="test_component", component=OtherComponent)

        @registry.library.inclusion_tag("component_inside_include_sub.html")
        def inclusion_tag():
            return {}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component_js_dependencies %}
            {% component_css_dependencies %}
            {% inclusion_tag %}
        """
        template = Template(template_str)
        rendered: str = template.render(Context({}))

        # Dependency manager script
        assertInHTML('<script src="django_components/django_components.min.js"></script>', rendered, count=1)
        assertInHTML(
            """
            <script src="xyz1.js"></script>
            """,
            rendered,
            count=1,
        )
        assertInHTML(
            """
            <link href="xyz1.css" media="all" rel="stylesheet">
            """,
            rendered,
            count=1,
        )

        assert rendered.count("<script") == 4  # manager + deps + 2 OtherComponent
        assert rendered.count("<link") == 1  # 1 OtherComponent
        assert rendered.count("<style") == 1  # 1 Style

        registry.library.tags.pop("inclusion_tag")
