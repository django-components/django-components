import pytest
from django.template import Context, Template
from django.test import RequestFactory
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, Script, Style, register, types
from django_components.cache import get_component_media_cache
from django_components.dependencies import cached_script_view
from django_components.testing import djc_test
from django_components.util.css import is_css_func, serialize_css_var_name, serialize_css_var_value

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


class TestCssValueSerialization:
    @pytest.mark.parametrize(
        "value",
        [
            "red",
            "10px",
            "-1.5em",
            "100%",
            "#ff0000",
            "calc(100% - 20px)",
            "rgba(0, 0, 0, 0.5)",
            "var(--a, red)",
            "linear-gradient(to right, red, blue)",
            "url(/a.png)",
            "url( /a.png )",
            "url(data:image/png;base64,AA==)",
            'url("/a b.png")',
            "url('/a.png')",
            '"text"',
            "'text'",
            "a,b",
            "1px/2px",
            "calc(1;2)",
            'f(a,"b;}c")',
            "xurl(a)",
            "URL(/a.png)",
            "",
        ],
    )
    def test_keeps_text_that_reads_as_one_value(self, value):
        assert serialize_css_var_value(value) == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, ""),
            (1, "1"),
            (1.5, "1.5"),
            (True, "True"),
            (["a", "b"], "\"['a', 'b']\""),
            ("Hello World", '"Hello World"'),
            ("10px 20px", '"10px 20px"'),
            ("a\tb", '"a\\9 b"'),
        ],
    )
    def test_converts_other_values(self, value, expected):
        assert serialize_css_var_value(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # A semicolon or brace would end the declaration or the rule.
            ("red;", '"red;"'),
            ("a;}b{c:d}", '"a;}b{c:d}"'),
            ("red}", '"red}"'),
            ("a{b", '"a{b"'),
            ("red!important", '"red!important"'),
            # A broken string or url() swallows the text after it.
            ("O'Brien", '"O\'Brien"'),
            ('"abc', '"\\"abc"'),
            ("url(a;b", '"url(a;b"'),
            ('url(a"x)y;b{c:d}z")', '"url(a\\"x)y;b{c:d}z\\")"'),
            ("url(a b)", '"url(a b)"'),
            ("url(a(b)", '"url(a(b)"'),
            ("url(a\x7fb)", '"url(a\\7f b)"'),
            # A quote inside a value with whitespace must not end the string that wraps it.
            ('a b";}b{c:d}.x{--a:"', '"a b\\";}b{c:d}.x{--a:\\""'),
            # A backslash could spell any character the check looks for.
            ("\\75rl(a;b)", '"\\\\75rl(a;b)"'),
            ("red\\", '"red\\\\"'),
            # Comments and unbalanced brackets.
            ("a/**/b", '"a/**/b"'),
            ("calc(1", '"calc(1"'),
            ("1)", '"1)"'),
            ("([)]", '"([)]"'),
            # Text before `url(` decides whether it starts a URL token.
            ("\x80url(x", '"\\80 url(x"'),
        ],
    )
    def test_quotes_text_that_could_leave_its_declaration(self, value, expected):
        assert serialize_css_var_value(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("</style>", '"\\3c /style>"'),
            ("</STYLE>", '"\\3c /STYLE>"'),
            ("<!--", '"\\3c !--"'),
            ('"</style>"', '"\\3c /style>"'),
            ('"\\</style>"', '"\\3c /style>"'),
            ('url("</style>")', 'url("\\3c /style>")'),
            ("url(</style>)", "url(\\3c /style>)"),
            ("red;}</STYLE><script>x</script>", '"red;}\\3c /STYLE>\\3c script>x\\3c /script>"'),
        ],
    )
    def test_writes_no_raw_less_than_sign(self, value, expected):
        assert serialize_css_var_value(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("caf\xe9", "caf\\e9 "),
            ('"\xe9"', '"\\e9 "'),
            ("a b\xe9", '"a b\\e9 "'),
            ('"\u4e2d\\""', '"\\4e2d \\""'),
            ('"\\\xe9"', '"\\e9 "'),
            ("\x1b", "\\1b "),
            ("a\x00b", '"a\\0 b"'),
            ("a\ud800b", '"a\\d800 b"'),
        ],
    )
    def test_writes_only_ascii(self, value, expected):
        result = serialize_css_var_value(value)
        assert result == expected
        assert result.isascii()
        # A lone surrogate must not fail when the cached stylesheet is encoded.
        result.encode()

    def test_str_subclass_cannot_hide_its_text(self):
        class Hidden(str):
            __slots__ = ()

            def __str__(self):
                return "red"

        # `str()` is what writes the value, so that is the text the check must read.
        assert serialize_css_var_value(Hidden("a;b")) == "red"

    def test_object_str_is_checked(self):
        class Evil:
            def __str__(self):
                return "a;}b{c:d}"

        assert serialize_css_var_value(Evil()) == '"a;}b{c:d}"'

    def test_number_subclass_str_is_checked(self):
        class Evil(int):
            def __str__(self):
                return "1;}b{c:d}"

        assert serialize_css_var_value(Evil(1)) == '"1;}b{c:d}"'

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("button_bg", "button_bg"),
            ("a-b", "a-b"),
            (1, "1"),
            ("a:red;}b{c:d}", "a\\3a red\\3b \\7d b\\7b c\\3a d\\7d "),
            ("a b", "a\\20 b"),
            ("a\nb", "a\\a b"),
            ("</style", "\\3c \\2f style"),
            ("\xe9", "\\e9 "),
            ("a\x00", "a\\0 "),
            ("a\ud800", "a\\d800 "),
        ],
    )
    def test_name_stays_one_name(self, name, expected):
        assert serialize_css_var_name(name) == expected


