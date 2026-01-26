from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.testing import djc_test
from django_components.util.css import is_css_func

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


@djc_test
class TestCssFunctionDetection:
    def test_is_css_func_detects_css_functions(self):
        """Test that is_css_func correctly identifies CSS function calls."""
        # Should return True for CSS functions
        assert is_css_func("calc(100% - 20px)") is True
        assert is_css_func("var(--color)") is True
        assert is_css_func("url(image.png)") is True
        assert is_css_func("rgba(255, 0, 0, 0.5)") is True
        assert is_css_func("linear-gradient(to right, red, blue)") is True
        assert is_css_func("rgb(255, 0, 0)") is True
        assert is_css_func("hsla(120, 100%, 50%, 0.5)") is True
        assert is_css_func("  calc(100%)") is True  # With leading spaces

        # Should return False for non-functions
        assert is_css_func("Hello World") is False
        assert is_css_func("red") is False
        assert is_css_func("#ff0000") is False
        assert is_css_func("100px") is False
        assert is_css_func("") is False


@djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
class TestCssVariables:
    def test_css_variables_multiple_variables_in_same_stylesheet(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="themed-button">Button</div>
                {% component_css_dependencies %}
            """
            css = """
                .themed-button {
                    background-color: var(--button_bg);
                    color: var(--button_color);
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "button_bg": "#0275d8",
                    "button_color": "#fff",
                }

        rendered = TestComponent.render()

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED TestComponent_415f49,ca1bc3e,,468e36 -->
            <div class="themed-button" data-djc-id-ca1bc3e data-djc-css-468e36>Button</div>
            <style>
                .themed-button {
                    background-color: var(--button_bg);
                    color: var(--button_color);
                }
            </style>
            <style>
/* TestComponent_415f49 */
[data-djc-css-468e36] {
  --button_bg: #0275d8;
  --button_color: #fff;
}
</style>
            """,
        )

    def test_css_variables_with_numeric_values(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="sized-box">Box</div>
                {% component_css_dependencies %}
            """
            css = """
                .sized-box {
                    width: var(--box_width);
                    height: var(--box_height);
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "box_width": "100px",
                    "box_height": "200px",
                }

        rendered = TestComponent.render()

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED TestComponent_f11bca,ca1bc3e,,af06fd -->
            <div class="sized-box" data-djc-id-ca1bc3e data-djc-css-af06fd>Box</div>
            <style>
                .sized-box {
                    width: var(--box_width);
                    height: var(--box_height);
                }
            </style>
            <style>
/* TestComponent_f11bca */
[data-djc-css-af06fd] {
  --box_width: 100px;
  --box_height: 200px;
}
</style>
            """,
        )

    def test_css_variables_with_color_values(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="colored-box">Box</div>
                {% component_css_dependencies %}
            """
            css = """
                .colored-box {
                    background-color: var(--bg_color);
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "bg_color": "red",
                }

        rendered = TestComponent.render()

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED TestComponent_a1edd9,ca1bc3e,,b9e76a -->
            <div class="colored-box" data-djc-id-ca1bc3e data-djc-css-b9e76a>Box</div>
            <style>
                .colored-box {
                    background-color: var(--bg_color);
                }
            </style>
            <style>
/* TestComponent_a1edd9 */
[data-djc-css-b9e76a] {
  --bg_color: red;
}
</style>
            """,
        )

    def test_css_variables_multiple_instances_different_values(self, components_settings):
        @register("themed_box")
        class TestComponent(Component):
            template: types.django_html = """
                <div class="themed-box">Box</div>
            """
            css = """
                .themed-box {
                    background-color: var(--bg_color);
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "bg_color": kwargs.get("color", "blue"),
                }

        # Render a single template with two instances with different colors
        template_str: types.django_html = """
            {% load component_tags %}
            <div id="box-red">
                {% component "themed_box" color="red" / %}
            </div>
            <div id="box-green">
                {% component "themed_box" color="green" / %}
            </div>
            {% component_css_dependencies %}
        """

        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div id="box-red">
                <div class="themed-box" data-djc-id-ca1bc41 data-djc-css-b9e76a>Box</div>
            </div>
            <div id="box-green">
                <div class="themed-box" data-djc-id-ca1bc42 data-djc-css-c5e6ab>Box</div>
            </div>
            <style>
                .themed-box {
                    background-color: var(--bg_color);
                }
            </style>
            <style>
                /* TestComponent_a0b5f2 */
                [data-djc-css-b9e76a] {
                    --bg_color: red;
                }
            </style>
            <style>
                /* TestComponent_a0b5f2 */
                [data-djc-css-c5e6ab] {
                    --bg_color: green;
                }
            </style>
            """,
        )

    def test_css_variables_empty_dict(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>Content</div>
                {% component_css_dependencies %}
            """
            css = """
                div {
                    color: red;
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return {}

        rendered = TestComponent.render()

        # Should not have CSS variables attribute when dict is empty
        assert "data-djc-css-" not in rendered

    def test_css_variables_none_returns_none(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>Content</div>
                {% component_css_dependencies %}
            """
            css = """
                div {
                    color: red;
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return None

        rendered = TestComponent.render()

        # Should not have CSS variables attribute when get_css_data returns None
        assert "data-djc-css-" not in rendered

    def test_css_variables_with_string_containing_spaces(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="text-box">Box</div>
                {% component_css_dependencies %}
            """
            css = """
                .text-box {
                    content: var(--text_content);
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "text_content": "Hello World",
                }

        rendered = TestComponent.render()

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED TestComponent_961494,ca1bc3e,,d335a4 -->
            <div class="text-box" data-djc-id-ca1bc3e data-djc-css-d335a4>Box</div>
            <style>
                .text-box {
                    content: var(--text_content);
                }
            </style>
            <style>
/* TestComponent_961494 */
[data-djc-css-d335a4] {
  --text_content: "Hello World";
}
</style>
            """,
        )

    def test_css_variables_with_css_functions(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="sized-box">Box</div>
                {% component_css_dependencies %}
            """
            css = """
                .sized-box {
                    width: var(--box_width);
                    background: var(--bg_gradient);
                    color: var(--text_color);
                }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "box_width": "calc(100% - 20px)",
                    "bg_gradient": "linear-gradient(to right, red, blue)",
                    "text_color": "rgba(255, 0, 0, 0.5)",
                }

        rendered = TestComponent.render()

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED TestComponent_5b14a4,ca1bc3e,,413e33 -->
            <div class="sized-box" data-djc-id-ca1bc3e data-djc-css-413e33>Box</div>
            <style>
                .sized-box {
                    width: var(--box_width);
                    background: var(--bg_gradient);
                    color: var(--text_color);
                }
            </style>
            <style>
/* TestComponent_5b14a4 */
[data-djc-css-413e33] {
  --box_width: calc(100% - 20px);
  --bg_gradient: linear-gradient(to right, red, blue);
  --text_color: rgba(255, 0, 0, 0.5);
}
</style>
            """,
        )
