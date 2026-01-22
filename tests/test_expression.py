"""Catch-all for tests that use template tags and don't fit other files"""

import re
from typing import Dict

import pytest
from django.template import Context, Template
from django.template.base import FilterExpression, Node, Parser, Token
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, registry, types
from django_components.expression import TemplateExpression
from django_components.testing import djc_test
from django_components.util.template_tag import is_aggregate_key

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


engine = Template("").engine
default_parser = Parser("", engine.template_libraries, engine.template_builtins)


# A tag that just returns the value, so we can
# check if the value is stringified
class NoopNode(Node):
    def __init__(self, expr: FilterExpression):
        self.expr = expr

    def render(self, context: Context):
        return self.expr.resolve(context)


def noop(parser: Parser, token: Token):
    _tag, raw_expr = token.split_contents()
    expr = parser.compile_filter(raw_expr)

    return NoopNode(expr)


def make_context(d: Dict):
    ctx = Context(d)
    ctx.template = Template("")
    return ctx


#######################
# TESTS
#######################


# NOTE: Django calls the `{{ }}` syntax "variables" and `{% %}` "blocks"
@djc_test
class TestTemplateExpression:
    def test_variable_resolve_template_expression(self):
        expr = TemplateExpression(
            "{{ var_a|lower }}",
            filters=default_parser.filters,
            tags=default_parser.tags,
        )

        ctx = make_context({"var_a": "LoREM"})
        assert expr.resolve(ctx) == "lorem"

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_variable_in_template(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["pos_var1"] = args[0]
                captured["bool_var"] = kwargs["bool_var"]
                captured["list_var"] = kwargs["list_var"]

                return {
                    "pos_var1": args[0],
                    "bool_var": kwargs["bool_var"],
                    "list_var": kwargs["list_var"],
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                "{{ var_a|lower }}"
                bool_var="{{ is_active }}"
                list_var="{{ list|slice:':-1' }}"
            / %}
            """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": "LoREM",
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                },
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["pos_var1"] == "lorem"
        assert captured["bool_var"] is True
        assert captured["list_var"] == [{"a": 1}, {"a": 2}]

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>lorem</div>
            <div data-djc-id-ca1bc3f>True</div>
            <div data-djc-id-ca1bc3f>[{'a': 1}, {'a': 2}]</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_block_in_template(self, components_settings):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["pos_var1"] = args[0]
                captured["bool_var"] = kwargs["bool_var"]
                captured["list_var"] = kwargs["list_var"]
                captured["dict_var"] = kwargs["dict_var"]

                return {
                    "pos_var1": args[0],
                    "bool_var": kwargs["bool_var"],
                    "list_var": kwargs["list_var"],
                    "dict_var": kwargs["dict_var"],
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
                <div>{{ dict_var|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                "{% lorem var_a w %}"
                bool_var="{% noop is_active %}"
                list_var="{% noop list %}"
                dict_var="{% noop dict %}"
            / %}
            """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                    "dict": {"a": 3},
                },
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["bool_var"] is True
        assert captured["dict_var"] == {"a": 3}
        assert captured["list_var"] == [{"a": 1}, {"a": 2}]

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_743413,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>lorem ipsum dolor</div>
            <div data-djc-id-ca1bc3f>True</div>
            <div data-djc-id-ca1bc3f>[{'a': 1}, {'a': 2}]</div>
            <div data-djc-id-ca1bc3f>{'a': 3}</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_comment_in_template(self, components_settings):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["pos_var1"] = args[0]
                captured["pos_var2"] = args[1]
                captured["bool_var"] = kwargs["bool_var"]
                captured["list_var"] = kwargs["list_var"]

                return {
                    "pos_var1": args[0],
                    "pos_var2": args[1],
                    "bool_var": kwargs["bool_var"],
                    "list_var": kwargs["list_var"],
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                "{# lorem var_a w #}"
                " {# lorem var_a w #} abc"
                bool_var="{# noop is_active #}"
                list_var=" {# noop list #} "
            / %}
            """

        template = Template(template_str)
        rendered: str = template.render(
            Context(
                {
                    "DJC_DEPS_STRATEGY": "ignore",
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                },
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["pos_var1"] == ""
        assert captured["pos_var2"] == "  abc"
        assert captured["bool_var"] == ""
        assert captured["list_var"] == "  "

        # NOTE: This is whitespace-sensitive test, so we check exact output
        assert rendered.strip() == (
            "<!-- _RENDERED SimpleComponent_3fd560,ca1bc3f,, -->\n"
            '                <div data-djc-id-ca1bc3f=""></div>\n'
            '                <div data-djc-id-ca1bc3f="">  abc</div>\n'
            '                <div data-djc-id-ca1bc3f=""></div>\n'
            '                <div data-djc-id-ca1bc3f="">  </div>'
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_mixed_in_template(self, components_settings):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["pos_var1"] = args[0]
                captured["bool_var"] = kwargs["bool_var"]
                captured["list_var"] = kwargs["list_var"]
                captured["dict_var"] = kwargs["dict_var"]

                return {
                    "pos_var1": args[0],
                    "pos_var2": args[1],
                    "bool_var": kwargs["bool_var"],
                    "list_var": kwargs["list_var"],
                    "dict_var": kwargs["dict_var"],
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
                <div>{{ dict_var|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                " {% lorem var_a w %} "
                " {% lorem var_a w %} {{ list|slice:':-1'|safe }} "
                bool_var=" {% noop is_active %} "
                list_var=" {% noop list %} "
                dict_var=" {% noop dict %} "
            / %}
            """

        template = Template(template_str)
        rendered: str = template.render(
            Context(
                {
                    "DJC_DEPS_STRATEGY": "ignore",
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                    "dict": {"a": 3},
                },
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["bool_var"] == " True "
        assert captured["dict_var"] == " {'a': 3} "
        assert captured["list_var"] == " [{'a': 1}, {'a': 2}] "

        # NOTE: This is whitespace-sensitive test, so we check exact output
        # fmt: off
        assert rendered.strip() == (
            "<!-- _RENDERED SimpleComponent_e51e4e,ca1bc3f,, -->\n"
            '                <div data-djc-id-ca1bc3f=""> lorem ipsum dolor </div>\n'
            '                <div data-djc-id-ca1bc3f=""> lorem ipsum dolor [{\'a\': 1}] </div>\n'
            '                <div data-djc-id-ca1bc3f=""> True </div>\n'
            '                <div data-djc-id-ca1bc3f=""> [{\'a\': 1}, {\'a\': 2}] </div>\n'
            '                <div data-djc-id-ca1bc3f=""> {\'a\': 3} </div>'
        )
        # fmt: on

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_ignores_invalid_tag(self, components_settings):
        registry.library.tag(noop)

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "pos_var1": args[0],
                    "pos_var2": args[1],
                    "bool_var": kwargs["bool_var"],
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' '"' "{%}" bool_var="{% noop is_active %}" / %}
            """

        template = Template(template_str)
        rendered = template.render(
            Context({"is_active": True}),
        )

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_c7a5c3,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>"</div>
            <div data-djc-id-ca1bc3f>{%}</div>
            <div data-djc-id-ca1bc3f>True</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_in_template(self, components_settings):
        registry.library.tag(noop)

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "pos_var1": args[0],
                    "bool_var": kwargs["bool_var"],
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                "{% component 'test' '{{ var_a }}' bool_var=is_active / %}"
                bool_var="{% noop is_active %}"
            / %}
            """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                },
            ),
        )

        assertHTMLEqual(
            rendered,
            """
                <!-- _RENDERED SimpleComponent_5c8766,ca1bc41,, -->
                <div data-djc-id-ca1bc41>
                    <!-- _RENDERED SimpleComponent_5c8766,ca1bc40,, -->
                    <div data-djc-id-ca1bc40>3</div>
                    <div data-djc-id-ca1bc40>True</div>
                </div>
                <div data-djc-id-ca1bc41>True</div>
            """,
        )


