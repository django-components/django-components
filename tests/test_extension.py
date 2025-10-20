import gc
from typing import Any, Callable, Dict, List, Optional, cast

import pytest
from django.http import HttpRequest, HttpResponse
from django.template import Context, Origin, Template
from django.test import Client

from django_components import Component, Slot, SlotNode, register, registry
from django_components.app_settings import app_settings
from django_components.component_registry import ComponentRegistry
from django_components.extension import (
    ComponentExtension,
    ExtensionComponentConfig,
    OnComponentClassCreatedContext,
    OnComponentClassDeletedContext,
    OnComponentDataContext,
    OnComponentInputContext,
    OnComponentRegisteredContext,
    OnComponentRenderedContext,
    OnComponentUnregisteredContext,
    OnCssLoadedContext,
    OnJsLoadedContext,
    OnRegistryCreatedContext,
    OnRegistryDeletedContext,
    OnSlotRenderedContext,
    OnTemplateCompiledContext,
    OnTemplateLoadedContext,
    URLRoute,
)
from django_components.extensions.cache import CacheExtension
from django_components.extensions.debug_highlight import DebugHighlightExtension
from django_components.extensions.defaults import DefaultsExtension
from django_components.extensions.dependencies import DependenciesExtension
from django_components.extensions.view import ViewExtension
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


def dummy_view(request: HttpRequest):
    # Test that the request object is passed to the view
    assert isinstance(request, HttpRequest)
    return HttpResponse("Hello, world!")


def dummy_view_2(request: HttpRequest, id: int, name: str):  # noqa: ARG001, A002
    return HttpResponse(f"Hello, world! {id} {name}")


# TODO_V1 - Remove
class LegacyExtension(ComponentExtension):
    name = "legacy"

    class ExtensionClass(ExtensionComponentConfig):
        foo = "1"
        bar = "2"

        @classmethod
        def baz(cls):
            return "3"


class DummyExtension(ComponentExtension):
    """Test extension that tracks all hook calls and their arguments."""

    name = "test_extension"

    class ComponentConfig(ExtensionComponentConfig):
        foo = "1"
        bar = "2"

        @classmethod
        def baz(cls):
            return "3"

    def __init__(self) -> None:
        self.calls: Dict[str, List[Any]] = {
            "on_component_class_created": [],
            "on_component_class_deleted": [],
            "on_registry_created": [],
            "on_registry_deleted": [],
            "on_component_registered": [],
            "on_component_unregistered": [],
            "on_component_input": [],
            "on_component_data": [],
            "on_component_rendered": [],
            "on_slot_rendered": [],
            "on_template_loaded": [],
            "on_template_compiled": [],
            "on_js_loaded": [],
            "on_css_loaded": [],
        }

    urls = [
        URLRoute(path="dummy-view/", handler=dummy_view, name="dummy"),
        URLRoute(path="dummy-view-2/<int:id>/<str:name>/", handler=dummy_view_2, name="dummy-2"),
    ]

    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        # NOTE: Store only component name to avoid strong references
        self.calls["on_component_class_created"].append(ctx.component_cls.__name__)

    def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
        # NOTE: Store only component name to avoid strong references
        self.calls["on_component_class_deleted"].append(ctx.component_cls.__name__)

    def on_registry_created(self, ctx: OnRegistryCreatedContext) -> None:
        # NOTE: Store only registry object ID to avoid strong references
        self.calls["on_registry_created"].append(id(ctx.registry))

    def on_registry_deleted(self, ctx: OnRegistryDeletedContext) -> None:
        # NOTE: Store only registry object ID to avoid strong references
        self.calls["on_registry_deleted"].append(id(ctx.registry))

    def on_component_registered(self, ctx: OnComponentRegisteredContext) -> None:
        self.calls["on_component_registered"].append(ctx)

    def on_component_unregistered(self, ctx: OnComponentUnregisteredContext) -> None:
        self.calls["on_component_unregistered"].append(ctx)

    def on_component_input(self, ctx: OnComponentInputContext) -> None:
        self.calls["on_component_input"].append(ctx)

    def on_component_data(self, ctx: OnComponentDataContext) -> None:
        self.calls["on_component_data"].append(ctx)

    def on_component_rendered(self, ctx: OnComponentRenderedContext) -> None:
        self.calls["on_component_rendered"].append(ctx)

    def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> None:
        self.calls["on_slot_rendered"].append(ctx)

    def on_template_loaded(self, ctx):
        self.calls["on_template_loaded"].append(ctx)

    def on_template_compiled(self, ctx):
        self.calls["on_template_compiled"].append(ctx)

    def on_js_loaded(self, ctx):
        self.calls["on_js_loaded"].append(ctx)

    def on_css_loaded(self, ctx):
        self.calls["on_css_loaded"].append(ctx)


