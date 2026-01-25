"""
Tests focusing on the Component class.
For tests focusing on the `component` tag, see `test_templatetags_component.py`
"""

import os
import re
from typing import Any, Literal, NamedTuple

import pytest
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template import Context, RequestContext, Template, TemplateSyntaxError
from django.template.base import TextNode
from django.test import Client
from django.urls import path
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import (
    Component,
    ComponentRegistry,
    Slot,
    SlotInput,
    all_components,
    get_component_by_class_id,
    register,
    registry,
    types,
)
from django_components.template import _get_component_template
from django_components.testing import djc_test
from django_components.urls import urlpatterns as dc_urlpatterns

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


# Client for testing endpoints via requests
class CustomClient(Client):
    def __init__(self, urlpatterns=None, *args, **kwargs):
        import types

        if urlpatterns:
            urls_module = types.ModuleType("urls")
            urls_module.urlpatterns = urlpatterns + dc_urlpatterns  # type: ignore[attr-defined]
            settings.ROOT_URLCONF = urls_module
        else:
            settings.ROOT_URLCONF = __name__
        settings.SECRET_KEY = "secret"  # noqa: S105
        super().__init__(*args, **kwargs)


@djc_test
class TestComponentLegacyApi:
    # TODO_REMOVE_IN_V1 - Superseded by `self.get_template` in v1
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_get_template_string(self, components_settings):
        class SimpleComponent(Component):
            def get_template_string(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

    # TODO_REMOVE_IN_V2 - `get_context_data()` was superseded by `self.get_template_data`
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_get_context_data(self, components_settings):
        class SimpleComponent(Component):
            template = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

    # TODO_REMOVE_IN_V1 - Registry and registered name should be passed to `Component.render()`,
    #                     not to the constructor.
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_instantiation(self, components_settings):
        class SimpleComponent(Component):
            template = """
                <div>
                    Name: {{ name }}
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "name": self.name,
                }

        # Old syntax
        rendered = SimpleComponent("simple").render()
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3f>
                Name: simple
            </div>
            """,
        )

        # New syntax
        rendered = SimpleComponent.render(registered_name="simple")
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc40>
                Name: simple
            </div>
            """,
        )

        # Sanity check
        rendered = SimpleComponent.render()
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41>
                Name: SimpleComponent
            </div>
            """,
        )

    # TODO_v1 - Remove
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_get_template_name(self, components_settings):
        class SvgComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "name": kwargs.pop("name", None),
                    "css_class": kwargs.pop("css_class", None),
                    "title": kwargs.pop("title", None),
                    **kwargs,
                }

            def get_template_name(self, context):
                return f"dynamic_{context['name']}.svg"

        assertHTMLEqual(
            SvgComponent.render(kwargs={"name": "svg1"}),
            """
            <svg data-djc-id-ca1bc3e>Dynamic1</svg>
            """,
        )
        assertHTMLEqual(
            SvgComponent.render(kwargs={"name": "svg2"}),
            """
            <svg data-djc-id-ca1bc3f>Dynamic2</svg>
            """,
        )

    # TODO_v1 - Remove
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_get_template__string(self, components_settings):
        class SimpleComponent(Component):
            def get_template(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

    # TODO_v1 - Remove
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_get_template__template(self, components_settings):
        class TestComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.pop("variable", None),
                }

            def get_template(self, context):
                template_str = "Variable: <strong>{{ variable }}</strong>"
                return Template(template_str)

        rendered = TestComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

    # TODO_v1 - Remove
    def test_get_template_is_cached(self):
        class SimpleComponent(Component):
            def get_template(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

        comp = SimpleComponent()
        template_1 = _get_component_template(comp)
        template_1._test_id = "123"  # type: ignore[union-attr]

        template_2 = _get_component_template(comp)
        assert template_2._test_id == "123"  # type: ignore[union-attr]

    # TODO_v1 - Remove
    def test_input(self):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                {% slot 'my_slot' / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                assert self.input.args == [123, "str"]
                assert self.input.kwargs == {"variable": "test", "another": 1}
                assert isinstance(self.input.context, Context)
                assert list(self.input.slots.keys()) == ["my_slot"]
                my_slot = self.input.slots["my_slot"]
                assert my_slot() == "MY_SLOT"

                return {
                    "variable": kwargs["variable"],
                }

            def on_render_before(self, context, template):
                assert self.input.args == [123, "str"]
                assert self.input.kwargs == {"variable": "test", "another": 1}
                assert isinstance(self.input.context, Context)
                assert list(self.input.slots.keys()) == ["my_slot"]
                my_slot = self.input.slots["my_slot"]
                assert my_slot() == "MY_SLOT"

        rendered = TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={"my_slot": "MY_SLOT"},
        )

        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong> MY_SLOT
            """,
        )

    def test_input_template_kwargs(self):
        captured = None

        @register("test")
        class Test(Component):
            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured
                captured = kwargs

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test"
                data={
                    "items": [
                        1|add:2,
                        {"x"|upper: 2|add:3},
                        *spread_items
                    ],
                    "nested": {
                        "a": [
                            1|add:2,
                            *nums|default:"",
                            *"{% lorem 1 w %}",
                        ],
                        "b": {
                            "x": [
                                *more|first,
                            ],
                            "{% lorem 2 w %}": "{% lorem 3 w %}",
                        }
                    },
                    **rest,
                    "key": _('value')|upper
                }
            / %}
        """

        template = Template(template_str)
        template.render(
            Context(
                {
                    "spread_items": ["foo", "bar"],
                    "nums": [1, 2, 3],
                    "more": ["baz", "qux"],
                    "rest": {"a": "b"},
                },
            ),
        )

        assert captured == {
            "data": {
                "items": [3, {"X": 5}, "foo", "bar"],
                "nested": {
                    "a": [3, 1, 2, 3, "l", "o", "r", "e", "m"],
                    "b": {
                        "x": ["b", "a", "z"],
                        "lorem ipsum": "lorem ipsum dolor",
                    },
                },
                "a": "b",
                "key": "VALUE",
            },
        }

    def test_input_template_both_args_kwargs(self):
        captured = None

        @register("test")
        class Test(Component):
            template = "var"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured
                captured = args, kwargs

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' 42 myvar key='val' key2=val2 %}
            {% endcomponent %}
        """
        Template(template_str).render(Context({"myvar": "myval", "val2": [1, 2, 3]}))

        assert captured == ([42, "myval"], {"key": "val", "key2": [1, 2, 3]})

    def test_input_kwargs_special(self):
        captured = None

        @register("test")
        class Test(Component):
            template = "var"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal captured
                captured = args, kwargs

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' date=date @lol=2 na-me=bzz @event:na-me.mod=bzz #my-id=True %}
            {% endcomponent %}
        """
        Template(template_str).render(Context({"date": 2024, "bzz": "fzz"}))

        assert captured == (
            [],
            {
                "date": 2024,
                "@lol": 2,
                "na-me": "fzz",
                "@event": {"na-me.mod": "fzz"},
                "#my-id": True,
            },
        )


@djc_test
class TestComponent:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_empty_component(self, components_settings):
        class EmptyComponent(Component):
            pass

        EmptyComponent.render(args=["123"])

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_string_static_inlined(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_file_static(self, components_settings):
        class SimpleComponent(Component):
            template_file = "simple_template.html"

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

            class Media:
                css = "style.css"
                js = "script.js"

        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

    # Test that even with cached template loaders, each Component has its own `Template`
    # even when multiple components point to the same template file.
    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        django_settings={
            "TEMPLATES": [
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [
                        "tests/templates/",
                        "tests/components/",
                    ],
                    "OPTIONS": {
                        "builtins": [
                            "django_components.templatetags.component_tags",
                        ],
                        "loaders": [
                            (
                                "django.template.loaders.cached.Loader",
                                [
                                    # Default Django loader
                                    "django.template.loaders.filesystem.Loader",
                                    # Including this is the same as APP_DIRS=True
                                    "django.template.loaders.app_directories.Loader",
                                    # Components loader
                                    "django_components.template_loader.Loader",
                                ],
                            ),
                        ],
                    },
                },
            ],
        },
    )
    def test_template_file_static__cached(self, components_settings):
        class SimpleComponent1(Component):
            template_file = "simple_template.html"

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

        class SimpleComponent2(Component):
            template_file = "simple_template.html"

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

        _ = SimpleComponent1.template  # Triggers template loading
        _ = SimpleComponent2.template  # Triggers template loading

        # Both components have their own Template instance, but they point to the same template file.
        assert isinstance(SimpleComponent1._template, Template)
        assert isinstance(SimpleComponent2._template, Template)
        assert SimpleComponent1._template is not SimpleComponent2._template
        assert SimpleComponent1._template.source == SimpleComponent2._template.source

        # The Template instances have different origins, but they point to the same template file.
        assert SimpleComponent1._template.origin is not SimpleComponent2._template.origin
        assert SimpleComponent1._template.origin.template_name == SimpleComponent2._template.origin.template_name
        assert SimpleComponent1._template.origin.name == SimpleComponent2._template.origin.name
        assert SimpleComponent1._template.origin.loader == SimpleComponent2._template.origin.loader

        # The origins point to their respective Component classes.
        assert SimpleComponent1._template.origin.component_cls == SimpleComponent1
        assert SimpleComponent2._template.origin.component_cls == SimpleComponent2

        rendered = SimpleComponent1.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

        rendered = SimpleComponent2.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3f>test</strong>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_file_static__compat(self, components_settings):
        class SimpleComponent(Component):
            template_name = "simple_template.html"

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

            class Media:
                css = "style.css"
                js = "script.js"

        # Access fields on Component class
        assert SimpleComponent.template_name == "simple_template.html"
        assert SimpleComponent.template_file == "simple_template.html"

        SimpleComponent.template_name = "other_template.html"
        assert SimpleComponent.template_name == "other_template.html"
        assert SimpleComponent.template_file == "other_template.html"

        SimpleComponent.template_name = "simple_template.html"
        rendered = SimpleComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong>
            """,
        )

        # Access fields on Component instance
        comp = SimpleComponent()
        assert comp.template_name == "simple_template.html"
        assert comp.template_file == "simple_template.html"

        # NOTE: Setting `template_file` on INSTANCE is not supported, as users should work
        #       with classes and not instances. This is tested for completeness.
        comp.template_name = "other_template_2.html"  # type: ignore[misc]
        assert comp.template_name == "other_template_2.html"
        assert comp.template_file == "other_template_2.html"
        assert SimpleComponent.template_name == "other_template_2.html"
        assert SimpleComponent.template_file == "other_template_2.html"

        SimpleComponent.template_name = "simple_template.html"
        rendered = comp.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc40>test</strong>
            """,
        )

    def test_get_component_by_id(self):
        class SimpleComponent(Component):
            pass

        assert get_component_by_class_id(SimpleComponent.class_id) == SimpleComponent

    def test_get_component_by_id_raises_on_missing_component(self):
        with pytest.raises(KeyError):
            get_component_by_class_id("nonexistent")

    def test_get_context_data_returns_none(self):
        class SimpleComponent(Component):
            template = "Hello"

            def get_template_data(self, args, kwargs, slots, context):
                return None

        assert SimpleComponent.render() == "Hello"