class TestSpreadOperator:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_later_spreads_can_overwrite_earlier(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {
                    **kwargs,
                }

            template: types.django_html = """
                <div>{{ attrs }}</div>
                <div>{{ items }}</div>
                <div>{{ a }}</div>
                <div>{{ x }}</div>
            """

        context = Context(
            {
                "my_dict": {
                    "attrs:@click": "() => {}",
                    "attrs:style": "height: 20px",
                    "items": [1, 2, 3],
                },
                "list": [
                    {"a": 1, "x": "OVERWRITTEN_X"},
                    {"a": 2},
                ],
            },
        )

        # Merging like this is fine - earlier spreads are overwritten by later spreads.
        template_str1: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                ...my_dict
                attrs:style="OVERWRITTEN"
                x=123
                ..."{{ list|first }}"
            / %}
            """

        template1 = Template(template_str1)
        rendered1 = template1.render(context)

        assertHTMLEqual(
            rendered1,
            """
            <div data-djc-id-ca1bc3f>{'@click': '() =&gt; {}', 'style': 'OVERWRITTEN'}</div>
            <div data-djc-id-ca1bc3f>[1, 2, 3]</div>
            <div data-djc-id-ca1bc3f>1</div>
            <div data-djc-id-ca1bc3f>OVERWRITTEN_X</div>
            """,
        )

        # But, similarly to python, we can merge multiple **kwargs by instead
        # merging them into a single dict, and spreading that.
        template_str2: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                ...{
                    **my_dict,
                    "x": 123,
                    **"{{ list|first }}",
                }
                attrs:style="OVERWRITTEN"
            / %}
            """

        template2 = Template(template_str2)
        rendered2 = template2.render(context)

        assertHTMLEqual(
            rendered2,
            """
            <div data-djc-id-ca1bc41>{'@click': '() =&gt; {}', 'style': 'OVERWRITTEN'}</div>
            <div data-djc-id-ca1bc41>[1, 2, 3]</div>
            <div data-djc-id-ca1bc41>1</div>
            <div data-djc-id-ca1bc41>OVERWRITTEN_X</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_on_missing_value(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                var_a
                ...
            / %}
            """

        with pytest.raises(SyntaxError, match=re.escape("Parse error")):
            Template(template_str)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_spread_list_and_iterables(self, components_settings):
        captured = None

        @register("test")
        class SimpleComponent(Component):
            template = ""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured
                captured = args, kwargs

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                ...var_a
                ...var_b
            / %}
            """
        template = Template(template_str)

        context = Context(
            {
                "var_a": "abc",
                "var_b": [1, 2, 3],
            },
        )

        template.render(context)

        assert captured == (
            ["a", "b", "c", 1, 2, 3],
            {},
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_on_non_dict(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                ...var_b
            / %}
            """

        template = Template(template_str)

        # List
        with pytest.raises(
            TypeError,
            match=re.escape("Value of '...var_b' must be a mapping or an iterable, not int"),
        ):
            template.render(Context({"var_b": 123}))


