import json
import re
from types import MappingProxyType
from typing import Any

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe
from pytest_django.asserts import assertHTMLEqual

from django_components import AttrsDict, Component, compose_attrs, register, types
from django_components.attributes import format_attributes, merge_attributes, parse_string_style
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


@djc_test
class TestFormatAttributes:
    def test_simple_attribute(self):
        assert format_attributes({"foo": "bar"}) == 'foo="bar"'

    def test_multiple_attributes(self):
        assert format_attributes({"class": "foo", "style": "color: red;"}) == 'class="foo" style="color: red;"'

    def test_escapes_special_characters(self):
        assert (
            format_attributes({"x-on:click": "bar", "@click": "'baz'"}) == 'x-on:click="bar" @click="&#x27;baz&#x27;"'
        )

    def test_does_not_escape_special_characters_if_safe_string(self):
        assert format_attributes({"foo": mark_safe("'bar'")}) == "foo=\"'bar'\""

    def test_result_is_safe_string(self):
        result = format_attributes({"foo": mark_safe("'bar'")})
        assert isinstance(result, SafeString)

    def test_attribute_with_no_value(self):
        assert format_attributes({"required": None}) == ""

    def test_attribute_with_false_value(self):
        assert format_attributes({"required": False}) == ""

    def test_attribute_with_true_value(self):
        assert format_attributes({"required": True}) == "required"

    def test_normalizes_structured_class_and_style(self):
        assert (
            format_attributes(
                {
                    "class": ["button", {"active": True}],
                    "style": ["color: red;", {"color": "blue"}],
                },
            )
            == 'class="button active" style="color: blue;"'
        )

    def test_omits_empty_structured_class_and_style(self):
        assert format_attributes({"class": {"hidden": False}, "style": {"color": False}}) == ""

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "bad name",
            "bad\tname",
            "bad\nname",
            "bad\rname",
            "bad=name",
            "bad/name",
            "bad>name",
            "bad<name",
            "bad{#name",
        ],
    )
    def test_rejects_invalid_attribute_name(self, name):
        with pytest.raises(ValueError, match="invalid HTML attribute name"):
            format_attributes({name: "value"})

    def test_rejects_non_string_attribute_name(self):
        with pytest.raises(TypeError, match="must use string attribute names"):
            format_attributes({1: "value"})  # type: ignore[dict-item]

    def test_strips_custom_markup_behavior_from_attribute_name(self):
        class UnsafeName(str):
            __slots__ = ()

            def __html__(self):
                return 'title onmouseover="unsafe"'

        assert format_attributes({UnsafeName("title"): "safe"}) == 'title="safe"'


