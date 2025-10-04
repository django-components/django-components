import re

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.utils.safestring import SafeString, mark_safe
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
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
                "Invalid parameters for tag 'html_attrs': takes 2 positional argument(s) but more were given",
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
            match=re.escape("Invalid parameters for tag 'html_attrs': got multiple values for argument 'attrs'"),
        ):
            template.render(Context({"class_var": "padding-top-8"}))

    def test_tag_raises_on_aggregate_and_positional_args_for_defaults(self):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div {% html_attrs
                    defaults=defaults
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
