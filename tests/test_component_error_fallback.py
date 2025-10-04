from typing import NamedTuple

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, ErrorFallback, register, types
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestErrorFallbackComponent:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_basic__python(self, components_settings):
        # 1. Content does not raise, fallback present
        rendered1 = ErrorFallback.render(
            slots={
                "content": lambda _data: "SAFE CONTENT",
                "fallback": lambda _data: "FALLBACK CONTENT",
            },
        )
        assert rendered1.strip() == "SAFE CONTENT"

        # 2. Content raises, fallback present
        def error_content(_ctx):
            raise Exception("fail!")

        rendered2 = ErrorFallback.render(
            slots={
                "content": error_content,
                "fallback": lambda _data: "FALLBACK CONTENT",
            },
        )
        assert rendered2.strip() == "FALLBACK CONTENT"

        # 3. Content raises, fallback missing - valid
        rendered3 = ErrorFallback.render(
            slots={
                "content": error_content,
            },
        )
        assert rendered3.strip() == ""

        # 4. Same as 3., but with default slot
        rendered4 = ErrorFallback.render(
            slots={
                "default": error_content,
            },
        )
        assert rendered4.strip() == ""

        # 5. Content missing, fallback present - valid
        rendered5 = ErrorFallback.render(
            slots={
                "fallback": lambda _ctx: "FALLBACK CONTENT",
            },
        )
        assert rendered5.strip() == ""

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_basic__template(self, components_settings):
        @register("broken")
        class BrokenComponent(Component):
            def on_render(self, context: Context, template: Template):
                raise Exception("fail!")

        # 1. Content does not raise, fallback present
        template_str1: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% fill "content" %}SAFE CONTENT{% endfill %}
                {% fill "fallback" %}FALLBACK CONTENT{% endfill %}
            {% endcomponent %}
        """
        template1 = Template(template_str1)
        rendered1 = template1.render(Context({}))

        assert "SAFE CONTENT" in rendered1
        assert "FALLBACK CONTENT" not in rendered1

        # 2. Content raises, fallback present
        template_str2: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% fill "content" %}
                    {% component "broken" / %}
                {% endfill %}
                {% fill "fallback" %}
                    FALLBACK CONTENT
                {% endfill %}
            {% endcomponent %}
        """
        template2 = Template(template_str2)
        rendered2 = template2.render(Context({}))
        assert "FALLBACK CONTENT" in rendered2

        # 3. Content raises, fallback missing - valid
        template_str3: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% fill "content" %}
                    {% component "broken" / %}
                {% endfill %}
            {% endcomponent %}
        """
        template3 = Template(template_str3)
        rendered3 = template3.render(Context({}))
        assert rendered3.strip() == ""

        # 4. Same as 3., but with default slot
        template_str4: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% component "broken" / %}
            {% endcomponent %}
        """
        template4 = Template(template_str4)
        rendered4 = template4.render(Context({}))
        assert rendered4.strip() == ""

        # 5. Content missing, fallback present - valid
        template_str5: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% fill "fallback" %}FALLBACK CONTENT{% endfill %}
            {% endcomponent %}
        """
        template5 = Template(template_str5)
        rendered5 = template5.render(Context({}))
        assert rendered5.strip() == ""

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_default_slot(self, components_settings):
        @register("test")
        class SimpleSlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot: {% slot "default" default / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs["variable"],
                    "variable2": kwargs.get("variable2", "default"),
                }

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}
                    HELLO_FROM_SLOT
                {% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>
            Slot: HELLO_FROM_SLOT
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_fallback_as_kwarg__python(self, components_settings):
        # Content does not raise, fallback kwarg present
        rendered1 = ErrorFallback.render(
            slots={
                "content": lambda _ctx: "SAFE CONTENT",
            },
            kwargs={
                "fallback": "FALLBACK CONTENT",
            },
        )
        assert rendered1.strip() == "SAFE CONTENT"

        # Content raises, fallback kwarg present
        def error_content(_ctx):
            raise Exception("fail!")

        rendered2 = ErrorFallback.render(
            slots={
                "content": error_content,
            },
            kwargs={
                "fallback": "FALLBACK CONTENT",
            },
        )
        assert rendered2.strip() == "FALLBACK CONTENT"

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_fallback_as_kwarg__template(self, components_settings):
        @register("broken")
        class BrokenComponent(Component):
            def on_render(self, context: Context, template: Template):
                raise Exception("fail!")

        # Content does not raise, fallback kwarg present
        template_str1: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" fallback="FALLBACK CONTENT" %}
                SAFE CONTENT
            {% endcomponent %}
        """
        template1 = Template(template_str1)
        rendered1 = template1.render(Context({}))
        assert "SAFE CONTENT" in rendered1
        assert "FALLBACK CONTENT" not in rendered1

        # Content raises, fallback kwarg present
        template_str2: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" fallback="FALLBACK CONTENT" %}
                {% component "broken" / %}
            {% endcomponent %}
        """
        template2 = Template(template_str2)
        rendered2 = template2.render(Context({}))
        assert "FALLBACK CONTENT" in rendered2

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_on_fallback_as_both_slot_and_kwarg(self, components_settings):
        # Python API: fallback as both slot and kwarg
        with pytest.raises(
            TemplateSyntaxError,
            match=r"The 'fallback' argument and slot cannot both be provided. Please provide only one.",
        ):
            ErrorFallback.render(
                slots={
                    "content": lambda _ctx: "SAFE CONTENT",
                    "fallback": lambda _ctx: "FALLBACK CONTENT",
                },
                kwargs={
                    "fallback": "FALLBACK CONTENT",
                },
            )

        # Template API: fallback as both slot and kwarg
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" fallback="FALLBACK CONTENT" %}
                {% fill "fallback" %}FALLBACK CONTENT{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        with pytest.raises(
            TemplateSyntaxError,
            match=r"The 'fallback' argument and slot cannot both be provided. Please provide only one.",
        ):
            template.render(Context({}))

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_error_fallback_inside_loop(self, components_settings):
        @register("sometimes_broken")
        class SometimesBrokenComponent(Component):
            template: types.django_html = """
                Item: {{ item_name }}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "item_name": kwargs.get("item_name", "default"),
                }

            def on_render(self, context: Context, template: Template):
                if self.kwargs.get("should_break", False):
                    raise Exception("fail!")
                return super().on_render(context, template)

        # Test error fallback inside a loop with some items failing
        template_str: types.django_html = """
            {% load component_tags %}
            {% for item in items %}
                {% component "error_fallback" %}
                    {% fill "content" %}
                        {% component "sometimes_broken" item_name=item.name should_break=item.should_break / %}
                    {% endfill %}
                    {% fill "fallback" %}
                        ERROR: Failed to render {{ item.name }}
                    {% endfill %}
                {% endcomponent %}
            {% endfor %}
        """

        template = Template(template_str)
        context_data = {
            "items": [
                {"name": "item1", "should_break": False},
                {"name": "item2", "should_break": True},
                {"name": "item3", "should_break": False},
                {"name": "item4", "should_break": True},
            ]
        }
        rendered = template.render(Context(context_data))

        expected = """
            Item: item1
            ERROR: Failed to render item2
            Item: item3
            ERROR: Failed to render item4
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_error_fallback_nested_inside_another(self, components_settings):
        @register("broken")
        class BrokenComponent(Component):
            class Kwargs(NamedTuple):
                msg: str

            def on_render(self, context: Context, template: Template):
                raise Exception(self.kwargs.msg)

        # Test nested error fallback components
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "error_fallback" %}
                {% fill "content" %}
                    {% if should_outer_fail %}
                        {% component "broken" msg="OUTER_FAIL" / %}
                    {% endif %}
                    OUTER_CONTENT_START
                    {% component "error_fallback" %}
                        {% fill "content" %}
                            {% component "broken" msg="INNER_FAIL" / %}
                        {% endfill %}
                        {% fill "fallback" data="data" %}
                            {% if should_inner_fallback_fail %}
                                {% component "broken" msg="INNER_FALLBACK_FAIL" / %}
                            {% else %}
                                INNER_FALLBACK: {{ data.error }}
                            {% endif %}
                        {% endfill %}
                    {% endcomponent %}
                    OUTER_CONTENT_END
                {% endfill %}
                {% fill "fallback" data="data" %}
                    OUTER_FALLBACK: {{ data.error }}
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        rendered1 = template.render(Context({}))
        if components_settings["context_behavior"] == "django":
            expected1 = """
                OUTER_CONTENT_START
                INNER_FALLBACK: An error occured while rendering components error_fallback > broken: INNER_FAIL
                OUTER_CONTENT_END
            """
        else:
            expected1 = """
                OUTER_CONTENT_START
                INNER_FALLBACK: An error occured while rendering components error_fallback(slot:content) > broken: INNER_FAIL
                OUTER_CONTENT_END
            """  # noqa: E501
        assertHTMLEqual(rendered1, expected1)

        rendered2 = template.render(Context({"should_outer_fail": True}))
        if components_settings["context_behavior"] == "django":
            expected2 = """
                OUTER_FALLBACK: An error occured while rendering components broken: OUTER_FAIL
            """
        else:
            expected2 = """
                OUTER_FALLBACK: An error occured while rendering components error_fallback(slot:content) > broken: OUTER_FAIL
            """  # noqa: E501
        assertHTMLEqual(rendered2, expected2)

        # Test when inner fallback also fails
        rendered3 = template.render(Context({"should_inner_fallback_fail": True}))
        if components_settings["context_behavior"] == "django":
            expected3 = """
                OUTER_FALLBACK: An error occured while rendering components error_fallback > broken > broken: INNER_FALLBACK_FAIL
            """  # noqa: E501
        else:
            expected3 = """
                OUTER_FALLBACK: An error occured while rendering components error_fallback(slot:content) > error_fallback > error_fallback(slot:fallback) > broken: INNER_FALLBACK_FAIL
            """  # noqa: E501
        assertHTMLEqual(rendered3, expected3)