@djc_test
class TestComposeAttrs:
    def test_returns_attrs_dict(self):
        result = compose_attrs({"id": "one"})

        assert isinstance(result, AttrsDict)
        assert isinstance(result, dict)
        assert result == {"id": "one"}

    def test_flattens_nested_sources_at_any_depth(self):
        source = {"id": "first", "class": "base"}
        nested: Any = {"title": "deep"}
        for _ in range(1_100):
            nested = [nested]

        result = compose_attrs([source, [[{"class": "active"}]], nested], {"id": "last"})

        assert result == {
            "id": "last",
            "class": "base active",
            "title": "deep",
        }

    def test_accepts_nested_tuples(self):
        result = compose_attrs(({"id": "one"}, ({"title": "two"},)), {"role": "button"})

        assert result == {"id": "one", "title": "two", "role": "button"}

    def test_accepts_non_dict_mapping_leaves(self):
        result = compose_attrs([MappingProxyType({"id": "one"})])

        assert result == {"id": "one"}

    def test_ordinary_keys_use_last_value(self):
        result = compose_attrs(
            {"id": "first", "disabled": True},
            [{"id": "last", "disabled": False}],
        )

        assert result == {"id": "last", "disabled": False}

    def test_merges_class_and_style(self):
        result = compose_attrs(
            {
                "class": "base removable",
                "style": "color: red; width: 10px;",
            },
            [
                {
                    "class": {"active": True, "removable": False},
                    "style": {"color": "blue", "width": False},
                },
            ],
        )

        assert result == {
            "class": "base active",
            "style": "color: blue;",
        }

    def test_none_class_and_style_contributions_are_ignored(self):
        result = compose_attrs(
            {"class": "base", "style": "color: red;"},
            {"class": None, "style": None},
        )

        assert result == {"class": "base", "style": "color: red;"}

    def test_preserves_first_seen_key_order(self):
        result = compose_attrs(
            {"id": "first", "class": "base"},
            {"title": "hello", "id": "last", "class": "active"},
        )

        assert list(result) == ["id", "class", "title"]

    def test_does_not_mutate_sources(self):
        first = {"class": ["base"], "id": "one"}
        second = {"class": {"active": True}, "id": "two"}

        compose_attrs(first, second)

        assert first == {"class": ["base"], "id": "one"}
        assert second == {"class": {"active": True}, "id": "two"}

    def test_rejects_non_mapping_leaf(self):
        with pytest.raises(TypeError, match="mapping or a nested list or tuple of mappings"):
            compose_attrs([{"id": "one"}, ["not-a-mapping"]])  # type: ignore[list-item]

    def test_rejects_cyclic_sources(self):
        cyclic: list = []
        cyclic.append(cyclic)

        with pytest.raises(ValueError, match="cannot contain a cycle"):
            compose_attrs(cyclic)

    def test_allows_reusing_the_same_source_container(self):
        shared: Any = [{"class": "shared"}]

        result = compose_attrs([shared, shared])

        assert result == {"class": "shared"}


@djc_test
class TestAttrsDict:
    def test_stringifies_as_escaped_html_attributes(self):
        attrs = compose_attrs({"title": "<unsafe>", "disabled": True, "hidden": False})

        assert str(attrs) == 'title="&lt;unsafe&gt;" disabled'

    def test_does_not_mark_itself_safe_in_an_attribute_value(self):
        attrs = compose_attrs({"title": "hello"})

        assert format_attributes({"data-attrs": attrs}) == 'data-attrs="title=&quot;hello&quot;"'

    def test_retains_mapping_behavior(self):
        attrs = compose_attrs({"id": "one", "class": "button"})

        assert {**attrs} == {"id": "one", "class": "button"}
        assert json.loads(json.dumps(attrs)) == {"id": "one", "class": "button"}


@djc_test
class TestAttrsTag:
    def test_serializes_nested_sources(self):
        template = Template(
            """
            {% load component_tags %}
            <div {% attrs [first, [second]] third %}></div>
            """,
        )

        rendered = template.render(
            Context(
                {
                    "first": {"id": "first", "class": "base"},
                    "second": {"class": "active", "title": "<unsafe>"},
                    "third": {"id": "last", "disabled": True},
                },
            ),
        )

        assertHTMLEqual(
            rendered,
            '<div id="last" class="base active" title="&lt;unsafe&gt;" disabled></div>',
        )

    def test_passes_attrs_dict_from_exact_nested_template(self):
        captured = {}

        @register("attrs_receiver")
        class AttrsReceiver(Component):
            template: types.django_html = ""

            def get_template_data(self, args, kwargs, slots, context):
                captured["attrs"] = kwargs["attrs"]
                return {}

        template = Template(
            """
            {% load component_tags %}
            {% component "attrs_receiver"
                attrs="{% attrs [first, [second]] {'class': 'local'} %}"
            / %}
            """,
        )

        template.render(
            Context(
                {
                    "first": {"id": "first", "class": "base"},
                    "second": {"id": "last", "class": "active"},
                },
            ),
        )

        assert isinstance(captured["attrs"], AttrsDict)
        assert captured["attrs"] == {"id": "last", "class": "base active local"}

    def test_surrounding_text_stringifies_attrs(self):
        captured = {}

        @register("attrs_string_receiver")
        class AttrsStringReceiver(Component):
            template: types.django_html = ""

            def get_template_data(self, args, kwargs, slots, context):
                captured["attrs"] = kwargs["attrs"]
                return {}

        template = Template(
            """
            {% load component_tags %}
            {% component "attrs_string_receiver"
                attrs="prefix {% attrs {'title': '<unsafe>'} %}"
            / %}
            """,
        )

        template.render(Context({}))

        assert captured["attrs"] == 'prefix title="&lt;unsafe&gt;"'

    def test_serialization_error_is_annotated_in_debug_mode(self):
        class ExplodingValue:
            def __str__(self):
                raise ValueError("cannot serialize")

        template = Template(
            """
            {% load component_tags %}
            <div {% attrs attrs %}></div>
            """,
        )
        old_debug = template.engine.debug
        template.engine.debug = True
        try:
            with pytest.raises(ValueError, match="cannot serialize") as exc_info:
                template.render(Context({"attrs": {"title": ExplodingValue()}}))
        finally:
            template.engine.debug = old_debug

        assert hasattr(exc_info.value, "template_debug")


