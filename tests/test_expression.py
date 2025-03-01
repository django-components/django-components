"""Catch-all for tests that use template tags and don't fit other files"""

import re
from typing import Any, Dict

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.template.base import FilterExpression, Node, Parser, Token
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, registry, types
from django_components.expression import DynamicFilterExpression, is_aggregate_key

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


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
    tag, raw_expr = token.split_contents()
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
class TestDynamicExpr:
    def test_variable_resolve_dynamic_expr(self):
        expr = DynamicFilterExpression(default_parser, '"{{ var_a|lower }}"')

        ctx = make_context({"var_a": "LoREM"})
        assert expr.resolve(ctx) == "lorem"

    def test_variable_raises_on_dynamic_expr_with_quotes_mismatch(self):
        with pytest.raises(TemplateSyntaxError):
            DynamicFilterExpression(default_parser, "'{{ var_a|lower }}\"")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_variable_in_template(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var

                return {
                    "pos_var1": pos_var1,
                    "bool_var": bool_var,
                    "list_var": list_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{{ var_a|lower }}"
                bool_var="{{ is_active }}"
                list_var="{{ list|slice:':-1' }}"
            / %}
            """
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": "LoREM",
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["pos_var1"] == "lorem"
        assert captured["bool_var"] is True
        assert captured["list_var"] == [{"a": 1}, {"a": 2}]

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_5b8d97,a1bc3f,, -->
            <div data-djc-id-a1bc3f>lorem</div>
            <div data-djc-id-a1bc3f>True</div>
            <div data-djc-id-a1bc3f>[{'a': 1}, {'a': 2}]</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_block_in_template(self, components_settings):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
                dict_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var
                captured["dict_var"] = dict_var

                return {
                    "pos_var1": pos_var1,
                    "bool_var": bool_var,
                    "list_var": list_var,
                    "dict_var": dict_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
                <div>{{ dict_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{% lorem var_a w %}"
                bool_var="{% noop is_active %}"
                list_var="{% noop list %}"
                dict_var="{% noop dict %}"
            / %}
            """
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                    "dict": {"a": 3},
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["bool_var"] is True
        assert captured["dict_var"] == {"a": 3}
        assert captured["list_var"] == [{"a": 1}, {"a": 2}]

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_743413,a1bc3f,, -->
            <div data-djc-id-a1bc3f>lorem ipsum dolor</div>
            <div data-djc-id-a1bc3f>True</div>
            <div data-djc-id-a1bc3f>[{'a': 1}, {'a': 2}]</div>
            <div data-djc-id-a1bc3f>{'a': 3}</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_comment_in_template(self, components_settings):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                pos_var2: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["pos_var2"] = pos_var2
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var

                return {
                    "pos_var1": pos_var1,
                    "pos_var2": pos_var2,
                    "bool_var": bool_var,
                    "list_var": list_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{# lorem var_a w #}"
                " {# lorem var_a w #} abc"
                bool_var="{# noop is_active #}"
                list_var=" {# noop list #} "
            / %}
            """
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["pos_var1"] == ""
        assert captured["pos_var2"] == "  abc"
        assert captured["bool_var"] == ""
        assert captured["list_var"] == "  "

        # NOTE: This is whitespace-sensitive test, so we check exact output
        assert rendered.strip() == (
            "<!-- _RENDERED SimpleComponent_6f07b3,a1bc3f,, -->\n"
            '                <div data-djc-id-a1bc3f=""></div>\n'
            '                <div data-djc-id-a1bc3f="">  abc</div>\n'
            '                <div data-djc-id-a1bc3f=""></div>\n'
            '                <div data-djc-id-a1bc3f="">  </div>'
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_mixed_in_template(self, components_settings):
        registry.library.tag(noop)
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                pos_var2: Any,
                *args: Any,
                bool_var: bool,
                list_var: Dict,
                dict_var: Dict,
            ):
                captured["pos_var1"] = pos_var1
                captured["bool_var"] = bool_var
                captured["list_var"] = list_var
                captured["dict_var"] = dict_var

                return {
                    "pos_var1": pos_var1,
                    "pos_var2": pos_var2,
                    "bool_var": bool_var,
                    "list_var": list_var,
                    "dict_var": dict_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
                <div>{{ list_var|safe }}</div>
                <div>{{ dict_var|safe }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                " {% lorem var_a w %} "
                " {% lorem var_a w %} {{ list|slice:':-1'|safe }} "
                bool_var=" {% noop is_active %} "
                list_var=" {% noop list %} "
                dict_var=" {% noop dict %} "
            / %}
            """
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                    "list": [{"a": 1}, {"a": 2}],
                    "dict": {"a": 3},
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["bool_var"] == " True "
        assert captured["dict_var"] == " {'a': 3} "
        assert captured["list_var"] == " [{'a': 1}, {'a': 2}] "

        # NOTE: This is whitespace-sensitive test, so we check exact output
        assert rendered.strip() == (
            "<!-- _RENDERED SimpleComponent_85c7eb,a1bc3f,, -->\n"
            '                <div data-djc-id-a1bc3f=""> lorem ipsum dolor </div>\n'
            '                <div data-djc-id-a1bc3f=""> lorem ipsum dolor [{\'a\': 1}] </div>\n'
            '                <div data-djc-id-a1bc3f=""> True </div>\n'
            '                <div data-djc-id-a1bc3f=""> [{\'a\': 1}, {\'a\': 2}] </div>\n'
            '                <div data-djc-id-a1bc3f=""> {\'a\': 3} </div>'
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_ignores_invalid_tag(self, components_settings):
        registry.library.tag(noop)

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                pos_var2: Any,
                *args: Any,
                bool_var: bool,
            ):
                return {
                    "pos_var1": pos_var1,
                    "pos_var2": pos_var2,
                    "bool_var": bool_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ pos_var2 }}</div>
                <div>{{ bool_var }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test' '"' "{%}" bool_var="{% noop is_active %}" / %}
            """
        )

        template = Template(template_str)
        rendered = template.render(
            Context({"is_active": True}),
        )

        assertHTMLEqual(
            rendered,
            """
            <!-- _RENDERED SimpleComponent_c7a5c3,a1bc3f,, -->
            <div data-djc-id-a1bc3f>"</div>
            <div data-djc-id-a1bc3f>{%}</div>
            <div data-djc-id-a1bc3f>True</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_in_template(self, components_settings):
        registry.library.tag(noop)

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                bool_var: bool,
            ):
                return {
                    "pos_var1": pos_var1,
                    "bool_var": bool_var,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ bool_var }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                "{% component 'test' '{{ var_a }}' bool_var=is_active / %}"
                bool_var="{% noop is_active %}"
            / %}
            """
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": 3,
                    "is_active": True,
                }
            ),
        )

        assertHTMLEqual(
            rendered,
            """
                <!-- _RENDERED SimpleComponent_5c8766,a1bc41,, -->
                <div data-djc-id-a1bc41>
                    <!-- _RENDERED SimpleComponent_5c8766,a1bc40,, -->
                    <div data-djc-id-a1bc40>3</div>
                    <div data-djc-id-a1bc40>True</div>
                </div>
                <div data-djc-id-a1bc41>True</div>
            """
        )


class TestSpreadOperator:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component(self, components_settings):
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                pos_var1: Any,
                *args: Any,
                **kwargs: Any,
            ):
                nonlocal captured
                captured = kwargs

                return {
                    "pos_var1": pos_var1,
                    **kwargs,
                }

            template: types.django_html = """
                <div>{{ pos_var1 }}</div>
                <div>{{ attrs }}</div>
                <div>{{ items }}</div>
                <div>{{ a }}</div>
                <div>{{ x }}</div>
            """

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                var_a
                ...my_dict
                ..."{{ list|first }}"
                x=123
            / %}
            """
        )

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": "LoREM",
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }
            ),
        )

        # Check that variables passed to the component are of correct type
        assert captured["attrs"] == {"@click": "() => {}", "style": "height: 20px"}
        assert captured["items"] == [1, 2, 3]
        assert captured["a"] == 1
        assert captured["x"] == 123

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc3f>LoREM</div>
            <div data-djc-id-a1bc3f>{'@click': '() =&gt; {}', 'style': 'height: 20px'}</div>
            <div data-djc-id-a1bc3f>[1, 2, 3]</div>
            <div data-djc-id-a1bc3f>1</div>
            <div data-djc-id-a1bc3f>123</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slot(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(self):
                return {
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }

            template: types.django_html = """
                {% load component_tags %}
                {% slot "my_slot" ...my_dict ..."{{ list|first }}" x=123 default / %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "my_slot" data="slot_data" %}
                    {{ slot_data }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            {'items': [1, 2, 3], 'a': 1, 'x': 123, 'attrs': {'@click': '() =&gt; {}', 'style': 'height: 20px'}}
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_fill(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(self):
                return {
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }

            template: types.django_html = """
                {% load component_tags %}
                {% slot "my_slot" ...my_dict ..."{{ list|first }}" x=123 default %}
                    __SLOT_DEFAULT__
                {% endslot %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' %}
                {% fill "my_slot" ...fill_data %}
                    {{ slot_data }}
                    {{ slot_default }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "fill_data": {
                        "data": "slot_data",
                        "default": "slot_default",
                    },
                }
            ),
        )

        assertHTMLEqual(
            rendered,
            """
            {'items': [1, 2, 3], 'a': 1, 'x': 123, 'attrs': {'@click': '() =&gt; {}', 'style': 'height: 20px'}}
            __SLOT_DEFAULT__
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(self):
                data = self.inject("test")
                return {
                    "attrs": data.attrs,
                    "items": data.items,
                    "a": data.a,
                }

            template: types.django_html = """
                {% load component_tags %}
                <div>{{ attrs }}</div>
                <div>{{ items }}</div>
                <div>{{ a }}</div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide 'test' ...my_dict ..."{{ list|first }}" %}
                {% component 'test' / %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "my_dict": {
                        "attrs:@click": "() => {}",
                        "attrs:style": "height: 20px",
                        "items": [1, 2, 3],
                    },
                    "list": [{"a": 1}, {"a": 2}, {"a": 3}],
                }
            ),
        )

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41>{'@click': '() =&gt; {}', 'style': 'height: 20px'}</div>
            <div data-djc-id-a1bc41>[1, 2, 3]</div>
            <div data-djc-id-a1bc41>1</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_html_attrs(self, components_settings):
        template_str: types.django_html = """
            {% load component_tags %}
            <div {% html_attrs defaults:test="hi" ...my_dict attrs:lol="123" %}>
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "my_dict": {
                        "attrs:style": "height: 20px",
                        "class": "button",
                        "defaults:class": "my-class",
                        "defaults:style": "NONO",
                    },
                }
            ),
        )
        assertHTMLEqual(
            rendered,
            """
            <div test="hi" class="my-class button" style="height: 20px" lol="123">
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_later_spreads_do_not_overwrite_earlier(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            def get_context_data(
                self,
                *args: Any,
                **kwargs: Any,
            ):
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
                "list": [{"a": 1, "x": "OVERWRITTEN_X"}, {"a": 2}, {"a": 3}],
            }
        )

        # Mergingg like this will raise TypeError, because it's like
        # a function receiving multiple kwargs with the same name.
        template_str1: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                ...my_dict
                attrs:style="OVERWRITTEN"
                x=123
                ..."{{ list|first }}"
            / %}
            """
        )

        template1 = Template(template_str1)

        with pytest.raises(TypeError, match=re.escape("got multiple values for argument 'x'")):
            template1.render(context)

        # But, similarly to python, we can merge multiple **kwargs by instead
        # merging them into a single dict, and spreading that.
        template_str2: types.django_html = (
            """
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
        )

        template2 = Template(template_str2)
        rendered2 = template2.render(context)

        assertHTMLEqual(
            rendered2,
            """
            <div data-djc-id-a1bc40>{'@click': '() =&gt; {}', 'style': 'OVERWRITTEN'}</div>
            <div data-djc-id-a1bc40>[1, 2, 3]</div>
            <div data-djc-id-a1bc40>1</div>
            <div data-djc-id-a1bc40>OVERWRITTEN_X</div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_on_missing_value(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                var_a
                ...
            / %}
            """
        )

        with pytest.raises(TemplateSyntaxError, match=re.escape("Spread syntax '...' is missing a value")):
            Template(template_str)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_spread_list_and_iterables(self, components_settings):
        captured = None

        @register("test")
        class SimpleComponent(Component):
            template = ""

            def get_context_data(self, *args, **kwargs):
                nonlocal captured
                captured = args, kwargs
                return {}

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                ...var_a
                ...var_b
            / %}
            """
        )
        template = Template(template_str)

        context = Context(
            {
                "var_a": "abc",
                "var_b": [1, 2, 3],
            }
        )

        template.render(context)

        assert captured == (
            ("a", "b", "c", 1, 2, 3),
            {},
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_on_non_dict(self, components_settings):
        @register("test")
        class SimpleComponent(Component):
            pass

        template_str: types.django_html = (
            """
            {% load component_tags %}
            {% component 'test'
                ...var_b
            / %}
            """
        )

        template = Template(template_str)

        # List
        with pytest.raises(
            ValueError,
            match=re.escape("Cannot spread non-iterable value: '...var_b' resolved to 123")
        ):
            template.render(Context({"var_b": 123}))


@djc_test
class TestAggregateKwargs:
    def test_aggregate_kwargs(self):
        captured = None

        @register("test")
        class Test(Component):
            template = ""

            def get_context_data(self, *args, **kwargs):
                nonlocal captured
                captured = args, kwargs
                return {}

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
            (),
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
