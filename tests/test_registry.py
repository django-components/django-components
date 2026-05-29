import gc

import pytest
from django.template import Context, Engine, Library, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import (
    AlreadyRegistered,
    Component,
    ComponentRegistry,
    ContextBehavior,
    NotRegistered,
    RegistrySettings,
    TagProtectedError,
    all_registries,
    component_formatter,
    component_shorthand_formatter,
    register,
    registry,
    types,
)
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


class MockComponent(Component):
    pass


class MockComponent2(Component):
    pass


class MockComponentView(Component):
    def get(self, request, *args, **kwargs):
        pass


def gen_reimported_component():
    return type(
        "ReimportedComponent",
        (Component,),
        {
            "__module__": "tests.components.reimported_component",
        },
    )


@djc_test
class TestComponentRegistry:
    def test_register_class_decorator(self):
        assert not registry.has("decorated_component")

        @register("decorated_component")
        class TestComponent(Component):
            pass

        assert registry.has("decorated_component")
        assert registry.get("decorated_component") == TestComponent

        # Cleanup
        registry.unregister("decorated_component")
        assert not registry.has("decorated_component")

    def test_register_class_decorator_custom_registry(self):
        my_lib = Library()
        my_reg = ComponentRegistry(library=my_lib)

        default_registry_comps_before = len(registry.all())

        assert my_reg.all() == {}

        @register("decorated_component", registry=my_reg)
        class TestComponent(Component):
            pass

        assert my_reg.all() == {"decorated_component": TestComponent}

        # Check that the component was NOT added to the default registry
        default_registry_comps_after = len(registry.all())
        assert default_registry_comps_before == default_registry_comps_after

    def test_simple_register(self):
        custom_registry = ComponentRegistry()
        custom_registry.register(name="testcomponent", component=MockComponent)
        assert custom_registry.all() == {"testcomponent": MockComponent}

    def test_register_two_components(self):
        custom_registry = ComponentRegistry()
        custom_registry.register(name="testcomponent", component=MockComponent)
        custom_registry.register(name="testcomponent2", component=MockComponent)
        assert custom_registry.all() == {
            "testcomponent": MockComponent,
            "testcomponent2": MockComponent,
        }

    def test_unregisters_only_unused_tags(self):
        custom_library = Library()
        custom_registry = ComponentRegistry(library=custom_library)
        assert custom_registry._tags == {}

        # NOTE: We preserve the default component tags
        assert "component" not in custom_registry.library.tags

        # Register two components that use the same tag
        custom_registry.register(name="testcomponent", component=MockComponent)
        custom_registry.register(name="testcomponent2", component=MockComponent)

        assert custom_registry._tags == {
            "component": {"testcomponent", "testcomponent2"},
        }

        assert "component" in custom_registry.library.tags

        # Unregister only one of the components. The tags should remain
        custom_registry.unregister(name="testcomponent")

        assert custom_registry._tags == {
            "component": {"testcomponent2"},
        }

        assert "component" in custom_registry.library.tags

        # Unregister the second components. The tags should be removed
        custom_registry.unregister(name="testcomponent2")

        assert custom_registry._tags == {}
        assert "component" not in custom_registry.library.tags

    def test_prevent_registering_different_components_with_the_same_name(self):
        custom_registry = ComponentRegistry()
        custom_registry.register(name="testcomponent", component=MockComponent)
        with pytest.raises(AlreadyRegistered):
            custom_registry.register(name="testcomponent", component=MockComponent2)

    def test_allow_duplicated_registration_of_the_same_component(self):
        custom_registry = ComponentRegistry()
        try:
            custom_registry.register(name="testcomponent", component=MockComponentView)
            custom_registry.register(name="testcomponent", component=MockComponentView)
        except AlreadyRegistered:
            pytest.fail("Should not raise AlreadyRegistered")

    def test_register_different_class_with_same_class_id_raises(self):
        # Two distinct class objects with identical `class_id` is the exact #1598
        # scenario. Replacement must require an explicit unregister.
        custom_registry = ComponentRegistry()

        component_v1 = gen_reimported_component()
        component_v2 = gen_reimported_component()
        assert component_v1 is not component_v2
        assert component_v1.class_id == component_v2.class_id

        custom_registry.register(name="testcomponent", component=component_v1)
        with pytest.raises(AlreadyRegistered):
            custom_registry.register(name="testcomponent", component=component_v2)

        # Original entry is untouched.
        assert custom_registry.get("testcomponent") is component_v1

    def test_unregister_then_reregister_with_replacement_class_succeeds(self):
        custom_registry = ComponentRegistry()

        component_v1 = gen_reimported_component()
        custom_registry.register(name="testcomponent", component=component_v1)

        custom_registry.unregister(name="testcomponent")

        component_v2 = gen_reimported_component()
        custom_registry.register(name="testcomponent", component=component_v2)
        assert custom_registry.get("testcomponent") is component_v2

        # Exactly one finalizer is tracked for the live entry.
        assert len(custom_registry._finalizers) == 1

        # Garbage-collecting the prior class object must NOT touch the live entry,
        # since `unregister()` detached its finalizer.
        del component_v1
        gc.collect()
        assert custom_registry.get("testcomponent") is component_v2

    def test_unregister_detaches_finalizer(self):
        custom_registry = ComponentRegistry()
        custom_registry.register(name="testcomponent", component=MockComponent)
        assert "testcomponent" in custom_registry._finalizers

        custom_registry.unregister(name="testcomponent")
        assert "testcomponent" not in custom_registry._finalizers

    def test_node_subcls_cache_is_per_registry(self):
        # Each registry owns its own `_node_subcls_cache`. Replaces the previous
        # module-global `component_node_subclasses_by_name` that pinned both the
        # subclass and the registry forever.
        library_a = Library()
        library_b = Library()
        registry_a = ComponentRegistry(library=library_a)
        registry_b = ComponentRegistry(library=library_b)

        assert registry_a._node_subcls_cache == {}
        assert registry_b._node_subcls_cache == {}
        assert registry_a._node_subcls_cache is not registry_b._node_subcls_cache

    def test_module_global_node_subcls_cache_no_longer_exists(self):
        # Pre-fix, `django_components.component` exposed a module-global
        # `component_node_subclasses_by_name` that pinned subclasses + registries
        # forever. The cache now lives per-registry. Catch any accidental
        # reintroduction of the global.
        import django_components.component as component_module

        assert not hasattr(component_module, "component_node_subclasses_by_name")

    def test_node_subcls_cache_populated_on_parse(self):
        library = Library()
        registry_local = ComponentRegistry(library=library)
        registry_local.register("simple", MockComponent)

        engine = Engine.get_default()
        engine.template_builtins.append(library)
        try:
            assert registry_local._node_subcls_cache == {}
            Template("{% component 'simple' / %}")
            # `_register_to_library` uses `formatter.start_tag(comp_name)`, which
            # for the default formatter returns "component" regardless of comp_name.
            assert list(registry_local._node_subcls_cache.keys()) == ["component"]
        finally:
            engine.template_builtins.remove(library)

    def test_simple_unregister(self):
        custom_registry = ComponentRegistry()
        custom_registry.register(name="testcomponent", component=MockComponent)
        custom_registry.unregister(name="testcomponent")
        assert custom_registry.all() == {}

    def test_raises_on_failed_unregister(self):
        custom_registry = ComponentRegistry()
        with pytest.raises(NotRegistered):
            custom_registry.unregister(name="testcomponent")