@djc_test
class TestCssDataReachingThePage:
    def _component(self):
        class CssDataComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="box">x</div>
                {% component_css_dependencies %}
            """
            css = """
                .box { color: var(--col); }
            """

            def get_css_data(self, args, kwargs, slots, context):
                return kwargs

        return CssDataComponent

    @pytest.mark.parametrize(
        "value",
        [
            "x</style",
            "</STYLE><script>document.title='x'</script><style>",
            "red;}</sTyLe ><script>document.title='x'</script>",
        ],
    )
    def test_value_cannot_end_style_element_or_fail_the_render(self, value):
        rendered = str(self._component().render(kwargs={"col": value}))
        assert "<script" not in rendered.rpartition("</style>")[2]
        assert rendered.lower().count("</style") == rendered.lower().count("<style")

    def test_value_with_surrogate_renders(self):
        assert "\\d800 " in str(self._component().render(kwargs={"col": "\ud800"}))

    def test_key_cannot_add_a_rule(self):
        rendered = str(self._component().render(kwargs={"a:red;}body{color:red}.x{--b": "x"}))
        assert "body{" not in rendered
        assert "--a\\3a red\\3b \\7d body\\7b color\\3a red\\7d \\2e x\\7b --b: x;" in rendered

    def test_route_serves_the_same_text_as_utf8(self):
        component = self._component()
        rendered = str(component.render(kwargs={"col": 'a b";}\u4e2d'}))
        variables_hash = rendered.partition("data-djc-css-")[2][:6]

        response = cached_script_view(RequestFactory().get("/"), component.class_id, "css", variables_hash)

        assert response["Content-Type"] == "text/css; charset=utf-8"
        assert '--col: "a b\\";}\\4e2d ";' in response.content.decode("ascii")
        assert response.content.decode("ascii") in rendered

    def test_old_stylesheet_in_a_lasting_cache_is_not_used(self):
        component = self._component()
        value = "red;}body{color:red}"
        rendered = str(component.render(kwargs={"col": value}))
        variables_hash = rendered.partition("data-djc-css-")[2][:6]

        # An older version stored its stylesheet under this key.
        old_key = f"__components:{component.class_id}:css:{variables_hash}"
        get_component_media_cache().set(old_key, "UNUSED")
        assert "UNUSED" not in str(component.render(kwargs={"col": value}))


class TestEndTagInScriptAndStyle:
    @pytest.mark.parametrize("content", ["a</style>", "a</STYLE>", "a</StYlE ", "a</stYLE"])
    def test_style_refuses_end_tag_in_any_letter_case(self, content):
        with pytest.raises(RuntimeError, match="end tag"):
            Style(content=content).render()

    @pytest.mark.parametrize("content", ["a</script>", "a</SCRIPT>", "a</ScRiPt "])
    def test_script_refuses_end_tag_in_any_letter_case(self, content):
        with pytest.raises(RuntimeError, match="end tag"):
            Script(content=content).render()


class TestServedContentType:
    @pytest.mark.parametrize(
        ("script_type", "expected"),
        [("js", "text/javascript; charset=utf-8"), ("css", "text/css; charset=utf-8")],
    )
    def test_names_the_charset(self, script_type, expected):
        class ServedComponent(Component):
            template = "<div>x</div>"
            css = ".a { content: '\u4e2d'; }"
            js = "console.log('\u4e2d')"

        str(ServedComponent.render())
        response = cached_script_view(RequestFactory().get("/"), ServedComponent.class_id, script_type)

        assert response["Content-Type"] == expected
        assert "\u4e2d" in response.content.decode("utf-8")


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
            <div class="themed-button" data-djc-id-ca1bc3e data-djc-css-468e36>Button</div>
            <style>
                .themed-button {
                    background-color: var(--button_bg);
                    color: var(--button_color);
                }
            </style>
            <style>
/* TestComponent_0c4787 */
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
