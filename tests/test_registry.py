import pytest
from django.template import Context, Engine, Library, Template

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
from pytest_django.asserts import assertHTMLEqual

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


class MockComponent(Component):
    pass


class MockComponent2(Component):
    pass


class MockComponentView(Component):
    def get(self, request, *args, **kwargs):
        pass


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