@djc_test
class TestMultipleComponentRegistries:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_different_registries_have_different_settings(self, components_settings):
        library_a = Library()
        registry_a = ComponentRegistry(
            library=library_a,
            settings=RegistrySettings(
                context_behavior=ContextBehavior.ISOLATED.value,
                tag_formatter=component_shorthand_formatter,
            ),
        )

        library_b = Library()
        registry_b = ComponentRegistry(
            library=library_b,
            settings=RegistrySettings(
                context_behavior=ContextBehavior.DJANGO.value,
                tag_formatter=component_formatter,
            ),
        )

        # NOTE: We cannot load the Libraries above using `{% load xxx %}` tag, because
        # for that we'd need to register a Django app and whatnot.
        # Instead, we insert the Libraries directly into the engine's builtins.
        engine = Engine.get_default()

        # Add the custom template tags to Django's built-in tags
        engine.template_builtins.append(library_a)
        engine.template_builtins.append(library_b)

        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot: {% slot "default" default / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs.get("variable", None),
                }

        registry_a.register("simple_a", SimpleComponent)
        registry_b.register("simple_b", SimpleComponent)

        template_str: types.django_html = """
            {% simple_a variable=123 %}
                SLOT 123
            {% endsimple_a %}
            {% component "simple_b" variable=123 %}
                SLOT ABC
            {% endcomponent %}
        """
        template = Template(template_str)

        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc40>123</strong>
            Slot:
            SLOT 123

            Variable: <strong data-djc-id-ca1bc42>123</strong>
            Slot:
            SLOT ABC
            """,
        )

        # Remove the custom template tags to clean up after tests
        engine.template_builtins.remove(library_a)
        engine.template_builtins.remove(library_b)


@djc_test
class TestProtectedTags:
    # NOTE: Use the `component_shorthand_formatter` formatter, so the components
    # are registered under that tag
    @djc_test(
        components_settings={
            "tag_formatter": "django_components.component_shorthand_formatter",
        },
    )
    def test_raises_on_overriding_our_tags(self):
        for tag in [
            "component_css_dependencies",
            "component_js_dependencies",
            "fill",
            "html_attrs",
            "provide",
            "slot",
        ]:
            with pytest.raises(TagProtectedError):

                @register(tag)
                class TestComponent(Component):
                    pass

        @register("sth_else")
        class TestComponent2(Component):
            pass

        # Cleanup
        registry.unregister("sth_else")


@djc_test
class TestRegistryHelpers:
    def test_all_registries(self):
        # Default registry
        assert len(all_registries()) == 1

        reg = ComponentRegistry()

        assert len(all_registries()) == 2

        del reg

        assert len(all_registries()) == 1
