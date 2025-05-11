"""
Tests focusing on the Python part of slots.
For tests focusing on the `{% slot %}` tag, see `test_templatetags_slot_fill.py`
"""

import re
from typing import Dict

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.template.base import NodeList, TextNode
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.slots import Slot, SlotRef

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


# Test interaction of the `Slot` instances with Component rendering
@djc_test
class TestSlot:
    @djc_test(
        parametrize=(
            ["components_settings", "is_isolated"],
            [
                [{"context_behavior": "django"}, False],
                [{"context_behavior": "isolated"}, True],
            ],
            ["django", "isolated"],
        )
    )
    def test_render_slot_as_func(self, components_settings, is_isolated):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" required data1="abc" data2:hello="world" data2:one=123 %}
                    SLOT_DEFAULT
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "the_arg": args[0],
                    "the_kwarg": kwargs.pop("the_kwarg", None),
                    "kwargs": kwargs,
                }

        def first_slot(ctx: Context, slot_data: Dict, slot_ref: SlotRef):
            assert isinstance(ctx, Context)
            # NOTE: Since the slot has access to the Context object, it should behave
            # the same way as it does in templates - when in "isolated" mode, then the
            # slot fill has access only to the "root" context, but not to the data of
            # get_template_data() of SimpleComponent.
            if is_isolated:
                assert ctx.get("the_arg") is None
                assert ctx.get("the_kwarg") is None
                assert ctx.get("kwargs") is None
                assert ctx.get("abc") is None
            else:
                assert ctx["the_arg"] == "1"
                assert ctx["the_kwarg"] == 3
                assert ctx["kwargs"] == {}
                assert ctx["abc"] == "def"

            slot_data_expected = {
                "data1": "abc",
                "data2": {"hello": "world", "one": 123},
            }
            assert slot_data_expected == slot_data

            assert isinstance(slot_ref, SlotRef)
            assert "SLOT_DEFAULT" == str(slot_ref).strip()

            return f"FROM_INSIDE_FIRST_SLOT | {slot_ref}"

        rendered = SimpleComponent.render(
            context={"abc": "def"},
            args=["1"],
            kwargs={"the_kwarg": 3},
            slots={"first": first_slot},
        )
        assertHTMLEqual(
            rendered,
            "FROM_INSIDE_FIRST_SLOT | SLOT_DEFAULT",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_raises_on_missing_slot(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" required %}
                {% endslot %}
            """

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape(
                "Slot 'first' is marked as 'required' (i.e. non-optional), yet no fill is provided."
            ),
        ):
            SimpleComponent.render()

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape(
                "Slot 'first' is marked as 'required' (i.e. non-optional), yet no fill is provided."
            ),
        ):
            SimpleComponent.render(
                slots={"first": None},
            )

        SimpleComponent.render(
            slots={"first": "FIRST_SLOT"},
        )

    # Part of the slot caching feature - test that static content slots reuse the slot function.
    # See https://github.com/django-components/django-components/issues/1164#issuecomment-2854682354
    def test_slots_reuse_functions__string(self):
        captured_slots = {}

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" required %}
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured_slots
                captured_slots = slots

        SimpleComponent.render(
            slots={"first": "FIRST_SLOT"},
        )

        first_slot_func = captured_slots["first"]
        first_nodelist: NodeList = first_slot_func.nodelist
        assert isinstance(first_slot_func, Slot)
        assert first_slot_func.content_func is not None
        assert first_slot_func.contents == "FIRST_SLOT"
        assert len(first_nodelist) == 1
        assert isinstance(first_nodelist[0], TextNode)
        assert first_nodelist[0].s == "FIRST_SLOT"

        captured_slots = {}
        SimpleComponent.render(
            slots={"first": "FIRST_SLOT"},
        )

        second_slot_func = captured_slots["first"]
        second_nodelist: NodeList = second_slot_func.nodelist
        assert isinstance(second_slot_func, Slot)
        assert second_slot_func.content_func is not None
        assert second_slot_func.contents == "FIRST_SLOT"
        assert len(second_nodelist) == 1
        assert isinstance(second_nodelist[0], TextNode)
        assert second_nodelist[0].s == "FIRST_SLOT"

        assert first_slot_func.contents == second_slot_func.contents

    # Part of the slot caching feature - test that consistent functions passed as slots
    # reuse the slot function.
    def test_slots_reuse_functions__func(self):
        captured_slots = {}

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" required %}
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured_slots
                captured_slots = slots

        slot_func = lambda ctx, slot_data, slot_ref: "FROM_INSIDE_SLOT"  # noqa: E731

        SimpleComponent.render(
            slots={"first": slot_func},
        )

        first_slot_func = captured_slots["first"]
        assert isinstance(first_slot_func, Slot)
        assert callable(first_slot_func.content_func)
        assert callable(first_slot_func.contents)
        assert first_slot_func.nodelist is None

        captured_slots = {}
        SimpleComponent.render(
            slots={"first": slot_func},
        )

        second_slot_func = captured_slots["first"]
        assert isinstance(second_slot_func, Slot)
        assert callable(second_slot_func.content_func)
        assert callable(second_slot_func.contents)
        assert second_slot_func.nodelist is None

        # NOTE: Both are functions, but different, because internally we wrap the function
        #       to escape the results.
        assert first_slot_func.contents is not second_slot_func.contents

    # Part of the slot caching feature - test that `Slot` instances with identical function
    # passed as slots reuse the slot function.
    def test_slots_reuse_functions__slot(self):
        captured_slots = {}

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" required %}
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured_slots
                captured_slots = slots

        slot_func = lambda ctx, slot_data, slot_ref: "FROM_INSIDE_SLOT"  # noqa: E731

        SimpleComponent.render(
            slots={"first": Slot(slot_func)},
        )

        first_slot_func = captured_slots["first"]
        assert isinstance(first_slot_func, Slot)
        assert callable(first_slot_func.content_func)
        assert callable(first_slot_func.contents)
        assert first_slot_func.nodelist is None

        captured_slots = {}
        SimpleComponent.render(
            slots={"first": Slot(slot_func)},
        )

        second_slot_func = captured_slots["first"]
        assert isinstance(second_slot_func, Slot)
        assert callable(second_slot_func.content_func)
        assert callable(second_slot_func.contents)
        assert second_slot_func.nodelist is None

        assert first_slot_func.contents == second_slot_func.contents

    # Part of the slot caching feature - test that identical slot fill content
    # slots reuse the slot function.
    def test_slots_reuse_functions__fill_tag_default(self):
        captured_slots = {}

        @register("test")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" default %}
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured_slots
                captured_slots = slots

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
              FROM_INSIDE_DEFAULT_SLOT
            {% endcomponent %}
        """
        template = Template(template_str)

        template.render(Context())

        first_slot_func = captured_slots["default"]
        first_nodelist: NodeList = first_slot_func.nodelist
        assert isinstance(first_slot_func, Slot)
        assert callable(first_slot_func.content_func)
        assert first_slot_func.contents == "\n              FROM_INSIDE_DEFAULT_SLOT\n            "
        assert len(first_nodelist) == 1
        assert isinstance(first_nodelist[0], TextNode)
        assert first_nodelist[0].s == "\n              FROM_INSIDE_DEFAULT_SLOT\n            "

        captured_slots = {}
        template.render(Context())

        second_slot_func = captured_slots["default"]
        second_nodelist: NodeList = second_slot_func.nodelist
        assert isinstance(second_slot_func, Slot)
        assert callable(second_slot_func.content_func)
        assert second_slot_func.contents == "\n              FROM_INSIDE_DEFAULT_SLOT\n            "
        assert len(second_nodelist) == 1
        assert isinstance(second_nodelist[0], TextNode)
        assert second_nodelist[0].s == "\n              FROM_INSIDE_DEFAULT_SLOT\n            "

        assert first_slot_func.contents == second_slot_func.contents

    # Part of the slot caching feature - test that identical slot fill content
    # slots reuse the slot function.
    def test_slots_reuse_functions__fill_tag_named(self):
        captured_slots = {}

        @register("test")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "first" default %}
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured_slots
                captured_slots = slots

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
              {% fill "first" %}
                FROM_INSIDE_NAMED_SLOT
              {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        template.render(Context())

        first_slot_func = captured_slots["first"]
        first_nodelist: NodeList = first_slot_func.nodelist
        assert isinstance(first_slot_func, Slot)
        assert callable(first_slot_func.content_func)
        assert first_slot_func.contents == "\n                FROM_INSIDE_NAMED_SLOT\n              "
        assert len(first_nodelist) == 1
        assert isinstance(first_nodelist[0], TextNode)
        assert first_nodelist[0].s == "\n                FROM_INSIDE_NAMED_SLOT\n              "

        captured_slots = {}
        template.render(Context())

        second_slot_func = captured_slots["first"]
        second_nodelist: NodeList = second_slot_func.nodelist
        assert isinstance(second_slot_func, Slot)
        assert callable(second_slot_func.content_func)
        assert second_slot_func.contents == "\n                FROM_INSIDE_NAMED_SLOT\n              "
        assert len(second_nodelist) == 1
        assert isinstance(second_nodelist[0], TextNode)
        assert second_nodelist[0].s == "\n                FROM_INSIDE_NAMED_SLOT\n              "

        assert first_slot_func.contents == second_slot_func.contents
