"""
Tests focusing on the Component class.
For tests focusing on the `component` tag, see `test_templatetags_component.py`
"""

import re
from typing import Any, Dict, Tuple, no_type_check
from typing_extensions import NotRequired, TypedDict

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse
from django.template import Context, RequestContext, Template, TemplateSyntaxError
from django.template.base import TextNode
from django.test import Client
from django.urls import path
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import (
    Component,
    ComponentView,
    SlotContent,
    Slot,
    all_components,
    get_component_by_class_id,
    register,
    types,
)
from django_components.slots import SlotRef
from django_components.urls import urlpatterns as dc_urlpatterns

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


# Client for testing endpoints via requests
class CustomClient(Client):
    def __init__(self, urlpatterns=None, *args, **kwargs):
        import types

        if urlpatterns:
            urls_module = types.ModuleType("urls")
            urls_module.urlpatterns = urlpatterns + dc_urlpatterns  # type: ignore
            settings.ROOT_URLCONF = urls_module
        else:
            settings.ROOT_URLCONF = __name__
        settings.SECRET_KEY = "secret"  # noqa
        super().__init__(*args, **kwargs)


# TODO_REMOVE_IN_V1 - Superseded by `self.get_template` in v1
@djc_test
class TestComponentOldTemplateApi:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_get_template_string(self, components_settings):
        class SimpleComponent(Component):
            def get_template_string(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

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
            Variable: <strong data-djc-id-a1bc3e>test</strong>
            """,
        )


@djc_test
class TestComponent:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_empty_component(self, components_settings):
        class EmptyComponent(Component):
            pass

        with pytest.raises(ImproperlyConfigured):
            EmptyComponent("empty_component")._get_template(Context({}), "123")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_string_static_inlined(self, components_settings):
        class SimpleComponent(Component):
            template: types.django_html = """
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
            Variable: <strong data-djc-id-a1bc3e>test</strong>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_string_dynamic(self, components_settings):
        class SimpleComponent(Component):
            def get_template(self, context):
                content: types.django_html = """
                    Variable: <strong>{{ variable }}</strong>
                """
                return content

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
            Variable: <strong data-djc-id-a1bc3e>test</strong>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_file_static(self, components_settings):
        class SimpleComponent(Component):
            template_file = "simple_template.html"

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
            Variable: <strong data-djc-id-a1bc3e>test</strong>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_file_static__compat(self, components_settings):
        class SimpleComponent(Component):
            template_name = "simple_template.html"

            def get_context_data(self, variable=None):
                return {
                    "variable": variable,
                }

            class Media:
                css = "style.css"
                js = "script.js"

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
            Variable: <strong data-djc-id-a1bc3e>test</strong>
            """,
        )

        comp = SimpleComponent()
        assert comp.template_name == "simple_template.html"
        assert comp.template_file == "simple_template.html"

        # NOTE: Setting `template_file` on INSTANCE is not supported, as users should work
        #       with classes and not instances. This is tested for completeness.
        comp.template_name = "other_template_2.html"
        assert comp.template_name == "other_template_2.html"
        assert comp.template_file == "other_template_2.html"
        assert SimpleComponent.template_name == "other_template_2.html"
        assert SimpleComponent.template_file == "other_template_2.html"

        SimpleComponent.template_name = "simple_template.html"
        rendered = comp.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-a1bc3f>test</strong>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_template_file_dynamic(self, components_settings):
        class SvgComponent(Component):
            def get_context_data(self, name, css_class="", title="", **attrs):
                return {
                    "name": name,
                    "css_class": css_class,
                    "title": title,
                    **attrs,
                }

            def get_template_name(self, context):
                return f"dynamic_{context['name']}.svg"

        assertHTMLEqual(
            SvgComponent.render(kwargs={"name": "svg1"}),
            """
            <svg data-djc-id-a1bc3e>Dynamic1</svg>
            """,
        )
        assertHTMLEqual(
            SvgComponent.render(kwargs={"name": "svg2"}),
            """
            <svg data-djc-id-a1bc3f>Dynamic2</svg>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_allows_to_return_template(self, components_settings):
        class TestComponent(Component):
            def get_context_data(self, variable, **attrs):
                return {
                    "variable": variable,
                }

            def get_template(self, context):
                template_str = "Variable: <strong>{{ variable }}</strong>"
                return Template(template_str)

        rendered = TestComponent.render(kwargs={"variable": "test"})
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-a1bc3e>test</strong>
            """,
        )

    def test_input(self):
        class TestComponent(Component):
            @no_type_check
            def get_context_data(self, var1, var2, variable, another, **attrs):
                assert self.input.args == [123, "str"]
                assert self.input.kwargs == {"variable": "test", "another": 1}
                assert isinstance(self.input.context, Context)
                assert list(self.input.slots.keys()) == ["my_slot"]
                assert self.input.slots["my_slot"](Context(), None, None) == "MY_SLOT"

                return {
                    "variable": variable,
                }

            @no_type_check
            def get_template(self, context):
                assert self.input.args == [123, "str"]
                assert self.input.kwargs == {"variable": "test", "another": 1}
                assert isinstance(self.input.context, Context)
                assert list(self.input.slots.keys()) == ["my_slot"]
                assert self.input.slots["my_slot"](Context(), None, None) == "MY_SLOT"

                template_str: types.django_html = """
                    {% load component_tags %}
                    Variable: <strong>{{ variable }}</strong>
                    {% slot 'my_slot' / %}
                """
                return Template(template_str)

        rendered = TestComponent.render(
            kwargs={"variable": "test", "another": 1},
            args=(123, "str"),
            slots={"my_slot": "MY_SLOT"},
        )

        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-a1bc3e>test</strong> MY_SLOT
            """,
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

            def get_context_data(self):
                data = self.inject("my_provide")
                data["data1"]  # This should raise TypeError
                return {"data": data}

        @register("provider")
        class Provider(Component):
            def get_context_data(self, data: Any) -> Any:
                return {"data": data}

            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" data=data %}
                    {% slot "content" default / %}
                {% endprovide %}
            """

        @register("parent")
        class Parent(Component):
            def get_context_data(self, data: Any) -> Any:
                return {"data": data}

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
                "tuple indices must be integers or slices, not str"
            ),
        ):
            Root.render()

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

            def get_context_data(self):
                return None

        assert SimpleComponent.render() == "Hello"

    def test_typing(self):
        # Types
        ButtonArgs = Tuple[str, ...]

        class ButtonKwargs(TypedDict):
            name: str
            age: int
            maybe_var: NotRequired[int]

        class ButtonFooterSlotData(TypedDict):
            value: int

        class ButtonSlots(TypedDict):
            # Use `SlotContent` when you want to allow either function (`Slot` instance)
            # or plain string.
            header: SlotContent
            # Use `Slot` for slot functions. The generic specifies the data available to the slot function.
            footer: NotRequired[Slot[ButtonFooterSlotData]]

        # Data returned from `get_context_data`
        class ButtonData(TypedDict):
            data1: str
            data2: int

        # Data returned from `get_js_data`
        class ButtonJsData(TypedDict):
            js_data1: str
            js_data2: int

        # Data returned from `get_css_data`
        class ButtonCssData(TypedDict):
            css_data1: str
            css_data2: int

        # Tests - We simply check that these don't raise any errors
        #         nor any type errors.
        ButtonType1 = Component[ButtonArgs, ButtonKwargs, ButtonSlots, ButtonData, ButtonJsData, ButtonCssData]
        ButtonType2 = Component[ButtonArgs, ButtonKwargs, ButtonSlots, ButtonData, ButtonJsData]
        ButtonType3 = Component[ButtonArgs, ButtonKwargs, ButtonSlots, ButtonData]
        ButtonType4 = Component[ButtonArgs, ButtonKwargs, ButtonSlots]
        ButtonType5 = Component[ButtonArgs, ButtonKwargs]
        ButtonType6 = Component[ButtonArgs]

        class Button1(ButtonType1):
            template = "<button>Click me!</button>"

        class Button2(ButtonType2):
            template = "<button>Click me!</button>"

        class Button3(ButtonType3):
            template = "<button>Click me!</button>"

        class Button4(ButtonType4):
            template = "<button>Click me!</button>"

        class Button5(ButtonType5):
            template = "<button>Click me!</button>"

        class Button6(ButtonType6):
            template = "<button>Click me!</button>"

        Button1.render(
            args=("arg1", "arg2"),
            kwargs={"name": "name", "age": 123},
            slots={"header": "HEADER", "footer": Slot(lambda ctx, slot_data, slot_ref: "FOOTER")},
        )

        Button2.render(
            args=("arg1", "arg2"),
            kwargs={"name": "name", "age": 123},
            slots={"header": "HEADER", "footer": Slot(lambda ctx, slot_data, slot_ref: "FOOTER")},
        )

        Button3.render(
            args=("arg1", "arg2"),
            kwargs={"name": "name", "age": 123},
            slots={"header": "HEADER", "footer": Slot(lambda ctx, slot_data, slot_ref: "FOOTER")},
        )

        Button4.render(
            args=("arg1", "arg2"),
            kwargs={"name": "name", "age": 123},
            slots={"header": "HEADER", "footer": Slot(lambda ctx, slot_data, slot_ref: "FOOTER")},
        )

        Button5.render(
            args=("arg1", "arg2"),
            kwargs={"name": "name", "age": 123},
        )

        Button6.render(
            args=("arg1", "arg2"),
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

            def get_context_data(self, the_arg2=None, *args, the_kwarg=None, **kwargs):
                return {
                    "the_arg2": the_arg2,
                    "the_kwarg": the_kwarg,
                    "args": args,
                    "kwargs": kwargs,
                }

        rendered = SimpleComponent.render()
        assertHTMLEqual(
            rendered,
            """
            the_arg2: None
            args: ()
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

            def get_context_data(self, the_arg, the_arg2=None, *args, the_kwarg, **kwargs):
                return {
                    "the_arg": the_arg,
                    "the_arg2": the_arg2,
                    "the_kwarg": the_kwarg,
                    "args": args,
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
            args: ('three',)
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

            def get_context_data(self, the_arg, the_arg2=None, *args, the_kwarg, **kwargs):
                return {
                    "the_arg": the_arg,
                    "the_arg2": the_arg2,
                    "the_kwarg": the_kwarg,
                    "args": args,
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
            args: ('three',)
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

            def get_context_data(self, the_arg, the_kwarg=None, **kwargs):
                return {
                    "the_arg": the_arg,
                    "the_kwarg": the_kwarg,
                    "kwargs": kwargs,
                }

        def first_slot(ctx: Context, slot_data: Dict, slot_ref: SlotRef):
            assert isinstance(ctx, Context)
            # NOTE: Since the slot has access to the Context object, it should behave
            # the same way as it does in templates - when in "isolated" mode, then the
            # slot fill has access only to the "root" context, but not to the data of
            # get_context_data() of SimpleComponent.
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

        SimpleComponent.render(
            slots={"first": "FIRST_SLOT"},
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
            <custom-template data-djc-id-a1bc3e>
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
            <custom-template data-djc-id-a1bc3e>
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
            <custom-template data-djc-id-a1bc3e>
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

            def get_context_data(self, *args, how: str, **kwargs):
                return {"how": how}

            class View(ComponentView):
                def get(self, request):
                    how = "via GET request"

                    return self.component.render_to_response(
                        context=RequestContext(self.request),
                        kwargs=self.component.get_context_data(how=how),
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
            <kbd data-djc-id-a1bc3e>
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

        rendered = SimpleComponent.render(render_dependencies=False)
        assertHTMLEqual(
            rendered,
            """
            <!DOCTYPE html>
            <html data-djc-id-a1bc3e lang="en">
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

            def get_context_data(self, **attrs):
                return {
                    "id": self.id,
                }

        rendered = TestComponent.render()
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-a1bc3e>a1bc3e</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_render_to_response_can_access_instance(self, components_settings):
        class TestComponent(Component):
            template = "Variable: <strong>{{ id }}</strong>"

            def get_context_data(self, **attrs):
                return {
                    "id": self.id,
                }

        rendered_resp = TestComponent.render_to_response()
        assertHTMLEqual(
            rendered_resp.content.decode("utf-8"),
            "Variable: <strong data-djc-id-a1bc3e>a1bc3e</strong>",
        )


@djc_test
class TestComponentHook:
    def test_on_render_before(self):
        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Hello from nested
                <div>
                    {% slot "content" default / %}
                </div>
            """

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                args: {{ args|safe }}
                kwargs: {{ kwargs|safe }}
                ---
                from_on_before: {{ from_on_before }}
                ---
                {% component "nested" %}
                    Hello from simple
                {% endcomponent %}
            """

            def get_context_data(self, *args, **kwargs):
                return {
                    "args": args,
                    "kwargs": kwargs,
                }

            def on_render_before(self, context: Context, template: Template) -> None:
                # Insert value into the Context
                context["from_on_before"] = ":)"

                # Insert text into the Template
                #
                # NOTE: Users should NOT do this, because this will insert the text every time
                #       the component is rendered.
                template.nodelist.append(TextNode("\n---\nFROM_ON_BEFORE"))

        rendered = SimpleComponent.render()
        assertHTMLEqual(
            rendered,
            """
            args: ()
            kwargs: {}
            ---
            from_on_before: :)
            ---
            Hello from nested
            <div data-djc-id-a1bc3e data-djc-id-a1bc40>
                Hello from simple
            </div>
            ---
            FROM_ON_BEFORE
            """,
        )

    # Check that modifying the context or template does nothing
    def test_on_render_after(self):
        captured_content = None

        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Hello from nested
                <div>
                    {% slot "content" default / %}
                </div>
            """

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                args: {{ args|safe }}
                kwargs: {{ kwargs|safe }}
                ---
                from_on_after: {{ from_on_after }}
                ---
                {% component "nested" %}
                    Hello from simple
                {% endcomponent %}
            """

            def get_context_data(self, *args, **kwargs):
                return {
                    "args": args,
                    "kwargs": kwargs,
                }

            # Check that modifying the context or template does nothing
            def on_render_after(self, context: Context, template: Template, content: str) -> None:
                # Insert value into the Context
                context["from_on_after"] = ":)"

                # Insert text into the Template
                template.nodelist.append(TextNode("\n---\nFROM_ON_AFTER"))

                nonlocal captured_content
                captured_content = content

        rendered = SimpleComponent.render()

        assertHTMLEqual(
            captured_content,
            """
            args: ()
            kwargs: {}
            ---
            from_on_after:
            ---
            Hello from nested
            <div data-djc-id-a1bc3e data-djc-id-a1bc40>
                Hello from simple
            </div>
            """,
        )
        assertHTMLEqual(
            rendered,
            """
            args: ()
            kwargs: {}
            ---
            from_on_after:
            ---
            Hello from nested
            <div data-djc-id-a1bc3e data-djc-id-a1bc40>
                Hello from simple
            </div>
            """,
        )

    # Check that modifying the context or template does nothing
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_on_render_after_override_output(self, components_settings):
        captured_content = None

        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Hello from nested
                <div>
                    {% slot "content" default / %}
                </div>
            """

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                args: {{ args|safe }}
                kwargs: {{ kwargs|safe }}
                ---
                from_on_before: {{ from_on_before }}
                ---
                {% component "nested" %}
                    Hello from simple
                {% endcomponent %}
            """

            def get_context_data(self, *args, **kwargs):
                return {
                    "args": args,
                    "kwargs": kwargs,
                }

            def on_render_after(self, context: Context, template: Template, content: str) -> str:
                nonlocal captured_content
                captured_content = content

                return "Chocolate cookie recipe: " + content

        rendered = SimpleComponent.render()

        assertHTMLEqual(
            captured_content,
            """
            args: ()
            kwargs: {}
            ---
            from_on_before:
            ---
            Hello from nested
            <div data-djc-id-a1bc3e data-djc-id-a1bc40>
                Hello from simple
            </div>
            """,
        )
        assertHTMLEqual(
            rendered,
            """
            Chocolate cookie recipe:
            args: ()
            kwargs: {}
            ---
            from_on_before:
            ---
            Hello from nested
            <div data-djc-id-a1bc3e data-djc-id-a1bc40>
                Hello from simple
            </div>
            """,
        )

    def test_on_render_before_after_same_context(self):
        context_in_before = None
        context_in_after = None

        @register("nested")
        class NestedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Hello from nested
                <div>
                    {% slot "content" default / %}
                </div>
            """

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                args: {{ args|safe }}
                kwargs: {{ kwargs|safe }}
                ---
                from_on_after: {{ from_on_after }}
                ---
                {% component "nested" %}
                    Hello from simple
                {% endcomponent %}
            """

            def get_context_data(self, *args, **kwargs):
                return {
                    "args": args,
                    "kwargs": kwargs,
                }

            def on_render_before(self, context: Context, template: Template) -> None:
                context["from_on_before"] = ":)"
                nonlocal context_in_before
                context_in_before = context

            # Check that modifying the context or template does nothing
            def on_render_after(self, context: Context, template: Template, html: str) -> None:
                context["from_on_after"] = ":)"
                nonlocal context_in_after
                context_in_after = context

        SimpleComponent.render()

        assert context_in_before == context_in_after
        assert "from_on_before" in context_in_before  # type: ignore[operator]
        assert "from_on_after" in context_in_after  # type: ignore[operator]


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