class DummyNestedExtension(ComponentExtension):
    name = "test_nested_extension"

    urls = [
        URLRoute(
            path="nested-view/",
            children=[
                URLRoute(path="<int:id>/<str:name>/", handler=dummy_view_2, name="dummy-2"),
            ],
            name="dummy",
        ),
    ]


class RenderExtension(ComponentExtension):
    name = "render"


class SlotOverrideExtension(ComponentExtension):
    name = "slot_override"

    def on_slot_rendered(self, ctx: OnSlotRenderedContext):
        return "OVERRIDEN BY EXTENSION"


class ErrorOnComponentRenderedExtension(ComponentExtension):
    name = "error_on_component_rendered"

    def on_component_rendered(self, ctx: OnComponentRenderedContext):
        raise RuntimeError("Custom error from extension")


class ReturnHtmlOnComponentRenderedExtension(ComponentExtension):
    name = "return_html_on_component_rendered"

    def on_component_rendered(self, ctx: OnComponentRenderedContext):
        return f"<div>OVERRIDDEN: {ctx.result}</div>"


def with_component_cls(on_created: Callable):
    class TempComponent(Component):
        template = "Hello {{ name }}!"

        def get_template_data(self, args, kwargs, slots, context):
            return {"name": kwargs.get("name", "World")}

    on_created()


def with_registry(on_created: Callable):
    registry = ComponentRegistry()

    on_created(registry)


class OverrideAssetExtension(ComponentExtension):
    name = "override_asset_extension"

    def on_template_loaded(self, ctx):
        return "OVERRIDDEN TEMPLATE"

    def on_js_loaded(self, ctx):
        return "OVERRIDDEN JS"

    def on_css_loaded(self, ctx):
        return "OVERRIDDEN CSS"


@djc_test
class TestExtensions:
    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_extensions_setting(self):
        assert len(app_settings.EXTENSIONS) == 6
        assert isinstance(app_settings.EXTENSIONS[0], CacheExtension)
        assert isinstance(app_settings.EXTENSIONS[1], DefaultsExtension)
        assert isinstance(app_settings.EXTENSIONS[2], DependenciesExtension)
        assert isinstance(app_settings.EXTENSIONS[3], ViewExtension)
        assert isinstance(app_settings.EXTENSIONS[4], DebugHighlightExtension)
        assert isinstance(app_settings.EXTENSIONS[5], DummyExtension)

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_access_component_from_extension(self):
        class TestAccessComp(Component):
            template = "Hello {{ name }}!"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

        ext_class = TestAccessComp.TestExtension  # type: ignore[attr-defined]
        assert issubclass(ext_class, ComponentExtension.ComponentConfig)
        assert ext_class.component_class is TestAccessComp

        # NOTE: Required for test_component_class_lifecycle_hooks to work
        del TestAccessComp
        gc.collect()

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_instantiate_ext_component_config_none(self):
        config = DummyExtension.ComponentConfig(None)
        assert isinstance(config, DummyExtension.ComponentConfig)

    def test_raises_on_extension_name_conflict(self):
        @djc_test(components_settings={"extensions": [RenderExtension]})
        def inner():
            pass

        with pytest.raises(ValueError, match="Extension name 'render' conflicts with existing Component class API"):
            inner()

    def test_raises_on_multiple_extensions_with_same_name(self):
        @djc_test(components_settings={"extensions": [DummyExtension, DummyExtension]})
        def inner():
            pass

        with pytest.raises(ValueError, match="Multiple extensions cannot have the same name 'test_extension'"):
            inner()

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_nested_extension_config_inheritance(self):
        component: Optional[Component] = None

        class TestExtensionParent:
            parent_var = "from_parent"

        class MyComponent(Component):
            template = "hello"

            class TestExtension(TestExtensionParent):
                nested_var = "from_nested"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal component
                component = self

        # Rendering the component will execute get_template_data
        MyComponent.render()

        assert component is not None
        # Check properties from DummyExtension.ComponentConfig
        assert component.test_extension.foo == "1"  # type: ignore[attr-defined]
        assert component.test_extension.bar == "2"  # type: ignore[attr-defined]
        # Check properties from nested class
        assert component.test_extension.nested_var == "from_nested"  # type: ignore[attr-defined]
        # Check properties from parent of nested class
        assert component.test_extension.parent_var == "from_parent"  # type: ignore[attr-defined]


