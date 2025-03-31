import gc
from typing import Any, Callable, Dict, List, cast

from django.http import HttpRequest, HttpResponse
from django.template import Context
from django.test import Client

from django_components import Component, Slot, register, registry
from django_components.app_settings import app_settings
from django_components.component_registry import ComponentRegistry
from django_components.extension import (
    URLRoute,
    ComponentExtension,
    OnComponentClassCreatedContext,
    OnComponentClassDeletedContext,
    OnRegistryCreatedContext,
    OnRegistryDeletedContext,
    OnComponentRegisteredContext,
    OnComponentUnregisteredContext,
    OnComponentInputContext,
    OnComponentDataContext,
)
from django_components.extensions.cache import CacheExtension
from django_components.extensions.defaults import DefaultsExtension
from django_components.extensions.view import ViewExtension
from django_components.extensions.url import UrlExtension

from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


def dummy_view(request: HttpRequest):
    # Test that the request object is passed to the view
    assert isinstance(request, HttpRequest)
    return HttpResponse("Hello, world!")


def dummy_view_2(request: HttpRequest, id: int, name: str):
    return HttpResponse(f"Hello, world! {id} {name}")


class DummyExtension(ComponentExtension):
    """
    Test extension that tracks all hook calls and their arguments.
    """

    name = "test_extension"

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


def with_component_cls(on_created: Callable):
    class TempComponent(Component):
        template = "Hello {{ name }}!"

        def get_context_data(self, name="World"):
            return {"name": name}

    on_created()


def with_registry(on_created: Callable):
    registry = ComponentRegistry()

    on_created(registry)


@djc_test
class TestExtension:
    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_extensions_setting(self):
        assert len(app_settings.EXTENSIONS) == 5
        assert isinstance(app_settings.EXTENSIONS[0], CacheExtension)
        assert isinstance(app_settings.EXTENSIONS[1], DefaultsExtension)
        assert isinstance(app_settings.EXTENSIONS[2], ViewExtension)
        assert isinstance(app_settings.EXTENSIONS[3], UrlExtension)
        assert isinstance(app_settings.EXTENSIONS[4], DummyExtension)

    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_access_component_from_extension(self):
        class TestAccessComp(Component):
            template = "Hello {{ name }}!"

            def get_context_data(self, arg1, arg2, name="World"):
                return {"name": name}

        ext_class = TestAccessComp.TestExtension  # type: ignore[attr-defined]
        assert issubclass(ext_class, ComponentExtension.ExtensionClass)
        assert ext_class.component_class is TestAccessComp

        # NOTE: Required for test_component_class_lifecycle_hooks to work
        del TestAccessComp
        gc.collect()


@djc_test
class TestExtensionHooks:
    @djc_test(components_settings={"extensions": [DummyExtension]})
    def test_component_class_lifecycle_hooks(self):
        extension = cast(DummyExtension, app_settings.EXTENSIONS[4])

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
        extension = cast(DummyExtension, app_settings.EXTENSIONS[4])

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

            def get_context_data(self, name="World"):
                return {"name": name}

        registry.register("test_comp", TestComponent)
        extension = cast(DummyExtension, app_settings.EXTENSIONS[4])

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

            def get_context_data(self, arg1, arg2, name="World"):
                return {"name": name}

            def get_js_data(self, *args, **kwargs):
                return {"script": "console.log('Hello!')"}

            def get_css_data(self, *args, **kwargs):
                return {"style": "body { color: blue; }"}

        # Render the component with some args and kwargs
        test_context = Context({"foo": "bar"})
        test_slots = {"content": "Some content"}
        TestComponent.render(context=test_context, args=("arg1", "arg2"), kwargs={"name": "Test"}, slots=test_slots)

        extension = cast(DummyExtension, app_settings.EXTENSIONS[4])

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
        assert data_call.context_data == {"name": "Test"}
        assert data_call.js_data == {"script": "console.log('Hello!')"}
        assert data_call.css_data == {"style": "body { color: blue; }"}


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
