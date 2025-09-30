import re

import pytest
from django.template import Context, Template, TemplateSyntaxError
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, NotRegistered, register, registry, types
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


def gen_slotted_component():
    class SlottedComponent(Component):
        template_file = "slotted_template.html"

    return SlottedComponent


def gen_slotted_component_with_context():
    class SlottedComponentWithContext(Component):
        template: types.django_html = """
            {% load component_tags %}
            <custom-template>
                <header>{% slot "header" %}Default header{% endslot %}</header>
                <main>{% slot "main" %}Default main{% endslot %}</main>
                <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
            </custom-template>
        """

        def get_template_data(self, args, kwargs, slots, context):
            return {"variable": kwargs["variable"]}

    return SlottedComponentWithContext


#######################
# TESTS
#######################


@djc_test
class TestComponentTemplateTag:
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "variable": kwargs["variable"],
                "variable2": kwargs.get("variable2", "default"),
            }

        class Media:
            css = "style.css"
            js = "script.js"

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_single_component(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" %}{% endcomponent %}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f>variable</strong>\n")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_single_component_self_closing(self, components_settings):
        registry.register(name="test", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" /%}
        """

        template = Template(simple_tag_template)
        rendered = template.render(Context({}))
        assertHTMLEqual(rendered, "Variable: <strong data-djc-id-ca1bc3f>variable</strong>\n")

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_call_with_invalid_name(self, components_settings):
        registry.register(name="test_one", component=self.SimpleComponent)

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" %}{% endcomponent %}
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

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs["variable"],
                    "variable2": kwargs.get("variable2", "default"),
                }

            class Media:
                css = "style.css"
                js = "script.js"

        simple_tag_template: types.django_html = """
            {% load component_tags %}
            {% component "test" variable="variable" variable2="hej" %}{% endcomponent %}
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

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "variable": kwargs["variable"],
                    "default_param": kwargs.get("default_param", "default text"),
                }

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
class TestMultiComponent:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_both_components_render_correctly_with_no_slots(self, components_settings):
        registry.register("first_component", gen_slotted_component())
        registry.register("second_component", gen_slotted_component_with_context())

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
        registry.register("first_component", gen_slotted_component())
        registry.register("second_component", gen_slotted_component_with_context())

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
        registry.register("first_component", gen_slotted_component())
        registry.register("second_component", gen_slotted_component_with_context())

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
        registry.register("first_component", gen_slotted_component())
        registry.register("second_component", gen_slotted_component_with_context())

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
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_instances_of_component_do_not_share_slots(self, components_settings):
        @register("test")
        class SlottedComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <custom-template>
                    <header>{% slot "header" %}Default header{% endslot %}</header>
                    <main>{% slot "main" %}Default main{% endslot %}</main>
                    <footer>{% slot "footer" %}Default footer{% endslot %}</footer>
                </custom-template>
            """

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

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "attrs": kwargs["attrs"],
                    "my_dict": kwargs["my_dict"],
                }

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
            class Defaults:
                depth = 0

            def get_template_data(self, args, kwargs, slots, context):
                return {"depth": kwargs["depth"] + 1, "DEPTH": DEPTH}

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
        registry.register("test", gen_slotted_component())
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
        registry.register("test", gen_slotted_component())
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
        registry.register("test", gen_slotted_component())
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
            match=re.escape(
                "Illegal content passed to component 'test'. Explicit 'fill' tags cannot occur alongside other text",
            ),
        ):
            template.render(Context())

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_unclosed_component_is_error(self, components_settings):
        registry.register("test", gen_slotted_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
            {% fill "header" %}{% endfill %}
        """
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Unclosed tag on line 3: 'component'"),
        ):
            Template(template_str)