@djc_test
class TestComponentRenderAPI:
    def test_component_render_id(self):
        class SimpleComponent(Component):
            template = "render_id: {{ render_id }}"

            def get_template_data(self, args, kwargs, slots, context):
                return {"render_id": self.id}

        rendered = SimpleComponent.render()
        assert rendered == "render_id: ca1bc3e"

    def test_raw_input(self):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                {% slot 'my_slot' / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                assert self.raw_args == [123, "str"]
                assert self.raw_kwargs == {"variable": "test", "another": 1}
                assert isinstance(self.context, Context)
                assert list(self.raw_slots.keys()) == ["my_slot"]
                my_slot = self.raw_slots["my_slot"]
                assert my_slot() == "MY_SLOT"

                return {
                    "variable": kwargs["variable"],
                }

            def on_render_before(self, context, template):
                assert self.raw_args == [123, "str"]
                assert self.raw_kwargs == {"variable": "test", "another": 1}
                assert isinstance(self.context, Context)
                assert list(self.raw_slots.keys()) == ["my_slot"]
                my_slot = self.raw_slots["my_slot"]
                assert my_slot() == "MY_SLOT"

        rendered = TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={"my_slot": "MY_SLOT"},
        )

        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3e>test</strong> MY_SLOT
            """,
        )

    def test_args_kwargs_slots__simple(self):
        called = False

        class TestComponent(Component):
            template = ""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal called
                called = True

                assert self.args == [123, "str"]
                assert self.kwargs == {"variable": "test", "another": 1}
                assert list(self.slots.keys()) == ["my_slot"]
                my_slot = self.slots["my_slot"]
                assert my_slot() == "MY_SLOT"

        TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={"my_slot": "MY_SLOT"},
        )

        assert called

    def test_args_kwargs_slots__typed(self):
        called = False

        class TestComponent(Component):
            template = ""

            class Args:
                variable: int
                another: str

            class Kwargs:
                variable: str
                another: int

            class Slots:
                my_slot: SlotInput

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal called
                called = True

                assert self.args == TestComponent.Args(123, "str")  # type: ignore[call-arg]
                assert self.kwargs == TestComponent.Kwargs(variable="test", another=1)  # type: ignore[call-arg]
                assert isinstance(self.slots, TestComponent.Slots)
                assert isinstance(self.slots.my_slot, Slot)
                assert self.slots.my_slot() == "MY_SLOT"

                # Check that the instances are reused across multiple uses
                assert self.args is self.args
                assert self.kwargs is self.kwargs
                assert self.slots is self.slots

        TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={"my_slot": "MY_SLOT"},
        )

        assert called

    def test_args_kwargs_slots__available_outside_render(self):
        comp: Any = None

        class TestComponent(Component):
            template = ""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self

        assert comp is None

        TestComponent.render()

        assert comp.args == []  # type: ignore[attr-defined]
        assert comp.kwargs == {}  # type: ignore[attr-defined]
        assert comp.slots == {}  # type: ignore[attr-defined]
        assert comp.context == Context()  # type: ignore[attr-defined]

    def test_metadata__template(self):
        comp: Any = None

        @register("test")
        class TestComponent(Component):
            template = "hello"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self

        template_str: types.django_html = """
            {% load component_tags %}
            <div class="test-component">
                {% component "test" / %}
            </div>
        """
        template = Template(template_str)
        rendered = template.render(Context())

        assertHTMLEqual(rendered, '<div class="test-component">hello</div>')

        assert isinstance(comp, TestComponent)

        assert isinstance(comp.outer_context, Context)
        assert comp.outer_context == Context()

        assert isinstance(comp.registry, ComponentRegistry)
        assert comp.registered_name == "test"

        assert comp.node is not None
        assert comp.node.template_component is None
        assert comp.node.template_name == "<unknown source>"

    def test_metadata__component(self):
        comp: Any = None

        @register("test")
        class TestComponent(Component):
            template = "hello"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self

        class Outer(Component):
            template = "{% component 'test' only / %}"

        rendered = Outer.render()

        assert rendered == "hello"

        assert isinstance(comp, TestComponent)

        assert isinstance(comp.outer_context, Context)
        assert comp.outer_context is not comp.context

        assert isinstance(comp.registry, ComponentRegistry)
        assert comp.registered_name == "test"

        assert comp.node is not None
        assert comp.node.template_component == Outer

        if os.name == "nt":
            assert comp.node.template_name.endswith("tests\\test_component.py::Outer")  # type: ignore[union-attr]
        else:
            assert comp.node.template_name.endswith("tests/test_component.py::Outer")  # type: ignore[union-attr]

    def test_metadata__python(self):
        comp: Any = None

        @register("test")
        class TestComponent(Component):
            template = "hello"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self

        rendered = TestComponent.render(
            context=Context(),
            args=(),
            kwargs={},
            slots={},
            deps_strategy="document",
            render_dependencies=True,
            request=None,
            outer_context=Context(),
            registry=ComponentRegistry(),
            registered_name="test",
        )

        assert rendered == "hello"

        assert isinstance(comp, TestComponent)

        assert isinstance(comp.outer_context, Context)
        assert comp.outer_context == Context()

        assert isinstance(comp.registry, ComponentRegistry)
        assert comp.registered_name == "test"

        assert comp.node is None

    def test_parent__root_component(self):
        """Test that parent returns None for root components."""
        comp: Any = None

        class RootComponent(Component):
            template = "root"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self
                # Root component should have no parent
                assert self.parent is None
                return {}

        RootComponent.render()
        assert comp is not None
        assert comp.parent is None

    def test_parent__nested_component(self):
        """Test that parent returns the correct parent component instance."""
        grandparent_comp: Any = None
        parent_comp: Any = None
        child_comp: Any = None

        @register("child")
        class ChildComponent(Component):
            template = "child"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal child_comp
                child_comp = self

                # Child should have a parent
                assert self.parent is not None
                assert self.parent == parent_comp
                # Child's parent should have a parent (grandparent)
                assert self.parent.parent == grandparent_comp

        @register("parent")
        class ParentComponent(Component):
            template = "{% component 'child' / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal parent_comp
                parent_comp = self

                # Parent should have a parent (grandparent)
                assert self.parent is not None
                assert self.parent == grandparent_comp

        class GrandparentComponent(Component):
            template = "{% component 'parent' / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal grandparent_comp
                grandparent_comp = self

                # Grandparent should have no parent (it's the root)
                assert self.parent is None

        GrandparentComponent.render()

        assert grandparent_comp is not None
        assert parent_comp is not None
        assert child_comp is not None
        assert child_comp.parent == parent_comp
        assert child_comp.parent is not None
        assert parent_comp.parent == grandparent_comp
        assert parent_comp.parent is not None
        assert grandparent_comp.parent is None

    def test_root__root_component(self):
        """Test that root returns self for root components."""
        comp: Any = None

        class RootComponent(Component):
            template = "root"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self
                # Root component should return self
                assert self.root == self
                return {}

        RootComponent.render()
        assert comp is not None
        assert comp.root == comp

    def test_root__nested_component(self):
        """Test that root returns the correct root component instance."""
        root_comp: Any = None
        middle_comp: Any = None
        leaf_comp: Any = None

        @register("leaf")
        class LeafComponent(Component):
            template = "leaf"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal leaf_comp
                leaf_comp = self
                # Leaf should point to root
                assert self.root == root_comp
                return {}

        @register("middle")
        class MiddleComponent(Component):
            template = "{% component 'leaf' / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal middle_comp
                middle_comp = self
                # Middle should also point to root
                assert self.root == root_comp
                return {}

        class RootComponent(Component):
            template = "{% component 'middle' / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal root_comp
                root_comp = self
                # Root should return self
                assert self.root == self
                return {}

        RootComponent.render()
        assert root_comp is not None
        assert middle_comp is not None
        assert leaf_comp is not None
        assert leaf_comp.root == root_comp
        assert middle_comp.root == root_comp
        assert root_comp.root == root_comp

    def test_ancestors__root_component(self):
        """Test that ancestors is empty for root components."""
        comp: Any = None

        class RootComponent(Component):
            template = "root"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self
                # Root component should have no ancestors
                ancestors_list = list(self.ancestors)
                assert ancestors_list == []
                return {}

        RootComponent.render()
        assert comp is not None
        assert list(comp.ancestors) == []

    def test_ancestors__nested_component(self):
        """Test that ancestors yields all ancestors in correct order."""
        root_comp: Any = None
        middle_comp: Any = None
        leaf_comp: Any = None

        @register("leaf")
        class LeafComponent(Component):
            template = "leaf"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal leaf_comp
                leaf_comp = self
                # Leaf should have middle and root as ancestors (in that order)
                ancestors_list = list(self.ancestors)
                assert len(ancestors_list) == 2
                assert ancestors_list[0] == middle_comp
                assert ancestors_list[1] == root_comp
                return {}

        @register("middle")
        class MiddleComponent(Component):
            template = "{% component 'leaf' / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal middle_comp
                middle_comp = self
                # Middle should have only root as ancestor
                ancestors_list = list(self.ancestors)
                assert len(ancestors_list) == 1
                assert ancestors_list[0] == root_comp
                return {}

        class RootComponent(Component):
            template = "{% component 'middle' / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal root_comp
                root_comp = self
                # Root should have no ancestors
                ancestors_list = list(self.ancestors)
                assert ancestors_list == []
                return {}

        RootComponent.render()
        assert root_comp is not None
        assert middle_comp is not None
        assert leaf_comp is not None

        # Verify ancestors from outside the render context
        leaf_ancestors = list(leaf_comp.ancestors)
        assert len(leaf_ancestors) == 2
        assert leaf_ancestors[0] == middle_comp
        assert leaf_ancestors[1] == root_comp

        middle_ancestors = list(middle_comp.ancestors)
        assert len(middle_ancestors) == 1
        assert middle_ancestors[0] == root_comp

        root_ancestors = list(root_comp.ancestors)
        assert root_ancestors == []

    def test_ancestors__same_component_at_different_levels(self):
        """Test ancestors when the same component class appears at different levels [CompA, CompB, CompA]."""
        comp_a_root: Any = None
        comp_b: Any = None
        comp_a_leaf: Any = None

        @register("comp_a")
        class CompA(Component):
            template: types.django_html = """
                {% if not leaf %}
                    {% component 'comp_b' / %}
                {% endif %}
            """

            class Kwargs(NamedTuple):
                leaf: bool = False

            def get_template_data(self, args, kwargs: Kwargs, slots, context):
                nonlocal comp_a_root

                # Root CompA
                if not kwargs.leaf:
                    comp_a_root = self
                    # Root should have no ancestors
                    ancestors_list = list(self.ancestors)
                    assert ancestors_list == []
                # Leaf CompA
                else:
                    nonlocal comp_a_leaf
                    # This is the leaf CompA (nested inside CompB)
                    comp_a_leaf = self
                    # Leaf CompA should have [CompB, CompA] as ancestors
                    ancestors_list = list(self.ancestors)
                    assert len(ancestors_list) == 2
                    assert ancestors_list[0] == comp_b
                    assert ancestors_list[1] == comp_a_root

                return {"leaf": kwargs.leaf}

        @register("comp_b")
        class CompB(Component):
            template = "{% component 'comp_a' leaf=True / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp_b
                comp_b = self
                # CompB should have [CompA] as ancestor
                ancestors_list = list(self.ancestors)

                assert len(ancestors_list) == 1
                assert ancestors_list[0] == comp_a_root

        CompA.render(
            kwargs=CompA.Kwargs(leaf=False),
        )

        assert comp_a_root is not None
        assert comp_b is not None
        assert comp_a_leaf is not None

        assert comp_a_root is not comp_a_leaf

        # Verify ancestors from outside the render context
        # Leaf CompA should have [CompB, CompA] as ancestors
        leaf_ancestors = list(comp_a_leaf.ancestors)
        assert len(leaf_ancestors) == 2
        assert leaf_ancestors[0] == comp_b
        assert leaf_ancestors[1] == comp_a_root

        # CompB should have [CompA] as ancestor
        comp_b_ancestors = list(comp_b.ancestors)
        assert len(comp_b_ancestors) == 1
        assert comp_b_ancestors[0] == comp_a_root

        # Root CompA should have no ancestors
        root_ancestors = list(comp_a_root.ancestors)
        assert root_ancestors == []

    def test_parent_root_ancestors__type_checking(self):
        """Test that parent, root, and ancestors work with isinstance checks."""
        root_comp: Any = None
        child_comp: Any = None

        @register("child")
        class ChildComponent(Component):
            template = "child"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal child_comp
                child_comp = self
                return {}

        class RootComponent(Component):
            template = "{% component 'child' / %}"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal root_comp
                root_comp = self
                return {}

        RootComponent.render()

        # Test isinstance checks work correctly
        assert isinstance(child_comp.parent, RootComponent)
        assert isinstance(child_comp.root, RootComponent)
        assert isinstance(root_comp.root, RootComponent)

        # Test ancestors iteration
        for ancestor in child_comp.ancestors:
            assert isinstance(ancestor, Component)
            assert ancestor == root_comp


@djc_test
class TestComponentTemplateVars:
    def test_args_kwargs_slots__simple_untyped(self):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="test-component">
                    {# Test whole objects #}
                    args: {{ component_vars.args|safe }}
                    kwargs: {{ component_vars.kwargs|safe }}
                    slots: {{ component_vars.slots|safe }}

                    {# Test individual values #}
                    arg: {{ component_vars.args.0|safe }}
                    kwarg: {{ component_vars.kwargs.variable|safe }}
                    slot: {{ component_vars.slots.my_slot|safe }}
                </div>
            """

        html = TestComponent.render(
            args=[123, "str"],
            kwargs={"variable": "test", "another": 1},
            slots={"my_slot": "MY_SLOT"},
        )
        assertHTMLEqual(
            html,
            """
            <div class="test-component" data-djc-id-ca1bc3e="">
                args: [123, 'str']
                kwargs: {'variable': 'test', 'another': 1}
                slots: {'my_slot': <Slot component_name='TestComponent' slot_name='my_slot'>}
                arg: 123
                kwarg: test
                slot: <Slot component_name='TestComponent' slot_name='my_slot'>
            </div>
            """,
        )

    def test_args_kwargs_slots__simple_typed(self):
        class TestComponent(Component):
            class Args:
                variable: int
                another: str

            class Kwargs:
                variable: str
                another: int

            class Slots:
                my_slot: SlotInput

            template: types.django_html = """
                {% load component_tags %}
                <div class="test-component">
                    {# Test whole objects #}
                    args: {{ component_vars.args|safe }}
                    kwargs: {{ component_vars.kwargs|safe }}
                    slots: {{ component_vars.slots|safe }}

                    {# Test individual values #}
                    arg: {{ component_vars.args.variable|safe }}
                    kwarg: {{ component_vars.kwargs.variable|safe }}
                    slot: {{ component_vars.slots.my_slot|safe }}
                </div>
            """

        html = TestComponent.render(
            args=[123, "str"],
            kwargs={"variable": "test", "another": 1},
            slots={"my_slot": "MY_SLOT"},
        )
        assertHTMLEqual(
            html,
            """
            <div class="test-component" data-djc-id-ca1bc3e="">
                args: Args(variable=123, another='str')
                kwargs: Kwargs(variable='test', another=1)
                slots: Slots(my_slot=<Slot component_name='TestComponent' slot_name='my_slot'>)
                arg: 123
                kwarg: test
                slot: <Slot component_name='TestComponent' slot_name='my_slot'>
            </div>
            """,
        )

    def test_args_kwargs_slots__nested_untyped(self):
        @register("wrapper")
        class Wrapper(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="wrapper">
                    {% slot "content" default %}
                        <div class="test">DEFAULT</div>
                    {% endslot %}
                </div>
            """

        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="test-component">
                    {% component "wrapper" %}
                        {# Test whole objects #}
                        args: {{ component_vars.args|safe }}
                        kwargs: {{ component_vars.kwargs|safe }}
                        slots: {{ component_vars.slots|safe }}

                        {# Test individual values #}
                        arg: {{ component_vars.args.0|safe }}
                        kwarg: {{ component_vars.kwargs.variable|safe }}
                        slot: {{ component_vars.slots.my_slot|safe }}
                    {% endcomponent %}
                </div>
            """

        html = TestComponent.render(
            args=[123, "str"],
            kwargs={"variable": "test", "another": 1},
            slots={"my_slot": "MY_SLOT"},
        )
        assertHTMLEqual(
            html,
            """
            <div class="test-component" data-djc-id-ca1bc3e="">
                <div class="wrapper" data-djc-id-ca1bc40="">
                    args: [123, 'str']
                    kwargs: {'variable': 'test', 'another': 1}
                    slots: {'my_slot': <Slot component_name='TestComponent' slot_name='my_slot'>}
                    arg: 123
                    kwarg: test
                    slot: <Slot component_name='TestComponent' slot_name='my_slot'>
                </div>
            </div>
            """,
        )

    def test_args_kwargs_slots__nested_typed(self):
        @register("wrapper")
        class Wrapper(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="wrapper">
                    {% slot "content" default %}
                        <div class="test">DEFAULT</div>
                    {% endslot %}
                </div>
            """

        class TestComponent(Component):
            class Args:
                variable: int
                another: str

            class Kwargs:
                variable: str
                another: int

            class Slots:
                my_slot: SlotInput

            template: types.django_html = """
                {% load component_tags %}
                <div class="test-component">
                    {% component "wrapper" %}
                        {# Test whole objects #}
                        args: {{ component_vars.args|safe }}
                        kwargs: {{ component_vars.kwargs|safe }}
                        slots: {{ component_vars.slots|safe }}

                        {# Test individual values #}
                        arg: {{ component_vars.args.variable|safe }}
                        kwarg: {{ component_vars.kwargs.variable|safe }}
                        slot: {{ component_vars.slots.my_slot|safe }}
                    {% endcomponent %}
                </div>
            """

        html = TestComponent.render(
            args=[123, "str"],
            kwargs={"variable": "test", "another": 1},
            slots={"my_slot": "MY_SLOT"},
        )
        assertHTMLEqual(
            html,
            """
            <div class="test-component" data-djc-id-ca1bc3e="">
                <div class="wrapper" data-djc-id-ca1bc40="">
                    args: Args(variable=123, another='str')
                    kwargs: Kwargs(variable='test', another=1)
                    slots: Slots(my_slot=<Slot component_name='TestComponent' slot_name='my_slot'>)
                    arg: 123
                    kwarg: test
                    slot: <Slot component_name='TestComponent' slot_name='my_slot'>
                </div>
            </div>
            """,
        )

    def test_args_kwargs_slots__nested_conditional_slots(self):
        @register("wrapper")
        class Wrapper(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="wrapper">
                    {% slot "content" default %}
                        <div class="test">DEFAULT</div>
                    {% endslot %}
                </div>
            """

        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="test-component">
                    {% component "wrapper" %}
                        {% if component_vars.slots.subtitle %}
                            <div class="subtitle">
                                {% slot "subtitle" %}
                                    Optional subtitle
                                {% endslot %}
                            </div>
                        {% endif %}
                    {% endcomponent %}
                </div>
            """

        html = TestComponent.render(
            slots={"subtitle": "SUBTITLE_FILLED"},
        )
        assertHTMLEqual(
            html,
            """
            <div class="test-component" data-djc-id-ca1bc3e="">
                <div class="wrapper" data-djc-id-ca1bc41="">
                    <div class="subtitle">SUBTITLE_FILLED</div>
                </div>
            </div>
            """,
        )


@djc_test
class TestComponentRender:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_minimal(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                the_arg2: {{ the_arg2 }}
                args: {{ args|safe }}
                the_kwarg: {{ the_kwarg }}
                kwargs: {{ kwargs|safe }}
                ---
                from_context: {{ from_context }}
                ---
                slot_second: {% slot "second" default %}
                    SLOT_SECOND_DEFAULT
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "the_arg2": args[0] if args else None,
                    "the_kwarg": kwargs.pop("the_kwarg", None),
                    "args": args[1:],
                    "kwargs": kwargs,
                }

        rendered = SimpleComponent.render()
        assertHTMLEqual(
            rendered,
            """
            the_arg2: None
            args: []
            the_kwarg: None
            kwargs: {}
            ---
            from_context:
            ---
            slot_second: SLOT_SECOND_DEFAULT
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_full(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                the_arg: {{ the_arg }}
                the_arg2: {{ the_arg2 }}
                args: {{ args|safe }}
                the_kwarg: {{ the_kwarg }}
                kwargs: {{ kwargs|safe }}
                ---
                from_context: {{ from_context }}
                ---
                slot_first: {% slot "first" required %}
                {% endslot %}
                ---
                slot_second: {% slot "second" default %}
                    SLOT_SECOND_DEFAULT
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "the_arg": args[0],
                    "the_arg2": args[1],
                    "the_kwarg": kwargs.pop("the_kwarg", None),
                    "args": args[2:],
                    "kwargs": kwargs,
                }

        rendered = SimpleComponent.render(
            context={"from_context": 98},
            args=["one", "two", "three"],
            kwargs={"the_kwarg": "test", "kw2": "ooo"},
            slots={"first": "FIRST_SLOT"},
        )
        assertHTMLEqual(
            rendered,
            """
            the_arg: one
            the_arg2: two
            args: ['three']
            the_kwarg: test
            kwargs: {'kw2': 'ooo'}
            ---
            from_context: 98
            ---
            slot_first: FIRST_SLOT
            ---
            slot_second: SLOT_SECOND_DEFAULT
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_to_response_full(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                the_arg: {{ the_arg }}
                the_arg2: {{ the_arg2 }}
                args: {{ args|safe }}
                the_kwarg: {{ the_kwarg }}
                kwargs: {{ kwargs|safe }}
                ---
                from_context: {{ from_context }}
                ---
                slot_first: {% slot "first" required %}
                {% endslot %}
                ---
                slot_second: {% slot "second" default %}
                    SLOT_SECOND_DEFAULT
                {% endslot %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "the_arg": args[0],
                    "the_arg2": args[1],
                    "the_kwarg": kwargs.pop("the_kwarg"),
                    "args": args[2:],
                    "kwargs": kwargs,
                }

        rendered = SimpleComponent.render_to_response(
            context={"from_context": 98},
            args=["one", "two", "three"],
            kwargs={"the_kwarg": "test", "kw2": "ooo"},
            slots={"first": "FIRST_SLOT"},
        )
        assert isinstance(rendered, HttpResponse)

        assertHTMLEqual(
            rendered.content.decode(),
            """
            the_arg: one
            the_arg2: two
            args: ['three']
            the_kwarg: test
            kwargs: {'kw2': 'ooo'}
            ---
            from_context: 98
            ---
            slot_first: FIRST_SLOT
            ---
            slot_second: SLOT_SECOND_DEFAULT
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_to_response_change_response_class(self, components_settings):
        class MyResponse:
            def __init__(self, content: str) -> None:
                self.content = bytes(content, "utf-8")

        class SimpleComponent(Component):
            response_class = MyResponse
            template: types.django_html = "HELLO"

        rendered = SimpleComponent.render_to_response()
        assert isinstance(rendered, MyResponse)

        assertHTMLEqual(
            rendered.content.decode(),
            "HELLO",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_with_include(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' %}
            """

        rendered = SimpleComponent.render()
        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc3e>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    # See https://github.com/django-components/django-components/issues/580
    # And https://github.com/django-components/django-components/commit/fee26ec1d8b46b5ee065ca1ce6143889b0f96764
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_with_include_and_context(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' %}
            """

        rendered = SimpleComponent.render(context=Context())
        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc3e>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    # See https://github.com/django-components/django-components/issues/580
    # And https://github.com/django-components/django-components/issues/634
    # And https://github.com/django-components/django-components/commit/fee26ec1d8b46b5ee065ca1ce6143889b0f96764
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_with_include_and_request_context(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% include 'slotted_template.html' %}
            """

        rendered = SimpleComponent.render(context=RequestContext(HttpRequest()))
        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc3e>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    # See https://github.com/django-components/django-components/issues/580
    # And https://github.com/django-components/django-components/issues/634
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_context_is_populated_from_context_processors(self, components_settings):
        @register("thing")
        class Thing(Component):
            template: types.django_html = """
                <kbd>Rendered {{ how }}</kbd>
                <div>
                    CSRF token: {{ csrf_token|default:"<em>No CSRF token</em>" }}
                </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {"how": kwargs.pop("how")}

            class View:
                def get(self, request):
                    how = "via GET request"

                    return self.component_cls.render_to_response(  # type: ignore[attr-defined]
                        context=RequestContext(request),
                        kwargs={"how": how},
                    )

        client = CustomClient(urlpatterns=[path("test_thing/", Thing.as_view())])
        response = client.get("/test_thing/")

        assert response.status_code == 200

        # Full response:
        # """
        # <kbd>
        #     Rendered via GET request
        # </kbd>
        # <div>
        #     CSRF token:
        #     <div>
        #         test_csrf_token
        #     </div>
        # </div>
        # """
        assertInHTML(
            """
            <kbd data-djc-id-ca1bc3f>
                Rendered via GET request
            </kbd>
            """,
            response.content.decode(),
        )

        token_re = re.compile(rb"CSRF token:\s+predictabletoken")
        token = token_re.findall(response.content)[0]

        assert token == b"CSRF token: predictabletoken"

    def test_request_context_created_when_no_context(self):
        @register("thing")
        class Thing(Component):
            template: types.django_html = """
                CSRF token: {{ csrf_token|default:"<em>No CSRF token</em>" }}
            """

            class View:
                def get(self, request):
                    return Thing.render_to_response(request=request)

        client = CustomClient(urlpatterns=[path("test_thing/", Thing.as_view())])
        response = client.get("/test_thing/")

        assert response.status_code == 200

        token_re = re.compile(rb"CSRF token:\s+predictabletoken")
        token = token_re.findall(response.content)[0]

        assert token == b"CSRF token: predictabletoken"

    def test_request_context_created_when_already_a_context_dict(self):
        @register("thing")
        class Thing(Component):
            template: types.django_html = """
                <p>CSRF token: {{ csrf_token|default:"<em>No CSRF token</em>" }}</p>
                <p>Existing context: {{ existing_context|default:"<em>No existing context</em>" }}</p>
            """

            class View:
                def get(self, request):
                    return Thing.render_to_response(request=request, context={"existing_context": "foo"})

        client = CustomClient(urlpatterns=[path("test_thing/", Thing.as_view())])
        response = client.get("/test_thing/")

        assert response.status_code == 200

        token_re = re.compile(rb"CSRF token:\s+predictabletoken")
        token = token_re.findall(response.content)[0]

        assert token == b"CSRF token: predictabletoken"
        assert "Existing context: foo" in response.content.decode()

    def request_context_ignores_context_when_already_a_context(self):
        @register("thing")
        class Thing(Component):
            template: types.django_html = """
                <p>CSRF token: {{ csrf_token|default:"<em>No CSRF token</em>" }}</p>
                <p>Existing context: {{ existing_context|default:"<em>No existing context</em>" }}</p>
            """

            class View:
                def get(self, request):
                    return Thing.render_to_response(
                        request=request,
                        context=Context({"existing_context": "foo"}),
                    )

        client = CustomClient(urlpatterns=[path("test_thing/", Thing.as_view())])
        response = client.get("/test_thing/")

        assert response.status_code == 200

        token_re = re.compile(rb"CSRF token:\s+(?P<token>[0-9a-zA-Z]{64})")

        assert not token_re.findall(response.content)
        assert "Existing context: foo" in response.content.decode()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_with_extends(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% extends 'block.html' %}
                {% block body %}
                    OVERRIDEN
                {% endblock %}
            """

        rendered = SimpleComponent.render(deps_strategy="ignore")
        assertHTMLEqual(
            rendered,
            """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc3e lang="en">
            <body>
                <main role="main">
                <div class='container main-container'>
                    OVERRIDEN
                </div>
                </main>
            </body>
            </html>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_can_access_instance(self, components_settings):
        class TestComponent(Component):
            template = "Variable: <strong>{{ id }}</strong>"

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "id": self.id,
                }

        rendered = TestComponent.render()
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3e>ca1bc3e</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_to_response_can_access_instance(self, components_settings):
        class TestComponent(Component):
            template = "Variable: <strong>{{ id }}</strong>"

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "id": self.id,
                }

        rendered_resp = TestComponent.render_to_response()
        assertHTMLEqual(
            rendered_resp.content.decode("utf-8"),
            "Variable: <strong data-djc-id-ca1bc3e>ca1bc3e</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_prepends_exceptions_with_component_path(self, components_settings):
        @register("broken")
        class Broken(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <main>
                    {% slot "content" default / %}
                </main>
            """

            def get_template_data(self, args, kwargs, slots, context):
                data = self.inject("my_provide")
                data["data1"]  # This should raise TypeError
                return {"data": data}

        @register("provider")
        class Provider(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"data": kwargs["data"]}

            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" data=data %}
                    {% slot "content" default / %}
                {% endprovide %}
            """

        @register("parent")
        class Parent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"data": kwargs["data"]}

            template: types.django_html = """
                {% load component_tags %}
                {% component "provider" data=data %}
                    {% component "broken" %}
                        {% slot "content" default / %}
                    {% endcomponent %}
                {% endcomponent %}
            """

        @register("root")
        class Root(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component "parent" data=123 %}
                    {% fill "content" %}
                        456
                    {% endfill %}
                {% endcomponent %}
            """

        with pytest.raises(
            TypeError,
            match=re.escape(
                "An error occured while rendering components Root > parent > provider > provider(slot:content) > broken:\n"  # noqa: E501
                "tuple indices must be integers or slices, not str",
            ),
        ):
            Root.render()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_prepends_exceptions_on_template_compile_error(self, components_settings):
        @register("simple_component")
        class SimpleComponent(Component):
            template = "hello"

        class Other(Component):
            template = """
                {% load component_tags %}
                {% component "simple_component" %}
                {% endif %}
            """

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape(
                "An error occured while rendering components Other:\n"
                "Invalid block tag on line 4: 'endif', expected 'endcomponent'",
            ),
        ):
            Other.render()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_prepends_exceptions_on_template_compile_error2(self, components_settings):
        @register("simple_component")
        class SimpleComponent(Component):
            template = "hello"

        class Other(Component):
            template = """
                {% load component_tags %}
                {% component "simple_component" %}
            """

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape(
                "An error occured while rendering components Other:\nUnclosed tag on line 3: 'component'",
            ),
        ):
            Other.render()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_pydantic_exception(self, components_settings):
        from pydantic import BaseModel, ValidationError

        @register("broken")
        class Broken(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <main>
                    {% slot "content" default / %}
                </main>
            """

            class Kwargs(BaseModel):
                data1: str

            def get_template_data(self, args, kwargs: Kwargs, slots, context):
                return {"data": kwargs.data1}

        @register("parent")
        class Parent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"data": kwargs["data"]}

            template: types.django_html = """
                {% load component_tags %}
                {% component "broken" %}
                    {% slot "content" default / %}
                {% endcomponent %}
            """

        @register("root")
        class Root(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component "parent" data=123 %}
                    {% fill "content" %}
                        456
                    {% endfill %}
                {% endcomponent %}
            """

        # NOTE: We're unable to insert the component path in the Pydantic's exception message
        with pytest.raises(
            ValidationError,
            match=re.escape("1 validation error for Kwargs\ndata1\n  Field required"),
        ):
            Root.render()


@djc_test
class TestComponentHook:
    def _gen_slotted_component(self, calls: list[str]):
        class Slotted(Component):
            template = "Hello from slotted"

            def on_render_before(self, context: Context, template: Template | None) -> None:
                calls.append("slotted__on_render_before")

            def on_render(self, context: Context, template: Template | None):
                calls.append("slotted__on_render_pre")
                _html, _error = yield lambda: template.render(context)  # type: ignore[union-attr]

                calls.append("slotted__on_render_post")

            # Check that modifying the context or template does nothing
            def on_render_after(
                self,
                context: Context,
                template: Template | None,
                html: str | None,
                error: Exception | None,
            ) -> None:
                calls.append("slotted__on_render_after")

        return Slotted

    def _gen_inner_component(self, calls: list[str]):
        class Inner(Component):
            template: types.django_html = """
                {% load component_tags %}
                Inner start
                {% slot "content" default / %}
                Inner end
            """

            def on_render_before(self, context: Context, template: Template | None) -> None:
                calls.append("inner__on_render_before")

            def on_render(self, context: Context, template: Template | None):
                calls.append("inner__on_render_pre")
                if template is None:
                    yield None
                else:
                    _html, _error = yield lambda: template.render(context)

                calls.append("inner__on_render_post")

            # Check that modifying the context or template does nothing
            def on_render_after(
                self,
                context: Context,
                template: Template | None,
                html: str | None,
                error: Exception | None,
            ) -> None:
                calls.append("inner__on_render_after")

        return Inner

    def _gen_middle_component(self, calls: list[str]):
        class Middle(Component):
            template: types.django_html = """
                {% load component_tags %}
                Middle start
                {% component "inner" %}
                    {% component "slotted" / %}
                {% endcomponent %}
                Middle text
                {% component "inner" / %}
                Middle end
            """

            def on_render_before(self, context: Context, template: Template | None) -> None:
                calls.append("middle__on_render_before")

            def on_render(self, context: Context, template: Template | None):
                calls.append("middle__on_render_pre")
                _html, _error = yield lambda: template.render(context)  # type: ignore[union-attr]

                calls.append("middle__on_render_post")

            # Check that modifying the context or template does nothing
            def on_render_after(
                self,
                context: Context,
                template: Template | None,
                html: str | None,
                error: Exception | None,
            ) -> None:
                calls.append("middle__on_render_after")

        return Middle

    def _gen_outer_component(self, calls: list[str]):
        class Outer(Component):
            template: types.django_html = """
                {% load component_tags %}
                Outer start
                {% component "middle" / %}
                Outer text
                {% component "middle" / %}
                Outer end
            """

            def on_render_before(self, context: Context, template: Template | None) -> None:
                calls.append("outer__on_render_before")

            def on_render(self, context: Context, template: Template | None):
                calls.append("outer__on_render_pre")
                _html, _error = yield lambda: template.render(context)  # type: ignore[union-attr]

                calls.append("outer__on_render_post")

            # Check that modifying the context or template does nothing
            def on_render_after(
                self,
                context: Context,
                template: Template | None,
                html: str | None,
                error: Exception | None,
            ) -> None:
                calls.append("outer__on_render_after")

        return Outer

    def _gen_broken_component(self):
        class BrokenComponent(Component):
            def on_render(self, context: Context, template: Template):
                raise ValueError("BROKEN")

        return BrokenComponent

    def test_order(self):
        calls: list[str] = []

        registry.register("slotted", self._gen_slotted_component(calls))
        registry.register("inner", self._gen_inner_component(calls))
        registry.register("middle", self._gen_middle_component(calls))
        Outer = self._gen_outer_component(calls)

        result = Outer.render()

        assertHTMLEqual(
            result,
            """
            Outer start
                Middle start
                    Inner start
                        Hello from slotted
                    Inner end
                    Middle text
                    Inner start
                    Inner end
                Middle end
                Outer text
                Middle start
                    Inner start
                        Hello from slotted
                    Inner end
                    Middle text
                    Inner start
                    Inner end
                Middle end
            Outer end
            """,
        )

        assert calls == [
            "outer__on_render_before",
            "outer__on_render_pre",
            "middle__on_render_before",
            "middle__on_render_before",
            "middle__on_render_pre",
            "inner__on_render_before",
            "inner__on_render_before",
            "inner__on_render_pre",
            "slotted__on_render_before",
            "slotted__on_render_pre",
            "slotted__on_render_post",
            "slotted__on_render_after",
            "inner__on_render_post",
            "inner__on_render_after",
            "inner__on_render_pre",
            "inner__on_render_post",
            "inner__on_render_after",
            "middle__on_render_post",
            "middle__on_render_after",
            "middle__on_render_pre",
            "inner__on_render_before",
            "inner__on_render_before",
            "inner__on_render_pre",
            "slotted__on_render_before",
            "slotted__on_render_pre",
            "slotted__on_render_post",
            "slotted__on_render_after",
            "inner__on_render_post",
            "inner__on_render_after",
            "inner__on_render_pre",
            "inner__on_render_post",
            "inner__on_render_after",
            "middle__on_render_post",
            "middle__on_render_after",
            "outer__on_render_post",
            "outer__on_render_after",
        ]

    def test_context(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                from_on_before: {{ from_on_before }}
                from_on_before__edited1: {{ from_on_before__edited1 }}
                from_on_before__edited2: {{ from_on_before__edited2 }}
                from_on_render_pre: {{ from_on_render_pre }}
                from_on_render_post: {{ from_on_render_post }}
                from_on_render_pre__edited2: {{ from_on_render_pre__edited2 }}
                from_on_render_post__edited2: {{ from_on_render_post__edited2 }}
                from_on_after: {{ from_on_after }}
            """

            def on_render_before(self, context: Context, template: Template) -> None:
                # Insert value into the Context
                context["from_on_before"] = "1"

            def on_render(self, context: Context, template: Template):
                context["from_on_render_pre"] = "2"
                # Check we can modify entries set by other methods
                context["from_on_before__edited1"] = context["from_on_before"] + " (on_render)"

                _html, _error = yield lambda: template.render(context)

                context["from_on_render_post"] = "3"

            # NOTE: Since this is called AFTER the render, the values set here should NOT
            #       make it to the rendered output.
            def on_render_after(
                self,
                context: Context,
                template: Template,
                html: str | None,
                error: Exception | None,
            ) -> None:
                context["from_on_after"] = "4"
                # Check we can modify entries set by other methods
                # NOTE: These also check that the previous values are available
                context["from_on_before__edited2"] = context["from_on_before"] + " (on_render_after)"
                context["from_on_render_pre__edited2"] = context["from_on_render_pre"] + " (on_render_after)"
                context["from_on_render_post__edited2"] = context["from_on_render_post"] + " (on_render_after)"

        rendered = SimpleComponent.render()

        assertHTMLEqual(
            rendered,
            """
            from_on_before: 1
            from_on_before__edited1: 1 (on_render)
            from_on_before__edited2:
            from_on_render_pre: 2
            from_on_render_post:
            from_on_render_pre__edited2:
            from_on_render_post__edited2:
            from_on_after:
            """,
        )

    def test_template(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                text
            """

            def on_render_before(self, context: Context, template: Template) -> None:
                # Insert text into the Template
                #
                # NOTE: Users should NOT do this, because this will insert the text every time
                #       the component is rendered.
                template.nodelist.append(TextNode("\n---\nFROM_ON_BEFORE"))

            def on_render(self, context: Context, template: Template):
                template.nodelist.append(TextNode("\n---\nFROM_ON_RENDER_PRE"))

                _html, _error = yield lambda: template.render(context)

                template.nodelist.append(TextNode("\n---\nFROM_ON_RENDER_POST"))

            # NOTE: Since this is called AFTER the render, the values set here should NOT
            #       make it to the rendered output.
            def on_render_after(
                self,
                context: Context,
                template: Template,
                html: str | None,
                error: Exception | None,
            ) -> None:
                template.nodelist.append(TextNode("\n---\nFROM_ON_AFTER"))

        rendered = SimpleComponent.render()
        assertHTMLEqual(
            rendered,
            """
            text
            ---
            FROM_ON_BEFORE
            ---
            FROM_ON_RENDER_PRE
            """,
        )

    def test_lambda_yield(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                text
            """

            def on_render(self, context: Context, template: Template):
                html, _error = yield lambda: template.render(context)
                return html + "<p>Hello</p>"

        rendered = SimpleComponent.render()
        assertHTMLEqual(
            rendered,
            "text<p data-djc-id-ca1bc3e>Hello</p>",
        )

        # Works without lambda
        class SimpleComponent2(SimpleComponent):
            def on_render(self, context: Context, template: Template):
                html, _error = yield template.render(context)
                return html + "<p>Hello</p>"

        rendered2 = SimpleComponent2.render()
        assertHTMLEqual(
            rendered2,
            "text<p data-djc-id-ca1bc3f>Hello</p>",
        )

    def test_lambda_yield_error(self):
        def broken_template():
            raise ValueError("BROKEN")

        class SimpleComponent(Component):
            def on_render(self, context: Context, template: Template):
                _html, error = yield lambda: broken_template()
                error.args = ("ERROR MODIFIED",)

        with pytest.raises(
            ValueError, match=re.escape("An error occured while rendering components SimpleComponent:\nERROR MODIFIED")
        ):
            SimpleComponent.render()

        # Does NOT work without lambda
        class SimpleComponent2(SimpleComponent):
            def on_render(self, context: Context, template: Template):
                # This raises an error instead of capturing it,
                # so we never get to modifying the error.
                _html, error = yield broken_template()
                error.args = ("ERROR MODIFIED",)

        with pytest.raises(
            ValueError, match=re.escape("An error occured while rendering components SimpleComponent2:\nBROKEN")
        ):
            SimpleComponent2.render()

    def test_on_render_no_yield(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                text
            """

            def on_render(self, context: Context, template: Template):
                return "OVERRIDDEN"

        rendered = SimpleComponent.render()
        assert rendered == "OVERRIDDEN"

    def test_on_render_reraise_error(self):
        registry.register("broken", self._gen_broken_component())

        class SimpleComponent(Component):
            template: types.django_html = """
                {% component "broken" / %}
            """

            def on_render(self, context: Context, template: Template):
                _html, error = yield lambda: template.render(context)

                raise error from None  # Re-raise original error

        with pytest.raises(ValueError, match=re.escape("BROKEN")):
            SimpleComponent.render()

    def test_on_render_multiple_yields(self):
        registry.register("broken", self._gen_broken_component())

        results = []

        class SimpleComponent(Component):
            template: types.django_html = """
                {% if case == 1 %}
                    {% component "broken" / %}
                {% elif case == 2 %}
                    <div>Hello</div>
                {% elif case == 3 %}
                    <div>There</div>
                {% endif %}
            """

            def on_render(self, context: Context, template: Template | None):
                assert template is not None

                with context.push({"case": 1}):
                    html1, error1 = yield lambda: template.render(context)
                    results.append((html1, error1))

                with context.push({"case": 2}):
                    html2, error2 = yield lambda: template.render(context)
                    results.append((html2.strip(), error2))

                with context.push({"case": 3}):
                    html3, error3 = yield lambda: template.render(context)
                    results.append((html3.strip(), error3))

                html4, error4 = yield "<div>Other result</div>"
                results.append((html4, error4))

                return "<div>Final result</div>"

        result = SimpleComponent.render()
        assert result == '<div data-djc-id-ca1bc3e="">Final result</div>'

        # NOTE: Exceptions are stubborn, comparison evaluates to False even with the same message.
        assert results[0][0] is None
        assert isinstance(results[0][1], ValueError)
        assert results[0][1].args[0] == "An error occured while rendering components broken:\nBROKEN"

        # NOTE: It's important that all the results are wrapped in `<div>`
        #       so we can check if the djc-id attribute was set.
        assert results[1:] == [
            ('<div data-djc-id-ca1bc3e="">Hello</div>', None),
            ('<div data-djc-id-ca1bc3e="">There</div>', None),
            ('<div data-djc-id-ca1bc3e="">Other result</div>', None),
        ]

    @djc_test(
        parametrize=(
            ["template", "action", "method"],
            [
                # on_render - return None
                ["simple", "return_none", "on_render"],
                ["broken", "return_none", "on_render"],
                [None, "return_none", "on_render"],
                # on_render_after - return None
                ["simple", "return_none", "on_render_after"],
                ["broken", "return_none", "on_render_after"],
                [None, "return_none", "on_render_after"],
                # on_render - no return
                ["simple", "no_return", "on_render"],
                ["broken", "no_return", "on_render"],
                [None, "no_return", "on_render"],
                # on_render_after - no return
                ["simple", "no_return", "on_render_after"],
                ["broken", "no_return", "on_render_after"],
                [None, "no_return", "on_render_after"],
                # on_render - raise error
                ["simple", "raise_error", "on_render"],
                ["broken", "raise_error", "on_render"],
                [None, "raise_error", "on_render"],
                # on_render_after - raise error
                ["simple", "raise_error", "on_render_after"],
                ["broken", "raise_error", "on_render_after"],
                [None, "raise_error", "on_render_after"],
                # on_render - return html
                ["simple", "return_html", "on_render"],
                ["broken", "return_html", "on_render"],
                [None, "return_html", "on_render"],
                # on_render_after - return html
                ["simple", "return_html", "on_render_after"],
                ["broken", "return_html", "on_render_after"],
                [None, "return_html", "on_render_after"],
            ],
            None,
        ),
    )
    def test_result_interception(
        self,
        template: Literal["simple", "broken"] | None,
        action: Literal["return_none", "no_return", "raise_error", "return_html"],
        method: Literal["on_render", "on_render_after"],
    ):
        calls: list[str] = []

        Broken = self._gen_broken_component()
        Slotted = self._gen_slotted_component(calls)
        Inner = self._gen_inner_component(calls)
        Middle = self._gen_middle_component(calls)
        Outer = self._gen_outer_component(calls)

        # Make modifications to the components based on the parameters

        # Set template
        if template is None:

            class Inner(Inner):  # type: ignore  # noqa: PGH003
                template = None

        elif template == "broken":

            class Inner(Inner):  # type: ignore  # noqa: PGH003
                template = "{% component 'broken' / %}"

        elif template == "simple":
            pass

        # Set `on_render` behavior
        if method == "on_render":
            if action == "return_none":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render(self, context: Context, template: Template | None):
                        if template is None:
                            yield None
                        else:
                            _html, _error = yield lambda: template.render(context)
                        return None  # noqa: PLR1711

            elif action == "no_return":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render(self, context: Context, template: Template | None):
                        if template is None:
                            yield None
                        else:
                            _html, _error = yield lambda: template.render(context)

            elif action == "raise_error":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render(self, context: Context, template: Template | None):
                        if template is None:
                            yield None
                        else:
                            _html, _error = yield lambda: template.render(context)
                        raise ValueError("ERROR_FROM_ON_RENDER")

            elif action == "return_html":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render(self, context: Context, template: Template | None):
                        if template is None:
                            yield None
                        else:
                            _html, _error = yield lambda: template.render(context)
                        return "HTML_FROM_ON_RENDER"

            else:
                raise pytest.fail(f"Unknown action: {action}")

        # Set `on_render_after` behavior
        elif method == "on_render_after":
            if action == "return_none":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render_after(
                        self,
                        context: Context,
                        template: Template,
                        html: str | None,
                        error: Exception | None,
                    ):
                        return None

            elif action == "no_return":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render_after(
                        self,
                        context: Context,
                        template: Template,
                        html: str | None,
                        error: Exception | None,
                    ):
                        pass

            elif action == "raise_error":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render_after(
                        self,
                        context: Context,
                        template: Template,
                        html: str | None,
                        error: Exception | None,
                    ):
                        raise ValueError("ERROR_FROM_ON_RENDER")

            elif action == "return_html":

                class Inner(Inner):  # type: ignore  # noqa: PGH003
                    def on_render_after(
                        self,
                        context: Context,
                        template: Template,
                        html: str | None,
                        error: Exception | None,
                    ):
                        return "HTML_FROM_ON_RENDER"

            else:
                raise pytest.fail(f"Unknown action: {action}")
        else:
            raise pytest.fail(f"Unknown method: {method}")

        registry.register("broken", Broken)
        registry.register("slotted", Slotted)
        registry.register("inner", Inner)
        registry.register("middle", Middle)
        registry.register("outer", Outer)

        def _gen_expected_output(inner1: str, inner2: str):
            return f"""
                Outer start
                Middle start
                {inner1}
                Middle text
                {inner2}
                Middle end
                Outer text
                Middle start
                {inner1}
                Middle text
                {inner2}
                Middle end
                Outer end
            """

        # Assert based on the behavior
        if template is None:
            # Overriden HTML
            if action == "return_html":
                expected = _gen_expected_output(inner1="HTML_FROM_ON_RENDER", inner2="HTML_FROM_ON_RENDER")
                result = Outer.render()
                assertHTMLEqual(result, expected)
            # Overriden error
            elif action == "raise_error":
                with pytest.raises(ValueError, match="ERROR_FROM_ON_RENDER"):
                    Outer.render()
            # Original output
            elif action in ["return_none", "no_return"]:
                expected = _gen_expected_output(inner1="", inner2="")
                result = Outer.render()
                assertHTMLEqual(result, expected)
            else:
                raise pytest.fail(f"Unknown action: {action}")

        elif template == "simple":
            # Overriden HTML
            if action == "return_html":
                expected = _gen_expected_output(inner1="HTML_FROM_ON_RENDER", inner2="HTML_FROM_ON_RENDER")
                result = Outer.render()
                assertHTMLEqual(result, expected)
            # Overriden error
            elif action == "raise_error":
                with pytest.raises(ValueError, match="ERROR_FROM_ON_RENDER"):
                    Outer.render()
            # Original output
            elif action in ["return_none", "no_return"]:
                expected = _gen_expected_output(
                    inner1="Inner start Hello from slotted Inner end",
                    inner2="Inner start Inner end",
                )
                result = Outer.render()
                assertHTMLEqual(result, expected)
            else:
                raise pytest.fail(f"Unknown action: {action}")

        elif template == "broken":
            # Overriden HTML
            if action == "return_html":
                expected = _gen_expected_output(inner1="HTML_FROM_ON_RENDER", inner2="HTML_FROM_ON_RENDER")
                result = Outer.render()
                assertHTMLEqual(result, expected)
            # Overriden error
            elif action == "raise_error":
                with pytest.raises(ValueError, match="ERROR_FROM_ON_RENDER"):
                    Outer.render()
            # Original output
            elif action in ["return_none", "no_return"]:
                with pytest.raises(ValueError, match="broken"):
                    Outer.render()
            else:
                raise pytest.fail(f"Unknown action: {action}")

        else:
            raise pytest.fail(f"Unknown template: {template}")


@djc_test
class TestComponentHelpers:
    def test_all_components(self):
        # NOTE: When running all tests, this list may already have some components
        # as some components in test files are defined on module level, outside of
        # `djc_test` decorator.
        all_comps_before = len(all_components())

        # Components don't have to be registered to be included in the list
        class TestComponent(Component):
            template: types.django_html = """
                Hello from test
            """

        assert len(all_components()) == all_comps_before + 1

        @register("test2")
        class Test2Component(Component):
            template: types.django_html = """
                Hello from test2
            """

        assert len(all_components()) == all_comps_before + 2
