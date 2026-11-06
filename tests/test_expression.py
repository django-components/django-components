"""Catch-all for tests that use template tags and don't fit other files"""

import re
from functools import partial

import pytest
from django.template import Context, Template
from django.template.base import FilterExpression, Node, Parser, Token
from django.utils.functional import SimpleLazyObject, lazy, lazystr
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString, mark_safe
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy, ngettext_lazy, pgettext_lazy
from djc_core.safe_eval import SecurityError
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, registry, types
from django_components.expression import TemplateExpression
from django_components.testing import djc_test
from django_components.util.template_tag import is_aggregate_key, resolve_python_expression

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


def make_context(d: dict):
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
    def test_multinode_expression_in_component_preserves_render_error_in_debug(self, components_settings):
        def explode(value, _arg=None):
            raise ValueError(f"boom: {value}")

        registry.library.filter("explode_1597", explode)

        @register("test")
        class SimpleComponent(Component):
            template: types.django_html = "{{ value }}"

            def get_template_data(self, args, kwargs, slots, context):
                return {"value": kwargs["value"]}

        template = Template(
            """
            {% load component_tags %}
            {% component 'test' value="prefix {{ value|explode_1597 }}" / %}
            """
        )

        old_debug = template.engine.debug
        template.engine.debug = True
        try:
            with pytest.raises(ValueError, match="boom: bad"):
                template.render(Context({"value": "bad"}))
        finally:
            template.engine.debug = old_debug

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_multinode_expression_nodes_get_real_origin(self, components_settings):
        # A multi-node expression (text + variable) is wrapped in `StringifiedNode`. With the
        # host origin threaded into the `Parser`, the wrapped nodes carry the host template's
        # origin instead of `None`, so Django's debug-mode annotator can locate the source.
        captured = {}

        @register("test")
        class SimpleComponent(Component):
            template: types.django_html = "{{ value }}"

            def get_template_data(self, args, kwargs, slots, context):
                captured["value"] = kwargs["value"]
                return {"value": kwargs["value"]}

        template = Template(
            """
            {% load component_tags %}
            {% component 'test' value="prefix {{ value }}" / %}
            """
        )

        old_debug = template.engine.debug
        template.engine.debug = True
        try:
            template.render(Context({"value": "X"}))
        finally:
            template.engine.debug = old_debug

        assert captured["value"] == "prefix X"

    def test_stringified_node_fallback_origin_without_host_origin(self):
        # When a node has no origin (e.g. an expression built outside a `Template.render()`),
        # `StringifiedNode.render` falls back to the currently-rendering template's origin.
        # This guards the `is None` branch, which the previous `hasattr` guard left as dead code.
        from django.template import NodeList

        from django_components.expression import StringifiedNode

        inner = Template("{{ value }}")
        wrapped = inner.nodelist[0]
        # Simulate a node parsed without a host origin.
        if hasattr(wrapped, "origin"):
            wrapped.origin = None

        node = StringifiedNode(wrapped)
        assert node.origin is None  # nothing real to copy at construction time

        ctx = Context({"value": "Y"})
        ctx.render_context.template = inner  # what `Template._render` sets during rendering
        nodelist = NodeList([node])

        assert nodelist.render(ctx) == "Y"
        assert node.origin is inner.origin  # fallback populated a real origin

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

    # See https://github.com/django-components/django-components/issues/1255
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_on_separate_line(self, components_settings):
        @register("ListItem")
        class ListItemComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"attrs": kwargs.get("attrs", {})}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "ListItem"
                attrs:hx-trigger="click[window.location.pathname != '{{ module_url }}']"
                attrs:class="
                    {{ module_classes }}
                    project-nav--item
                    w-full mt-0 shadow
                "
            / %}
        """

        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "module_url": "/test/url",
                    "module_classes": "dynamic-class",
                }
            )
        )

        assertHTMLEqual(
            rendered,
            """
            <div
                class="dynamic-class mt-0 project-nav--item shadow w-full"
                data-djc-id-ca1bc3f
                hx-trigger="click[window.location.pathname != '/test/url']"
            >
                content
            </div>
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


class HiddenMarker:
    """Holds a value that an expression must not be able to read."""

    _hidden = "HIDDEN-MARKER"


class ForwardingObject:
    """Forwards attribute reads to another object, as many wrapper classes do."""

    def __init__(self, target):
        self.target = target

    def __getattr__(self, name):
        return getattr(self.target, name)


class FormatMethodOwner:
    """An ordinary class that happens to have a `format` method and a `format_map` field."""

    format_map = "a4"

    def format(self):
        return "formatted"


def evaluate(code, **context):
    # The real resolver, so that these tests cover the checks the template tags use.
    return resolve_python_expression(context, "", (0, 0), {}, {}, code)


PATH_TEXT = "{0._hidden}"
KEYED_PATH_TEXT = "{item._hidden}"


