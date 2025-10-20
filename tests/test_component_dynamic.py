import re

import pytest
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import AlreadyRegistered, Component, DynamicComponent, NotRegistered, registry, types
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


@djc_test
class TestDynamicComponent:
    def _gen_simple_component(self):
        class SimpleComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            class Kwargs:
                variable: str
                variable2: str

            class Defaults:
                variable2 = "default"

            def get_template_data(self, args, kwargs: Kwargs, slots, context):
                return {
                    "variable": kwargs.variable,
                    "variable2": kwargs.variable2,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        return SimpleComponent

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_basic__python(self, components_settings):
        registry.register(name="test", component=self._gen_simple_component())

        rendered = DynamicComponent.render(
            kwargs={
                "is": "test",
                "variable": "variable",
            },
        )
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3e data-djc-id-ca1bc3f>variable</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_basic__template(self, components_settings):
        registry.register(name="test", component=self._gen_simple_component())

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_call_with_invalid_name(self, components_settings):
        registry.register(name="test", component=self._gen_simple_component())

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is="haber_der_baber" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        with pytest.raises(NotRegistered, match=re.escape("The component 'haber_der_baber' was not found")):
            template.render(Context({}))

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_variable_as_name(self, components_settings):
        registry.register(name="test", component=self._gen_simple_component())

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_variable_as_spread(self, components_settings):
        registry.register(name="test", component=self._gen_simple_component())

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" ...props %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(
            Context(
                {
                    "props": {
                        "is": "test",
                        "variable": "variable",
                    },
                },
            ),
        )
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_as_class(self, components_settings):
        SimpleComponent = self._gen_simple_component()
        registry.register(name="test", component=SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is=comp_cls variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(
            Context(
                {
                    "comp_cls": SimpleComponent,
                },
            ),
        )
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>",
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": "django_components.component_shorthand_formatter",
            "autodiscover": False,
        },
    )
    def test_shorthand_formatter(self, components_settings):
        from django_components.apps import ComponentsConfig

        ComponentsConfig.ready(None)  # type: ignore[arg-type]

        registry.register(name="test", component=self._gen_simple_component())

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% dynamic is="test" variable="variable" %}{% enddynamic %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>\n")

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "dynamic_component_name": "uno_reverse",
            "tag_formatter": "django_components.component_shorthand_formatter",
            "autodiscover": False,
        },
    )
    def test_component_name_is_configurable(self, components_settings):
        from django_components.apps import ComponentsConfig

        ComponentsConfig.ready(None)  # type: ignore[arg-type]

        registry.register(name="test", component=self._gen_simple_component())

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% uno_reverse is="test" variable="variable" %}{% enduno_reverse %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_already_registered_on_name_conflict(self, components_settings):
        with pytest.raises(
            AlreadyRegistered,
            match=re.escape('The component "dynamic" has already been registered'),
        ):
            registry.register(name="dynamic", component=self._gen_simple_component())

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_default_slot(self, components_settings):
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

        registry.register(name="test", component=SimpleSlottedComponent)

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
    def test_component_called_with_named_slots(self, components_settings):
        class SimpleSlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "default" default / %}
                Slot 2: {% slot "two" / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs["variable"],
                    "variable2": kwargs.get("variable2", "default"),
                }

        registry.register(name="test", component=SimpleSlottedComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}
                    {% fill "default" %}
                        HELLO_FROM_SLOT_1
                    {% endfill %}
                    {% fill "two" %}
                        HELLO_FROM_SLOT_2
                    {% endfill %}
                {% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc41 data-djc-id-ca1bc42>variable</strong>
            Slot 1: HELLO_FROM_SLOT_1
            Slot 2: HELLO_FROM_SLOT_2
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_ignores_invalid_slots(self, components_settings):
        class SimpleSlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot 1: {% slot "default" default / %}
                Slot 2: {% slot "two" / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs["variable"],
                    "variable2": kwargs.get("variable2", "default"),
                }

        registry.register(name="test", component=SimpleSlottedComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name variable="variable" %}
                    {% fill "default" %}
                        HELLO_FROM_SLOT_1
                    {% endfill %}
                    {% fill "three" %}
                        HELLO_FROM_SLOT_2
                    {% endfill %}
                {% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc41 data-djc-id-ca1bc42>variable</strong>
            Slot 1: HELLO_FROM_SLOT_1
            Slot 2:
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_on_invalid_input(self, components_settings):
        registry.register(name="test", component=self._gen_simple_component())

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component "dynamic" is=component_name invalid_variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        template = Template(simple_tag_template)
        with pytest.raises(
            TypeError,
            match=re.escape("got an unexpected keyword argument 'invalid_variable'"),
        ):
            template.render(Context({}))
