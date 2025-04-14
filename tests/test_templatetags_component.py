import re

import pytest
from django.template import Context, Template, TemplateSyntaxError
from pytest_django.asserts import assertHTMLEqual
from django_components import AlreadyRegistered, Component, NotRegistered, register, registry, types

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_file = "slotted_template.html"


class SlottedComponentWithContext(Component):
    template: types.django_html = """
        {% load component_tags %}
        <custom-template>
            <header>{% slot "header" %}Default header{% endslot %}</header>
            <main>{% slot "main" %}Default main{% endslot %}</main>
            <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
        </custom-template>
    """

    def get_context_data(self, variable):
        return {"variable": variable}


#######################
# TESTS
#######################


@djc_test
class TestComponentTemplateTag:
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_context_data(self, variable, variable2="default"):
            return {
                "variable": variable,
                "variable2": variable2,
            }

        class Media:
            css = "style.css"
            js = "script.js"

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_single_component(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f>variable</strong>\n")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_single_component_self_closing(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" /%}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f>variable</strong>\n")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_call_with_invalid_name(self, components_settings):
        registry.register(name="test_one", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        with pytest.raises(NotRegistered):
            template.render(Context({}))

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_positional_name(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f>variable</strong>\n")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_call_component_with_two_variables(self, components_settings):
        @register("test")
        class IffedComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
                {% if variable2 != "default" %}
                    Variable2: <strong>{{ variable2 }}</strong>
                {% endif %}
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

            class Media:
                css = "style.css"
                js = "script.js"

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component name="test" variable="variable" variable2="hej" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            Variable: <strong data-djc-id-ca1bc3f>variable</strong>
            Variable2: <strong data-djc-id-ca1bc3f>hej</strong>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_singlequoted_name(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component 'test' variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f>variable</strong>\n")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_raises_on_component_called_with_variable_as_name(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% with component_name="test" %}
                {% component component_name variable="variable" %}{% endcomponent %}
            {% endwith %}
        """

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Component name must be a string 'literal', got: component_name"),
        ):
            Template(simple_tag_template)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_accepts_provided_and_default_parameters(self, components_settings):
        @register("test")
        class ComponentWithProvidedAndDefaultParameters(Component):
            template: types.django_html = """
                Provided variable: <strong>{{ variable }}</strong>
                Default: <p>{{ default_param }}</p>
            """

            def get_context_data(self, variable, default_param="default text"):
                return {"variable": variable, "default_param": default_param}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="provided value" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            Provided variable: <strong data-djc-id-ca1bc3f>provided value</strong>
            Default: <p data-djc-id-ca1bc3f>default text</p>
            """,
        )


@djc_test
class TestDynamicComponentTemplateTag:
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_context_data(self, variable, variable2="default"):
            return {
                "variable": variable,
                "variable2": variable2,
            }

        class Media:
            css = "style.css"
            js = "script.js"

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_basic(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

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
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is="haber_der_baber" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        with pytest.raises(NotRegistered, match=re.escape("The component 'haber_der_baber' was not found")):
            template.render(Context({}))

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_variable_as_name(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

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
        registry.register(name="test", component=self.SimpleComponent)

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
                }
            )
        )
        assertHTMLEqual(
            rendered,
            "Variable: <strong data-djc-id-ca1bc3f data-djc-id-ca1bc40>variable</strong>",
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_as_class(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "dynamic" is=comp_cls variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(
            Context(
                {
                    "comp_cls": self.SimpleComponent,
                }
            )
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

        registry.register(name="test", component=self.SimpleComponent)

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

        registry.register(name="test", component=self.SimpleComponent)

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
            registry.register(name="dynamic", component=self.SimpleComponent)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_called_with_default_slot(self, components_settings):
        class SimpleSlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                Variable: <strong>{{ variable }}</strong>
                Slot: {% slot "default" default / %}
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
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

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
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

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
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
    def test_raises_on_invalid_args(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

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


@djc_test
class TestMultiComponent:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_both_components_render_correctly_with_no_slots(self, components_settings):
        registry.register("first_component", SlottedComponent)
        registry.register("second_component", SlottedComponentWithContext)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'first_component' %}
            {% endcomponent %}
            {% component 'second_component' variable='xyz' %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc40>
                <header>
                    Default header
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template data-djc-id-ca1bc47>
                <header>
                    Default header
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_both_components_render_correctly_with_slots(self, components_settings):
        registry.register("first_component", SlottedComponent)
        registry.register("second_component", SlottedComponentWithContext)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'first_component' %}
                {% fill "header" %}<p>Slot #1</p>{% endfill %}
            {% endcomponent %}
            {% component 'second_component' variable='xyz' %}
                {% fill "header" %}<div>Slot #2</div>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc42>
                <header>
                    <p>Slot #1</p>
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template data-djc-id-ca1bc49>
                <header>
                    <div>Slot #2</div>
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_both_components_render_correctly_when_only_first_has_slots(self, components_settings):
        registry.register("first_component", SlottedComponent)
        registry.register("second_component", SlottedComponentWithContext)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'first_component' %}
                {% fill "header" %}<p>Slot #1</p>{% endfill %}
            {% endcomponent %}
            {% component 'second_component' variable='xyz' %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc41>
                <header>
                    <p>Slot #1</p>
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template data-djc-id-ca1bc48>
                <header>
                    Default header
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_both_components_render_correctly_when_only_second_has_slots(self, components_settings):
        registry.register("first_component", SlottedComponent)
        registry.register("second_component", SlottedComponentWithContext)

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'first_component' %}
            {% endcomponent %}
            {% component 'second_component' variable='xyz' %}
                {% fill "header" %}<div>Slot #2</div>{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc41>
                <header>
                    Default header
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template data-djc-id-ca1bc48>
                <header>
                    <div>Slot #2</div>
                </header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            """,
        )


@djc_test
class TestComponentIsolation:
    class SlottedComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <custom-template>
                <header>{% slot "header" %}Default header{% endslot %}</header>
                <main>{% slot "main" %}Default main{% endslot %}</main>
                <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
            </custom-template>
        """

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_instances_of_component_do_not_share_slots(self, components_settings):
        registry.register("test", self.SlottedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% fill "header" %}Override header{% endfill %}
            {% endcomponent %}
            {% component "test" %}
                {% fill "main" %}Override main{% endfill %}
            {% endcomponent %}
            {% component "test" %}
                {% fill "footer" %}Override footer{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        template.render(Context({}))
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <custom-template data-djc-id-ca1bc4a>
                <header>Override header</header>
                <main>Default main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template data-djc-id-ca1bc4b>
                <header>Default header</header>
                <main>Override main</main>
                <footer>Default footer</footer>
            </custom-template>
            <custom-template data-djc-id-ca1bc4c>
                <header>Default header</header>
                <main>Default main</main>
                <footer>Override footer</footer>
            </custom-template>
        """,
        )


@djc_test
class TestAggregateInput:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_agg_input_accessible_in_get_context_data(self, components_settings):
        @register("test")
        class AttrsComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    attrs: {{ attrs|safe }}
                    my_dict: {{ my_dict|safe }}
                </div>
            """

            def get_context_data(self, *args, attrs, my_dict):
                return {"attrs": attrs, "my_dict": my_dict}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" attrs:@click.stop="dispatch('click_event')" attrs:x-data="{hello: 'world'}" attrs:class=class_var my_dict:one=2 %}
            {% endcomponent %}
        """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context({"class_var": "padding-top-8"}))
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3f>
                attrs: {'@click.stop': "dispatch('click_event')", 'x-data': "{hello: 'world'}", 'class': 'padding-top-8'}
                my_dict: {'one': 2}
            </div>
            """,  # noqa: E501
        )


@djc_test
class TestRecursiveComponent:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_recursive_component(self, components_settings):
        DEPTH = 100

        @register("recursive")
        class Recursive(Component):
            def get_context_data(self, depth: int = 0):
                print("depth:", depth)
                return {"depth": depth + 1, "DEPTH": DEPTH}

            template: types.django_html = """
                <div>
                    <span> depth: {{ depth }} </span>
                    {% if depth <= DEPTH %}
                        {% component "recursive" depth=depth / %}
                    {% endif %}
                </div>
            """

        result = Recursive.render()

        for i in range(DEPTH):
            assert f"<span> depth: {i + 1} </span>" in result


@djc_test
class TestComponentTemplateSyntaxError:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_variable_outside_fill_tag_compiles_w_out_error(self, components_settings):
        registry.register("test", SlottedComponent)
        # As of v0.28 this is valid, provided the component registered under "test"
        # contains a slot tag marked as 'default'. This is verified outside
        # template compilation time.
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {{ anything }}
            {% endcomponent %}
        """
        Template(template_str)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_text_outside_fill_tag_is_not_error_when_no_fill_tags(self, components_settings):
        registry.register("test", SlottedComponent)
        # As of v0.28 this is valid, provided the component registered under "test"
        # contains a slot tag marked as 'default'. This is verified outside
        # template compilation time.
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                Text
            {% endcomponent %}
        """
        Template(template_str)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_text_outside_fill_tag_is_error_when_fill_tags(self, components_settings):
        registry.register("test", SlottedComponent)
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
                {% lorem 3 w random %}
                {% fill "header" %}{% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Illegal content passed to component 'test'. Explicit 'fill' tags cannot occur alongside other text"),  # noqa: E501
        ):
            template.render(Context())

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_unclosed_component_is_error(self, components_settings):
        registry.register("test", SlottedComponent)
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Unclosed tag on line 3: 'component'"),
        ):
            template_str: types.django_html = """
                {% load component_tags %}
                {% component "test" %}
                {% fill "header" %}{% endfill %}
            """
            Template(template_str)