@djc_test
class TestExtensionHooks:
    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_component_class_lifecycle_hooks(self):
        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        assert len(extension.calls["on_component_class_created"]) == 0
        assert len(extension.calls["on_component_class_deleted"]) == 0

        did_call_on_comp_cls_created = False

        def on_comp_cls_created():
            nonlocal did_call_on_comp_cls_created
            did_call_on_comp_cls_created = True

            # Verify on_component_class_created was called
            assert len(extension.calls["on_component_class_created"]) == 1
            assert extension.calls["on_component_class_created"][0] == "TempComponent"

        # Create a component class in a separate scope, to avoid any references from within
        # this test function, so we can garbage collect it after the function returns
        with_component_cls(on_comp_cls_created)
        assert did_call_on_comp_cls_created

        # This should trigger the garbage collection of the component class
        gc.collect()

        # Verify on_component_class_deleted was called
        # NOTE: The previous test, `test_access_component_from_extension`, is sometimes
        # garbage-collected too late, in which case it's included in `on_component_class_deleted`.
        # So in the test we check only for the last call.
        assert len(extension.calls["on_component_class_deleted"]) >= 1
        assert extension.calls["on_component_class_deleted"][-1] == "TempComponent"

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_registry_lifecycle_hooks(self):
        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        assert len(extension.calls["on_registry_created"]) == 0
        assert len(extension.calls["on_registry_deleted"]) == 0

        did_call_on_registry_created = False
        reg_id = None

        def on_registry_created(reg):
            nonlocal did_call_on_registry_created
            nonlocal reg_id
            did_call_on_registry_created = True
            reg_id = id(reg)

            # Verify on_registry_created was called
            assert len(extension.calls["on_registry_created"]) == 1
            assert extension.calls["on_registry_created"][0] == reg_id

        with_registry(on_registry_created)
        assert did_call_on_registry_created
        assert reg_id is not None

        gc.collect()

        # Verify on_registry_deleted was called
        assert len(extension.calls["on_registry_deleted"]) == 1
        assert extension.calls["on_registry_deleted"][0] == reg_id

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_component_registration_hooks(self):
        class TestComponent(Component):
            template = "Hello {{ name }}!"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

        registry.register("test_comp", TestComponent)
        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        # Verify on_component_registered was called
        assert len(extension.calls["on_component_registered"]) == 1
        reg_call: OnComponentRegisteredContext = extension.calls["on_component_registered"][0]
        assert reg_call.registry == registry
        assert reg_call.name == "test_comp"
        assert reg_call.component_cls == TestComponent

        registry.unregister("test_comp")

        # Verify on_component_unregistered was called
        assert len(extension.calls["on_component_unregistered"]) == 1
        unreg_call: OnComponentUnregisteredContext = extension.calls["on_component_unregistered"][0]
        assert unreg_call.registry == registry
        assert unreg_call.name == "test_comp"
        assert unreg_call.component_cls == TestComponent

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_component_render_hooks(self):
        @register("test_comp")
        class TestComponent(Component):
            template = "Hello {{ name }}!"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

            def get_js_data(self, args, kwargs, slots, context):
                return {"script": "console.log('Hello!')"}

            def get_css_data(self, args, kwargs, slots, context):
                return {"style": "body { color: blue; }"}

        # Render the component with some args and kwargs
        test_context = Context({"foo": "bar"})
        test_slots = {"content": "Some content"}
        TestComponent.render(context=test_context, args=("arg1", "arg2"), kwargs={"name": "Test"}, slots=test_slots)

        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        # Verify on_component_input was called with correct args
        assert len(extension.calls["on_component_input"]) == 1
        input_call: OnComponentInputContext = extension.calls["on_component_input"][0]
        assert input_call.component_cls == TestComponent
        assert isinstance(input_call.component_id, str)
        assert input_call.args == ["arg1", "arg2"]
        assert input_call.kwargs == {"name": "Test"}
        assert len(input_call.slots) == 1
        assert isinstance(input_call.slots["content"], Slot)
        assert input_call.context == test_context

        # Verify on_component_data was called with correct args
        assert len(extension.calls["on_component_data"]) == 1
        data_call: OnComponentDataContext = extension.calls["on_component_data"][0]
        assert data_call.component_cls == TestComponent
        assert isinstance(data_call.component_id, str)
        assert data_call.template_data == {"name": "Test"}
        assert data_call.js_data == {"script": "console.log('Hello!')"}
        assert data_call.css_data == {"style": "body { color: blue; }"}

        # Verify on_component_rendered was called with correct args
        assert len(extension.calls["on_component_rendered"]) == 1
        rendered_call: OnComponentRenderedContext = extension.calls["on_component_rendered"][0]
        assert rendered_call.component_cls == TestComponent
        assert isinstance(rendered_call.component, TestComponent)
        assert isinstance(rendered_call.component_id, str)
        assert rendered_call.result == "<!-- _RENDERED TestComponent_f4a4f0,ca1bc3e,, -->Hello Test!"
        assert rendered_call.error is None

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_component_render_hooks__error(self):
        @register("test_comp")
        class TestComponent(Component):
            template = "Hello {{ name }}!"

            def on_render_after(self, context, template, result, error):
                raise Exception("Oopsie woopsie")

        with pytest.raises(Exception, match="Oopsie woopsie"):
            # Render the component with some args and kwargs
            TestComponent.render(
                context=Context({"foo": "bar"}),
                args=("arg1", "arg2"),
                kwargs={"name": "Test"},
                slots={"content": "Some content"},
            )

        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        # Verify on_component_rendered was called with correct args
        assert len(extension.calls["on_component_rendered"]) == 1
        rendered_call: OnComponentRenderedContext = extension.calls["on_component_rendered"][0]
        assert rendered_call.component_cls == TestComponent
        assert isinstance(rendered_call.component, TestComponent)
        assert isinstance(rendered_call.component_id, str)
        assert rendered_call.result is None
        assert isinstance(rendered_call.error, Exception)
        assert str(rendered_call.error) == "An error occured while rendering components TestComponent:\nOopsie woopsie"

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_on_slot_rendered(self):
        @register("test_comp")
        class TestComponent(Component):
            template = "Hello {% slot 'content' required default / %}!"

        # Render the component with some args and kwargs
        test_context = Context({"foo": "bar"})
        rendered = TestComponent.render(
            context=test_context,
            args=("arg1", "arg2"),
            kwargs={"name": "Test"},
            slots={"content": "Some content"},
        )

        assert rendered == "Hello Some content!"

        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        # Verify on_slot_rendered was called with correct args
        assert len(extension.calls["on_slot_rendered"]) == 1
        slot_call: OnSlotRenderedContext = extension.calls["on_slot_rendered"][0]
        assert isinstance(slot_call.component, TestComponent)
        assert slot_call.component_cls == TestComponent

        assert slot_call.component_id == "ca1bc3e"
        assert isinstance(slot_call.slot, Slot)
        assert slot_call.slot_name == "content"
        assert isinstance(slot_call.slot_node, SlotNode)
        assert slot_call.slot_node.template_name.endswith("test_extension.py::TestComponent")  # type: ignore[union-attr]
        assert slot_call.slot_node.template_component == TestComponent
        assert slot_call.slot_is_required is True
        assert slot_call.slot_is_default is True
        assert slot_call.result == "Some content"

    @djc_test(components_settings={"extensions": [SlotOverrideExtension]})
    def test_on_slot_rendered__override(self):
        @register("test_comp")
        class TestComponent(Component):
            template = "Hello {% slot 'content' required default / %}!"

        rendered = TestComponent.render(
            slots={"content": "Some content"},
        )

        assert rendered == "Hello OVERRIDEN BY EXTENSION!"

    @djc_test(components_settings={"extensions": [ErrorOnComponentRenderedExtension]})
    def test_on_component_rendered__error_from_extension(self):
        @register("test_comp_error_ext")
        class TestComponent(Component):
            template = "Hello {{ name }}!"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

        with pytest.raises(RuntimeError, match="Custom error from extension"):
            TestComponent.render(args=(), kwargs={"name": "Test"})

    @djc_test(components_settings={"extensions": [ReturnHtmlOnComponentRenderedExtension]})
    def test_on_component_rendered__return_html_from_extension(self):
        @register("test_comp_html_ext")
        class TestComponent(Component):
            template = "Hello {{ name }}!"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

        rendered = TestComponent.render(args=(), kwargs={"name": "Test"})
        assert rendered == "<div>OVERRIDDEN: Hello Test!</div>"

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_asset_hooks__inlined(self):
        @register("test_comp_hooks")
        class TestComponent(Component):
            template = "Hello {{ name }}!"
            js = "console.log('hi');"
            css = "body { color: red; }"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

        # Render the component to trigger all hooks
        TestComponent.render(args=(), kwargs={"name": "Test"})

        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        # on_template_loaded
        assert len(extension.calls["on_template_loaded"]) == 1
        ctx1: OnTemplateLoadedContext = extension.calls["on_template_loaded"][0]
        assert ctx1.component_cls == TestComponent
        assert ctx1.content == "Hello {{ name }}!"
        assert isinstance(ctx1.origin, Origin)
        assert ctx1.origin.name.endswith("test_extension.py::TestComponent")
        assert ctx1.name is None

        # on_template_compiled
        assert len(extension.calls["on_template_compiled"]) == 1
        ctx2: OnTemplateCompiledContext = extension.calls["on_template_compiled"][0]
        assert ctx2.component_cls == TestComponent
        assert isinstance(ctx2.template, Template)

        # on_js_loaded
        assert len(extension.calls["on_js_loaded"]) == 1
        ctx3: OnJsLoadedContext = extension.calls["on_js_loaded"][0]
        assert ctx3.component_cls == TestComponent
        assert ctx3.content == "console.log('hi');"

        # on_css_loaded
        assert len(extension.calls["on_css_loaded"]) == 1
        ctx4: OnCssLoadedContext = extension.calls["on_css_loaded"][0]
        assert ctx4.component_cls == TestComponent
        assert ctx4.content == "body { color: red; }"

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_asset_hooks__file(self):
        @register("test_comp_hooks")
        class TestComponent(Component):
            template_file = "relative_file/relative_file.html"
            js_file = "relative_file/relative_file.js"
            css_file = "relative_file/relative_file.css"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

        # Render the component to trigger all hooks
        TestComponent.render(args=(), kwargs={"name": "Test"})

        extension = cast("DummyExtension", app_settings.EXTENSIONS[5])

        # on_template_loaded
        # NOTE: The template file gets picked up by 'django.template.loaders.filesystem.Loader',
        #       as well as our own loader, so we get two calls here.
        assert len(extension.calls["on_template_loaded"]) == 2
        ctx1: OnTemplateLoadedContext = extension.calls["on_template_loaded"][0]
        assert ctx1.component_cls == TestComponent
        assert ctx1.content == (
            '<form method="post">\n'
            "  {% csrf_token %}\n"
            '  <input type="text" name="variable" value="{{ variable }}">\n'
            '  <input type="submit">\n'
            "</form>\n"
        )
        assert isinstance(ctx1.origin, Origin)
        assert ctx1.origin.name.endswith("relative_file.html")
        assert ctx1.name == "relative_file/relative_file.html"

        # on_template_compiled
        assert len(extension.calls["on_template_compiled"]) == 2
        ctx2: OnTemplateCompiledContext = extension.calls["on_template_compiled"][0]
        assert ctx2.component_cls == TestComponent
        assert isinstance(ctx2.template, Template)

        # on_js_loaded
        assert len(extension.calls["on_js_loaded"]) == 1
        ctx3: OnJsLoadedContext = extension.calls["on_js_loaded"][0]
        assert ctx3.component_cls == TestComponent
        assert ctx3.content == 'console.log("JS file");\n'

        # on_css_loaded
        assert len(extension.calls["on_css_loaded"]) == 1
        ctx4: OnCssLoadedContext = extension.calls["on_css_loaded"][0]
        assert ctx4.component_cls == TestComponent
        assert ctx4.content == ".html-css-only {\n  color: blue;\n}\n"

    @djc_test(components_settings={"extensions": [OverrideAssetExtension]})
    def test_asset_hooks_override(self):
        @register("test_comp_override")
        class TestComponent(Component):
            template = "Hello {{ name }}!"
            js = "console.log('hi');"
            css = "body { color: red; }"

            def get_template_data(self, args, kwargs, slots, context):
                return {"name": kwargs.get("name", "World")}

        # No need to render, accessing the attributes should trigger the hooks
        assert TestComponent.template == "OVERRIDDEN TEMPLATE"
        assert TestComponent.js == "OVERRIDDEN JS"
        assert TestComponent.css == "OVERRIDDEN CSS"