@djc_test
class TestPythonExpressionFormatting:
    def render_show(self, template_str, context):
        @register("show")
        class Show(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"text": kwargs["text"]}

            template: types.django_html = """
                <div>{{ text }}</div>
            """

        return Template("{% load component_tags %}" + template_str).render(Context(context))

    # Only the template text chooses the format text here: the app passes no lazy string in.
    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("{0._hidden}", id="private_attribute"),
            pytest.param("{0.__class__.__name__}", id="dunder_attribute"),
        ],
    )
    def test_translation_in_template_cannot_format(self, text):
        template_str = '{% with x=_("' + text + '") %}{% component "show" text=(x.format(obj)) / %}{% endwith %}'
        with pytest.raises(SecurityError):
            self.render_show(template_str, {"obj": HiddenMarker()})

    def test_translation_in_template_cannot_format_itself(self):
        # The lazy string is its own argument, so the path needs no object from the app.
        template_str = (
            '{% with x=_("{0.__init__.__globals__}") %}{% component "show" text=(x.format(x)) / %}{% endwith %}'
        )
        with pytest.raises(SecurityError):
            self.render_show(template_str, {})

    def test_lazy_string_from_context_cannot_format(self):
        with pytest.raises(SecurityError):
            self.render_show(
                '{% component "show" text=(x.format(obj)) / %}',
                {"x": gettext_lazy(PATH_TEXT), "obj": HiddenMarker()},
            )

    @pytest.mark.parametrize(
        "make_text",
        [
            pytest.param(lambda: gettext_lazy(PATH_TEXT), id="gettext_lazy"),
            pytest.param(lambda: pgettext_lazy("menu", PATH_TEXT), id="pgettext_lazy"),
            pytest.param(lambda: ngettext_lazy(PATH_TEXT, PATH_TEXT, 1), id="ngettext_lazy_number"),
            pytest.param(lambda: ngettext_lazy(PATH_TEXT, PATH_TEXT, "n"), id="ngettext_lazy_key"),
            pytest.param(lambda: lazystr(PATH_TEXT), id="lazystr"),
            pytest.param(lambda: lazy(str, str)(PATH_TEXT), id="lazy"),
            pytest.param(lambda: mark_safe(gettext_lazy(PATH_TEXT)), id="mark_safe_of_lazy"),
            pytest.param(lambda: format_lazy("{}", PATH_TEXT), id="format_lazy_result"),
            pytest.param(lambda: SimpleLazyObject(lambda: gettext_lazy(PATH_TEXT)), id="simple_lazy_object"),
            pytest.param(lambda: ForwardingObject(gettext_lazy(PATH_TEXT)), id="forwarding_object"),
            # These count as `str` for `isinstance`, so `safe_eval` must refuse them without the
            # hooks in `template_tag.py`.
            pytest.param(lambda: SafeString(PATH_TEXT), id="safe_string"),
            pytest.param(lambda: mark_safe(PATH_TEXT), id="mark_safe"),
            pytest.param(lambda: SimpleLazyObject(lambda: PATH_TEXT), id="simple_lazy_object_of_str"),
        ],
    )
    def test_format_refused_on_string_like_objects(self, make_text):
        with pytest.raises(SecurityError):
            evaluate("x.format(obj)", x=make_text(), obj=HiddenMarker())

    @pytest.mark.parametrize(
        "make_text",
        [
            pytest.param(lambda: gettext_lazy(KEYED_PATH_TEXT), id="gettext_lazy"),
            pytest.param(lambda: SimpleLazyObject(lambda: gettext_lazy(KEYED_PATH_TEXT)), id="simple_lazy_object"),
            pytest.param(lambda: ForwardingObject(gettext_lazy(KEYED_PATH_TEXT)), id="forwarding_object"),
        ],
    )
    def test_format_map_refused_on_lazy_strings(self, make_text):
        with pytest.raises(SecurityError):
            evaluate("x.format_map(values)", x=make_text(), values={"item": HiddenMarker()})

    # The check runs on each attribute read, so try the ways an expression can write one.
    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("(lambda value: x.format(value))(obj)", id="lambda"),
            pytest.param("[x.format(value) for value in [obj]]", id="comprehension"),
            pytest.param("f'{x.format(obj)}'", id="f_string"),
            pytest.param("(y := x).format(obj)", id="walrus"),
            pytest.param("(x if True else '').format(obj)", id="conditional"),
            pytest.param("[x][0].format(obj)", id="subscript"),
        ],
    )
    def test_lazy_string_method_refused_in_each_expression_form(self, code):
        with pytest.raises(SecurityError):
            evaluate(code, x=gettext_lazy(PATH_TEXT), obj=HiddenMarker())

    @pytest.mark.parametrize("code", ["cls.format(x, obj)", "cls.upper(x)"], ids=["format", "upper"])
    def test_lazy_string_class_attribute_refused(self, code):
        lazy_text = gettext_lazy(PATH_TEXT)
        with pytest.raises(SecurityError):
            evaluate(code, cls=type(lazy_text), x=lazy_text, obj=HiddenMarker())

    @pytest.mark.parametrize("code", ["cls.format(x, obj)", "cls.upper(x)"], ids=["format", "upper"])
    def test_lazy_string_class_inside_simple_lazy_object_attribute_refused(self, code):
        lazy_text = gettext_lazy(PATH_TEXT)
        cls = SimpleLazyObject(lambda: type(lazy_text))
        with pytest.raises(SecurityError):
            evaluate(code, cls=cls, x=lazy_text, obj=HiddenMarker())

    @pytest.mark.parametrize(
        "make_function",
        [
            pytest.param(lambda text: text.format, id="bound_method"),
            pytest.param(lambda text: text.format_map, id="bound_format_map"),
            pytest.param(lambda text: partial(text.format), id="partial"),
            pytest.param(lambda text: partial(partial(text.format)), id="nested_partial"),
            pytest.param(lambda text: text.upper, id="upper"),
            pytest.param(lambda text: partial(text.upper), id="partial_of_upper"),
        ],
    )
    def test_lazy_string_method_from_context_cannot_be_called(self, make_function):
        function = make_function(gettext_lazy(PATH_TEXT))
        with pytest.raises(SecurityError):
            evaluate("function(obj)", function=function, obj=HiddenMarker())

    @pytest.mark.parametrize(
        ("function", "args"),
        [
            pytest.param(format_lazy, ("{0._hidden}", HiddenMarker()), id="format_lazy"),
            # `format_html()` escapes its arguments, but the escaped text still has a
            # `__html__` method, and the path can start there.
            pytest.param(format_html, ("{0.__html__.__name__}", "text"), id="format_html"),
            pytest.param(format_html_join, ("", "{0.__html__.__name__}", [("text",)]), id="format_html_join"),
            pytest.param(partial(format_lazy, "{0._hidden}"), (HiddenMarker(),), id="partial_of_format_lazy"),
        ],
    )
    def test_django_format_functions_cannot_be_called(self, function, args):
        with pytest.raises(SecurityError):
            evaluate("function(*args)", function=function, args=args)

    def test_lazy_string_plain_method_is_refused(self):
        with pytest.raises(SecurityError):
            evaluate("x.upper()", x=gettext_lazy("hello"))

    def test_lazy_string_method_cannot_be_redirected(self):
        # A forwarding method takes a keyword that picks the method to run, so every name is refused.
        with pytest.raises(SecurityError):
            evaluate("x.upper(obj, __method_name='format')", x=gettext_lazy(PATH_TEXT), obj=HiddenMarker())

    def test_lazy_string_redirected_method_in_template_is_refused(self):
        template_str = (
            '{% with x=_("{0._hidden}") %}'
            "{% component \"show\" text=(x.upper(obj, __method_name='format')) / %}"
            "{% endwith %}"
        )
        with pytest.raises(SecurityError):
            self.render_show(template_str, {"obj": HiddenMarker()})

    def test_lazy_string_operators_and_f_strings_keep_working(self):
        text = gettext_lazy("hello")
        assert evaluate("x + ' world'", x=text) == "hello world"
        assert evaluate("f'{x} world'", x=text) == "hello world"
        # An f-string gives a plain `str`, which is how to reach the string methods.
        assert evaluate("f'{x}'.upper()", x=text) == "HELLO"

    def test_lazy_string_percent_formatting_keeps_working(self):
        assert evaluate("x % name", x=gettext_lazy("Hello %s"), name="Ann") == "Hello Ann"

    def test_f_string_with_translation_in_template_keeps_working(self):
        template_str = """
            {% with x=_("Hello") %}
                {% component "show" text=(f"{x} {name}") / %}
                {% component "show" text=(f"{x}".upper()) / %}
            {% endwith %}
        """
        rendered = self.render_show(template_str, {"name": "Ann"})
        assert "Hello Ann" in rendered
        assert "HELLO" in rendered

    def test_format_of_other_objects_keeps_working(self):
        owner = FormatMethodOwner()
        assert evaluate("owner.format()", owner=owner) == "formatted"
        assert evaluate("owner.format_map", owner=owner) == "a4"
        assert evaluate("function()", function=partial(owner.format)) == "formatted"
        assert evaluate("wrapped.format()", wrapped=SimpleLazyObject(lambda: owner)) == "formatted"

    def test_lazy_object_of_any_result_class_is_refused(self):
        # The check looks only at `Promise`, not at the type the object will produce, so a
        # result that is not text is refused too.
        lazy_owner = lazy(FormatMethodOwner, FormatMethodOwner)()
        with pytest.raises(SecurityError):
            evaluate("owner.format()", owner=lazy_owner)


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