@djc_test
class TestMergeAttributes:
    def test_single_dict(self):
        assert merge_attributes({"foo": "bar"}) == {"foo": "bar"}

    def test_appends_dicts(self):
        assert merge_attributes({"class": "foo", "id": "bar"}, {"class": "baz"}) == {
            "class": "foo baz",
            "id": "bar",
        }

    def test_merge_with_empty_dict(self):
        assert merge_attributes({}, {"foo": "bar"}) == {"foo": "bar"}

    def test_merge_with_overlapping_keys(self):
        assert merge_attributes({"foo": "bar"}, {"foo": "baz"}) == {"foo": "bar baz"}

    def test_merge_classes(self):
        assert merge_attributes(
            {"class": "foo"},
            {
                "class": [
                    "bar",
                    "tuna",
                    "tuna2",
                    "tuna3",
                    {"baz": True, "baz2": False, "tuna": False, "tuna2": True, "tuna3": None},
                    ["extra", {"extra2": False, "baz2": True, "tuna": True, "tuna2": False}],
                ],
            },
        ) == {"class": "foo bar tuna baz baz2 extra"}

    def test_merge_styles(self):
        assert merge_attributes(
            {"style": "color: red; width: 100px; height: 100px;"},
            {
                "style": [
                    "background-color: blue;",
                    {"background-color": "green", "color": None, "width": False},
                    ["position: absolute", {"height": "12px"}],
                ],
            },
        ) == {"style": "color: red; height: 12px; background-color: green; position: absolute;"}

    def test_merge_with_none_values(self):
        # Normal attributes merge even `None` values
        assert merge_attributes({"foo": None}, {"foo": "bar"}) == {"foo": "None bar"}
        assert merge_attributes({"foo": "bar"}, {"foo": None}) == {"foo": "bar None"}

        # Classes append the class only if the last value is truthy
        assert merge_attributes({"class": {"bar": None}}, {"class": {"bar": True}}) == {"class": "bar"}
        assert merge_attributes({"class": {"bar": True}}, {"class": {"bar": None}}) == {"class": ""}

        # Styles remove values that are `False` and ignore `None`
        assert merge_attributes(
            {"style": {"color": None}},
            {"style": {"color": "blue"}},
        ) == {"style": "color: blue;"}
        assert merge_attributes(
            {"style": {"color": "blue"}},
            {"style": {"color": None}},
        ) == {"style": "color: blue;"}

    def test_merge_with_false_values(self):
        # Normal attributes merge even `False` values
        assert merge_attributes({"foo": False}, {"foo": "bar"}) == {"foo": "False bar"}
        assert merge_attributes({"foo": "bar"}, {"foo": False}) == {"foo": "bar False"}

        # Classes append the class only if the last value is truthy
        assert merge_attributes({"class": {"bar": False}}, {"class": {"bar": True}}) == {"class": "bar"}
        assert merge_attributes({"class": {"bar": True}}, {"class": {"bar": False}}) == {"class": ""}

        # Styles remove values that are `False` and ignore `None`
        assert merge_attributes(
            {"style": {"color": False}},
            {"style": {"color": "blue"}},
        ) == {"style": "color: blue;"}
        assert merge_attributes(
            {"style": {"color": "blue"}},
            {"style": {"color": False}},
        ) == {"style": ""}