@djc_test
class TestExtensionViews:
    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_views(self):
        client = Client()

        # Check basic view
        response = client.get("/components/ext/test_extension/dummy-view/")
        assert response.status_code == 200
        assert response.content == b"Hello, world!"

        # Check that URL parameters are passed to the view
        response2 = client.get("/components/ext/test_extension/dummy-view-2/123/John/")
        assert response2.status_code == 200
        assert response2.content == b"Hello, world! 123 John"

    @djc_test(components_settings={"extensions": [DummyNestedExtension]})
    def test_nested_views(self):
        client = Client()

        # Check basic view
        # NOTE: Since the parent route contains child routes, the parent route should not be matched
        response = client.get("/components/ext/test_nested_extension/nested-view/")
        assert response.status_code == 404

        # Check that URL parameters are passed to the view
        response2 = client.get("/components/ext/test_nested_extension/nested-view/123/John/")
        assert response2.status_code == 200
        assert response2.content == b"Hello, world! 123 John"


@djc_test
class TestExtensionDefaults:
    @djc_test(
        components_settings={
            "extensions": [DummyExtension],
            "extensions_defaults": {
                "test_extension": {},
            },
        },
    )
    def test_no_defaults(self):
        class TestComponent(Component):
            template = "Hello"

        dummy_ext_cls: DummyExtension.ComponentConfig = TestComponent.TestExtension  # type: ignore[attr-defined]
        assert dummy_ext_cls.foo == "1"
        assert dummy_ext_cls.bar == "2"
        assert dummy_ext_cls.baz() == "3"

    @djc_test(
        components_settings={
            "extensions": [DummyExtension],
            "extensions_defaults": {
                "test_extension": {
                    "foo": "NEW_FOO",
                    "baz": classmethod(lambda _self: "OVERRIDEN"),
                },
                "nonexistent": {
                    "1": "2",
                },
            },
        },
    )
    def test_defaults(self):
        class TestComponent(Component):
            template = "Hello"

        dummy_ext_cls: DummyExtension.ComponentConfig = TestComponent.TestExtension  # type: ignore[attr-defined]
        assert dummy_ext_cls.foo == "NEW_FOO"
        assert dummy_ext_cls.bar == "2"
        assert dummy_ext_cls.baz() == "OVERRIDEN"


@djc_test
class TestLegacyApi:
    # TODO_V1 - Remove
    @djc_test(
        components_settings={
            "extensions": [LegacyExtension],
        },
    )
    def test_extension_class(self):
        class TestComponent(Component):
            template = "Hello"

        dummy_ext_cls: LegacyExtension.ExtensionClass = TestComponent.Legacy  # type: ignore[attr-defined]
        assert dummy_ext_cls.foo == "1"
        assert dummy_ext_cls.bar == "2"
        assert dummy_ext_cls.baz() == "3"