@djc_test
class TestAggregateKwargs:
    def test_aggregate_kwargs(self):
        captured = None

        @register("test")
        class Test(Component):
            template = ""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured
                captured = args, kwargs

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                attrs:@click.stop="dispatch('click_event')"
                attrs:x-data="{hello: 'world'}"
                attrs:class=class_var
                attrs::placeholder="No text"
                my_dict:one=2
                three=four
            / %}
        """

        template = Template(template_str)
        template.render(Context({"class_var": "padding-top-8", "four": 4}))

        assert captured == (
            [],
            {
                "attrs": {
                    "@click.stop": "dispatch('click_event')",
                    "x-data": "{hello: 'world'}",
                    "class": "padding-top-8",
                    ":placeholder": "No text",
                },
                "my_dict": {"one": 2},
                "three": 4,
            },
        )

    def test_is_aggregate_key(self):
        assert not is_aggregate_key("")
        assert not is_aggregate_key(" ")
        assert not is_aggregate_key(" : ")
        assert not is_aggregate_key("attrs")
        assert not is_aggregate_key(":attrs")
        assert not is_aggregate_key(" :attrs ")
        assert not is_aggregate_key("attrs:")
        assert not is_aggregate_key(":attrs:")
        assert is_aggregate_key("at:trs")
        assert not is_aggregate_key(":at:trs")


@djc_test
class TestPythonExpressions:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_python_expression_negating_boolean(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["disabled"] = kwargs["disabled"]
                return {"disabled": kwargs["disabled"]}

            template: types.django_html = """
                <div>{{ disabled }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' disabled=(not editable) / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({"editable": False}))

        assert captured["disabled"] is True
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>True</div>
            """,
        )

        # Test with True
        rendered = template.render(Context({"editable": True}))
        assert captured["disabled"] is False

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_python_expression_conditional(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["variant"] = kwargs["variant"]
                return {"variant": kwargs["variant"]}

            template: types.django_html = """
                <div>{{ variant }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' variant=(user.is_admin and 'danger' or 'primary') / %}
        """

        template = Template(template_str)

        # Test with admin user
        rendered = template.render(
            Context(
                {
                    "user": type("User", (), {"is_admin": True})(),
                }
            )
        )
        assert captured["variant"] == "danger"
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>danger</div>
            """,
        )

        # Test with regular user
        rendered = template.render(
            Context(
                {
                    "user": type("User", (), {"is_admin": False})(),
                }
            )
        )
        assert captured["variant"] == "primary"

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_python_expression_method_calls(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["text"] = kwargs["text"]
                return {"text": kwargs["text"]}

            template: types.django_html = """
                <div>{{ text }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' text=(name.upper()) / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({"name": "hello"}))

        assert captured["text"] == "HELLO"
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>HELLO</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_python_expression_arithmetic(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["score"] = kwargs["score"]
                return {"score": kwargs["score"]}

            template: types.django_html = """
                <div>{{ score }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' score=(user.points + bonus_points) / %}
        """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "user": type("User", (), {"points": 100})(),
                    "bonus_points": 25,
                }
            )
        )

        assert captured["score"] == 125
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>125</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_python_expression_with_filter(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["text"] = kwargs["text"]
                return {"text": kwargs["text"]}

            template: types.django_html = """
                <div>{{ text }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' text=(name.upper())|lower / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({"name": "Hello"}))

        assert captured["text"] == "hello"
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>hello</div>
            """,
        )


@djc_test
class TestLiteralListsAndDicts:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_list_simple(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["items"] = kwargs["items"]
                return {"items": kwargs["items"]}

            template: types.django_html = """
                <div>{{ items|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' items=[1, 2, 3, 4, 5] / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({}))

        assert captured["items"] == [1, 2, 3, 4, 5]
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>[1, 2, 3, 4, 5]</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_list_with_variables(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["items"] = kwargs["items"]
                return {"items": kwargs["items"]}

            template: types.django_html = """
                <div>{{ items|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' items=[user.name, user.email, "extra"] / %}
        """

        template = Template(template_str)
        rendered = template.render(
            Context({"user": type("User", (), {"name": "John", "email": "john@example.com"})()})
        )

        assert captured["items"] == ["John", "john@example.com", "extra"]
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>['John', 'john@example.com', 'extra']</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_list_with_filters(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["items"] = kwargs["items"]
                return {"items": kwargs["items"]}

            template: types.django_html = """
                <div>{{ items|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' items=["John"|upper, "Jane"|upper] / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({}))

        assert captured["items"] == ["JOHN", "JANE"]
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>['JOHN', 'JANE']</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_list_with_filter_on_list(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["items"] = kwargs["items"]
                return {"items": kwargs["items"]}

            template: types.django_html = """
                <div>{{ items|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' items=["John", "Jane", "Bob"]|slice:":2" / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({}))

        assert captured["items"] == ["John", "Jane"]
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>['John', 'Jane']</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_dict_simple(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["config"] = kwargs["config"]
                return {"config": kwargs["config"]}

            template: types.django_html = """
                <div>{{ config|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' config={"title": "Hello", "count": 5, "active": True} / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({}))

        assert captured["config"] == {"title": "Hello", "count": 5, "active": True}
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>{'title': 'Hello', 'count': 5, 'active': True}</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_dict_with_variables(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["config"] = kwargs["config"]
                return {"config": kwargs["config"]}

            template: types.django_html = """
                <div>{{ config|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' config={"name": user.name, "count": count} / %}
        """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "user": type("User", (), {"name": "John"})(),
                    "count": 10,
                }
            )
        )

        assert captured["config"] == {"name": "John", "count": 10}
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>{'name': 'John', 'count': 10}</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_nested_structures(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["data"] = kwargs["data"]
                return {"data": kwargs["data"]}

            template: types.django_html = """
                <div>{{ data|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test'
                data=[
                    {
                        "name": "John",
                        "hobbies": ["reading", "coding"],
                        "meta": {"age": 30, "active": True}
                    }
                ]
            / %}
        """

        template = Template(template_str)
        rendered = template.render(Context({}))

        expected_data = [
            {
                "name": "John",
                "hobbies": ["reading", "coding"],
                "meta": {"age": 30, "active": True},
            }
        ]
        assert captured["data"] == expected_data
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>[{'name': 'John', 'hobbies': ['reading', 'coding'], 'meta': {'age': 30, 'active': True}}]</div>
            """,  # noqa: E501
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_list_with_python_expressions(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["items"] = kwargs["items"]
                return {"items": kwargs["items"]}

            template: types.django_html = """
                <div>{{ items|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' items=[(not user.active), False, True] / %}
        """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "user": type("User", (), {"active": False})(),
                }
            )
        )

        assert captured["items"] == [True, False, True]
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>[True, False, True]</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_literal_dict_with_python_expressions(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                captured["config"] = kwargs["config"]
                return {"config": kwargs["config"]}

            template: types.django_html = """
                <div>{{ config|safe }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' config={"disabled": (not editable), "count": (len(items))} / %}
        """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "editable": False,
                    "items": [1, 2, 3],
                    "len": len,
                }
            )
        )

        assert captured["config"] == {"disabled": True, "count": 3}
        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,ca1bc3f,, -->
            <div data-djc-id-ca1bc3f>{'disabled': True, 'count': 3}</div>
            """,
        )