@djc_test
class TestHtmlAttrs:
    template_str: types.django_html = """
        {% load component_tags %}
        {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
        {% endcomponent %}
    """  # noqa: E501

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_tag_positional_args(self, components_settings):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs defaults class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs["attrs"],
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class another-class" data-djc-id-ca1bc3f data-id=123>
                content
            </div>
            """,  # noqa: E501
        )
        assert "override-me" not in rendered

    def test_tag_raises_on_extra_positional_args(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs defaults class %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs["attrs"],
                    "defaults": {"class": "override-me"},
                    "class": "123 457",
                }

        template = Template(self.template_str)

        with pytest.raises(
            TypeError,
            match=re.escape(
                "takes from 0 to 2 positional arguments but 3 were given",
            ),
        ):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_tag_kwargs(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs=attrs defaults=defaults class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs["attrs"],
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" class="added_class another-class padding-top-8" data-djc-id-ca1bc3f data-id="123" x-data="{hello: 'world'}">
                content
            </div>
            """,  # noqa: E501
        )
        assert "override-me" not in rendered

    def test_tag_kwargs_2(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs class="added_class" class="another-class" data-id=123 defaults=defaults attrs=attrs %}>
                    content
                </div>
            """  # noqa: E501

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs["attrs"],
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class another-class" data-djc-id-ca1bc3f data-id=123>
                content
            </div>
            """,  # noqa: E501
        )
        assert "override-me" not in rendered

    def test_tag_spread(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs ...props class="another-class" %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "props": {
                        "attrs": kwargs["attrs"],
                        "defaults": {"class": "override-me"},
                        "class": "added_class",
                        "data-id": 123,
                    },
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" class="added_class another-class padding-top-8" data-djc-id-ca1bc3f data-id="123" x-data="{hello: 'world'}">
                content
            </div>
            """,  # noqa: E501
        )
        assert "override-me" not in rendered

    def test_tag_aggregate_args(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs:class="from_agg_key" attrs:type="submit" defaults:class="override-me" class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_template_data(self, args, kwargs, slots, context):
                return {"attrs": kwargs["attrs"]}

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))

        # NOTE: The attrs from self.template_str should be ignored because they are not used.
        assertHTMLEqual(
            rendered,
            """
            <div class="added_class another-class from_agg_key" data-djc-id-ca1bc3f data-id="123" type="submit">
                content
            </div>
            """,
        )
        assert "override-me" not in rendered

    # Note: Because there's both `attrs:class` and `defaults:class`, the `attrs`,
    # it's as if the template tag call was (ignoring the `class` and `data-id` attrs):
    #
    # `{% html_attrs attrs={"class": ...} defaults={"class": ...} attrs %}>content</div>`
    #
    # Which raises, because `attrs` is passed both as positional and as keyword argument.
    def test_tag_raises_on_aggregate_and_positional_args_for_attrs(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs attrs:class="from_agg_key" defaults:class="override-me" class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_template_data(self, args, kwargs, slots, context):
                return {"attrs": kwargs["attrs"]}

        template = Template(self.template_str)

        with pytest.raises(
            TypeError,
            match=re.escape("got multiple values for argument 'attrs'"),
        ):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_tag_raises_on_aggregate_and_positional_args_for_defaults(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs
                    defaults={"key": "val"}
                    attrs:class="from_agg_key"
                    defaults:class="override-me"
                    class="added_class"
                    class="another-class"
                    data-id=123
                %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"attrs": kwargs["attrs"]}

        template = Template(self.template_str)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Received argument 'defaults' both as a regular input"),
        ):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_tag_no_attrs(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs defaults:class="override-me" class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """  # noqa: E501

            def get_template_data(self, args, kwargs, slots, context):
                return {"attrs": kwargs["attrs"]}

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div class="added_class another-class override-me" data-djc-id-ca1bc3f data-id=123>
                content
            </div>
            """,
        )

    def test_tag_no_defaults(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"attrs": kwargs["attrs"]}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var %}
            {% endcomponent %}
        """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div @click.stop="dispatch('click_event')" x-data="{hello: 'world'}" class="padding-top-8 added_class another-class" data-djc-id-ca1bc3f data-id=123>
                content
            </div>
            """,  # noqa: E501
        )
        assert "override-me" not in rendered

    def test_tag_no_attrs_no_defaults(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs class="added_class" class="another-class" data-id=123 %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"attrs": kwargs["attrs"]}

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div class="added_class another-class" data-djc-id-ca1bc3f data-id="123">
                content
            </div>
            """,
        )
        assert "override-me" not in rendered

    def test_tag_empty(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs["attrs"],
                    "defaults": {"class": "override-me"},
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3f>
                content
            </div>
            """,
        )
        assert "override-me" not in rendered

    def test_tag_null_attrs_and_defaults(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs defaults %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": None,
                    "defaults": None,
                }

        template = Template(self.template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3f>
                content
            </div>
            """,
        )
        assert "override-me" not in rendered

    def test_duplicate_class_with_variable_and_literal(self):
        """Test that duplicate class attributes with a variable and literal are merged correctly."""

        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs
                    class=btn_class
                    class="inline-flex w-full text-sm"
                  %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs.get("attrs", {}),
                    "btn_class": "px-3 py-2 justify-center rounded-md shadow-sm",
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            <div class="px-3 py-2 justify-center rounded-md shadow-sm inline-flex w-full text-sm" data-djc-id-ca1bc3f>
                content
            </div>
            """,
        )

    def test_duplicate_style_with_variable_and_literal(self):
        """Test that duplicate style attributes with a variable and literal are merged correctly."""

        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs attrs
                    style=base_style
                    style="color: red; font-weight: bold;"
                  %}>
                    content
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs.get("attrs", {}),
                    "base_style": "padding: 10px; margin: 5px;",
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        # The styles should be merged, with later values taking precedence for same properties
        assert "padding: 10px" in rendered or "padding:10px" in rendered
        assert "margin: 5px" in rendered or "margin:5px" in rendered
        assert "color: red" in rendered or "color:red" in rendered
        assert "font-weight: bold" in rendered or "font-weight:bold" in rendered


@djc_test
class TestParseStringStyle:
    def test_single_style(self):
        assert parse_string_style("color: red;") == {"color": "red"}

    def test_multiple_styles(self):
        assert parse_string_style("color: red; background-color: blue;") == {
            "color": "red",
            "background-color": "blue",
        }

    def test_with_comments(self):
        assert parse_string_style("color: red /* comment */; background-color: blue;") == {
            "color": "red",
            "background-color": "blue",
        }

    def test_with_whitespace(self):
        assert parse_string_style("  color: red;  background-color: blue;  ") == {
            "color": "red",
            "background-color": "blue",
        }

    def test_empty_string(self):
        assert parse_string_style("") == {}

    def test_no_delimiters(self):
        assert parse_string_style("color: red background-color: blue") == {"color": "red background-color: blue"}

    def test_incomplete_style(self):
        assert parse_string_style("color: red; background-color") == {"color": "red"}
