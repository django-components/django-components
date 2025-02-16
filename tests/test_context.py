from django.http import HttpRequest
from django.template import Context, RequestContext, Template

from django_components import Component, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


#########################
# COMPONENTS
#########################


class SimpleComponent(Component):
    template: types.django_html = """
        Variable: <strong>{{ variable }}</strong>
    """

    def get_context_data(self, variable=None):
        return {"variable": variable} if variable is not None else {}


class VariableDisplay(Component):
    template: types.django_html = """
        {% load component_tags %}
        <h1>Shadowing variable = {{ shadowing_variable }}</h1>
        <h1>Uniquely named variable = {{ unique_variable }}</h1>
    """

    def get_context_data(self, shadowing_variable=None, new_variable=None):
        context = {}
        if shadowing_variable is not None:
            context["shadowing_variable"] = shadowing_variable
        if new_variable is not None:
            context["unique_variable"] = new_variable
        return context


class IncrementerComponent(Component):
    template: types.django_html = """
        {% load component_tags %}
        <p class="incrementer">value={{ value }};calls={{ calls }}</p>
        {% slot 'content' %}{% endslot %}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_count = 0

    def get_context_data(self, value=0):
        value = int(value)
        if hasattr(self, "call_count"):
            self.call_count += 1
        else:
            self.call_count = 1
        return {"value": value + 1, "calls": self.call_count}


class SimpleComponentWithContextProcessorVariable(Component):
    template: types.django_html = """{% csrf_token %}"""


#########################
# TESTS
#########################


class ContextTests(BaseTestCase):
    class ParentComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component name="variable_display" shadowing_variable='override' new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component name="variable_display" shadowing_variable='slot_default_override' new_variable='slot_default_unique' %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_context_data(self):
            return {"shadowing_variable": "NOT SHADOWED"}

    def setUp(self):
        super().setUp()
        registry.register(name="variable_display", component=VariableDisplay)
        registry.register(name="parent_component", component=self.ParentComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_parent_with_unfilled_slots_and_component_tag(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertInHTML("<h1 data-djc-id-a1bc43>Shadowing variable = override</h1>", rendered)
        self.assertInHTML("<h1 data-djc-id-a1bc44>Shadowing variable = slot_default_override</h1>", rendered)
        self.assertNotIn("Shadowing variable = NOT SHADOWED", rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_instances_have_unique_context_with_unfilled_slots_and_component_tag(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component name='parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertInHTML("<h1 data-djc-id-a1bc43>Uniquely named variable = unique_val</h1>", rendered)
        self.assertInHTML(
            "<h1 data-djc-id-a1bc44>Uniquely named variable = slot_default_unique</h1>",
            rendered,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_parent_with_filled_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertInHTML("<h1 data-djc-id-a1bc45>Shadowing variable = override</h1>", rendered)
        self.assertInHTML("<h1 data-djc-id-a1bc46>Shadowing variable = shadow_from_slot</h1>", rendered)
        self.assertNotIn("Shadowing variable = NOT SHADOWED", rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_instances_have_unique_context_with_filled_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertInHTML("<h1 data-djc-id-a1bc45>Uniquely named variable = unique_val</h1>", rendered)
        self.assertInHTML("<h1 data-djc-id-a1bc46>Uniquely named variable = unique_from_slot</h1>", rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_outer_context_with_unfilled_slots_and_component_tag(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component name='parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"shadowing_variable": "NOT SHADOWED"}))

        self.assertInHTML("<h1 data-djc-id-a1bc43>Shadowing variable = override</h1>", rendered)
        self.assertInHTML("<h1 data-djc-id-a1bc44>Shadowing variable = slot_default_override</h1>", rendered)
        self.assertNotIn("Shadowing variable = NOT SHADOWED", rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_context_shadows_outer_context_with_filled_slots(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context({"shadowing_variable": "NOT SHADOWED"}))

        self.assertInHTML("<h1 data-djc-id-a1bc45>Shadowing variable = override</h1>", rendered)
        self.assertInHTML("<h1 data-djc-id-a1bc46>Shadowing variable = shadow_from_slot</h1>", rendered)
        self.assertNotIn("Shadowing variable = NOT SHADOWED", rendered)


class ParentArgsTests(BaseTestCase):
    class ParentComponentWithArgs(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component name="variable_display" shadowing_variable=inner_parent_value new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component name="variable_display" shadowing_variable='slot_default_override' new_variable=inner_parent_value %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_context_data(self, parent_value):
            return {"inner_parent_value": parent_value}

    def setUp(self):
        super().setUp()
        registry.register(name="incrementer", component=IncrementerComponent)
        registry.register(name="parent_with_args", component=self.ParentComponentWithArgs)
        registry.register(name="variable_display", component=VariableDisplay)

    @parametrize_context_behavior(["django", "isolated"])
    def test_parent_args_can_be_drawn_from_context(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_with_args' parent_value=parent_value %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"parent_value": "passed_in"}))

        self.assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc3f>
                <h1>Parent content</h1>
                <h1 data-djc-id-a1bc43>Shadowing variable = passed_in</h1>
                <h1 data-djc-id-a1bc43>Uniquely named variable = unique_val</h1>
            </div>
            <div data-djc-id-a1bc3f>
                <h2>Slot content</h2>
                <h1 data-djc-id-a1bc44>Shadowing variable = slot_default_override</h1>
                <h1 data-djc-id-a1bc44>Uniquely named variable = passed_in</h1>
            </div>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_parent_args_available_outside_slots(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_with_args' parent_value='passed_in' %}{%endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertInHTML("<h1 data-djc-id-a1bc43>Shadowing variable = passed_in</h1>", rendered)
        self.assertInHTML("<h1 data-djc-id-a1bc44>Uniquely named variable = passed_in</h1>", rendered)
        self.assertNotIn("Shadowing variable = NOT SHADOWED", rendered)

    # NOTE: Second arg in tuple are expected values passed through components.
    @parametrize_context_behavior(
        [
            ("django", ("passed_in", "passed_in")),
            ("isolated", ("passed_in", "")),
        ]
    )
    def test_parent_args_available_in_slots(self, context_behavior_data):
        first_val, second_val = context_behavior_data

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_with_args' parent_value='passed_in' %}
                {% fill 'content' %}
                    {% component name='variable_display' shadowing_variable='value_from_slot' new_variable=inner_parent_value %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
            """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context())

        self.assertHTMLEqual(
            rendered,
            f"""
            <div data-djc-id-a1bc41>
                <h1>Parent content</h1>
                <h1 data-djc-id-a1bc45>Shadowing variable = {first_val}</h1>
                <h1 data-djc-id-a1bc45>Uniquely named variable = unique_val</h1>
            </div>
            <div data-djc-id-a1bc41>
                <h1 data-djc-id-a1bc46>Shadowing variable = value_from_slot</h1>
                <h1 data-djc-id-a1bc46>Uniquely named variable = {second_val}</h1>
            </div>
            """,
        )


class ContextCalledOnceTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        registry.register(name="incrementer", component=IncrementerComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_simple_component(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component name='incrementer' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip().replace("\n", "")
        self.assertHTMLEqual(
            rendered,
            '<p class="incrementer" data-djc-id-a1bc3f>value=1;calls=1</p>',
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_simple_component_and_arg(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component name='incrementer' value='2' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(
            rendered,
            """
            <p class="incrementer" data-djc-id-a1bc3f>value=3;calls=1</p>
            """,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_component(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(rendered, '<p class="incrementer" data-djc-id-a1bc3f>value=1;calls=1</p>')

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_component_and_arg(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' value='3' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(rendered, '<p class="incrementer" data-djc-id-a1bc3f>value=4;calls=1</p>')

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_slot(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' %}
                {% fill 'content' %}
                    <p>slot</p>
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(
            rendered,
            """
            <p class="incrementer" data-djc-id-a1bc40>value=1;calls=1</p>
            <p data-djc-id-a1bc40>slot</p>
            """,
            rendered,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_one_context_call_with_slot_and_arg(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' value='3' %}
                {% fill 'content' %}
                    <p>slot</p>
                {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        self.assertHTMLEqual(
            rendered,
            """
            <p class="incrementer" data-djc-id-a1bc40>value=4;calls=1</p>
            <p data-djc-id-a1bc40>slot</p>
            """,
            rendered,
        )


class ComponentsCanAccessOuterContext(BaseTestCase):
    def setUp(self):
        super().setUp()
        registry.register(name="simple_component", component=SimpleComponent)

    # NOTE: Second arg in tuple is expected value.
    @parametrize_context_behavior(
        [
            ("django", "outer_value"),
            ("isolated", ""),
        ]
    )
    def test_simple_component_can_use_outer_context(self, context_behavior_data):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertHTMLEqual(
            rendered,
            f"""
            Variable: <strong data-djc-id-a1bc3f> {context_behavior_data} </strong>
            """,
        )


class IsolatedContextTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        registry.register(name="simple_component", component=SimpleComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_simple_component_can_pass_outer_context_in_args(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' variable only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        self.assertIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["django", "isolated"])
    def test_simple_component_cannot_use_outer_context(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        self.assertNotIn("outer_value", rendered, rendered)


class IsolatedContextSettingTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        registry.register(name="simple_component", component=SimpleComponent)
        registry.register(
            name="simple_component_with_context_processor_variable",
            component=SimpleComponentWithContextProcessorVariable,
        )

    @parametrize_context_behavior(["isolated"])
    def test_component_tag_includes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' variable %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_component_tag_excludes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertNotIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_component_includes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' variable %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_component_excludes_variable_with_isolated_context_from_settings(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        self.assertNotIn("outer_value", rendered, rendered)

    @parametrize_context_behavior(["isolated"])
    def test_component_can_use_context_processors_variables(
        self,
    ):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component_with_context_processor_variable' %}
            {% endcomponent %}
        """
        request = HttpRequest()
        request_context = RequestContext(request)

        template = Template(template_str)
        rendered = template.render(request_context)
        self.assertIn("csrfmiddlewaretoken", rendered, rendered)


class OuterContextPropertyTests(BaseTestCase):
    class OuterContextComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_context_data(self):
            return self.outer_context.flatten()  # type: ignore[union-attr]

    def setUp(self):
        super().setUp()
        registry.register(name="outer_context_component", component=self.OuterContextComponent)

    @parametrize_context_behavior(["django", "isolated"])
    def test_outer_context_property_with_component(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'outer_context_component' only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        self.assertIn("outer_value", rendered, rendered)


class ContextVarsIsFilledTests(BaseTestCase):
    class IsFilledVarsComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div class="frontmatter-component">
                {% slot "title" default / %}
                {% slot "my-title" / %}
                {% slot "my-title-1" / %}
                {% slot "my-title-2" / %}
                {% slot "escape this: #$%^*()" / %}

                title: {{ component_vars.is_filled.title }}
                my_title: {{ component_vars.is_filled.my_title }}
                my_title_1: {{ component_vars.is_filled.my_title_1 }}
                my_title_2: {{ component_vars.is_filled.my_title_2 }}
                escape_this_________: {{ component_vars.is_filled.escape_this_________ }}
            </div>
        """

    class ComponentWithConditionalSlots(Component):
        template: types.django_html = """
            {# Example from django-components/issues/98 #}
            {% load component_tags %}
            <div class="frontmatter-component">
                <div class="title">{% slot "title" %}Title{% endslot %}</div>
                {% if component_vars.is_filled.subtitle %}
                    <div class="subtitle">
                        {% slot "subtitle" %}Optional subtitle
                        {% endslot %}
                    </div>
                {% endif %}
            </div>
        """

    class ComponentWithComplexConditionalSlots(Component):
        template: types.django_html = """
            {# Example from django-components/issues/98 #}
            {% load component_tags %}
            <div class="frontmatter-component">
                <div class="title">{% slot "title" %}Title{% endslot %}</div>
                {% if component_vars.is_filled.subtitle %}
                    <div class="subtitle">{% slot "subtitle" %}Optional subtitle{% endslot %}</div>
                {% elif component_vars.is_filled.alt_subtitle %}
                    <div class="subtitle">{% slot "alt_subtitle" %}Why would you want this?{% endslot %}</div>
                {% else %}
                <div class="warning">Nothing filled!</div>
                {% endif %}
            </div>
        """

    def setUp(self) -> None:
        super().setUp()
        registry.register("conditional_slots", self.ComponentWithConditionalSlots)
        registry.register(
            "complex_conditional_slots",
            self.ComponentWithComplexConditionalSlots,
        )

    @parametrize_context_behavior(["django", "isolated"])
    def test_is_filled_vars(self):
        registry.register("is_filled_vars", self.IsFilledVarsComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "is_filled_vars" %}
                {% fill "title" / %}
                {% fill "my-title-2" / %}
                {% fill "escape this: #$%^*()" / %}
            {% endcomponent %}
        """

        rendered = Template(template).render(Context())

        expected = """
            <div class="frontmatter-component" data-djc-id-a1bc42>
                title: True
                my_title: False
                my_title_1: False
                my_title_2: True
                escape_this_________: True
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_is_filled_vars_default(self):
        registry.register("is_filled_vars", self.IsFilledVarsComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "is_filled_vars" %}
                bla bla
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div class="frontmatter-component" data-djc-id-a1bc3f>
                bla bla
                title: False
                my_title: False
                my_title_1: False
                my_title_2: False
                escape_this_________: False
            </div>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_simple_component_with_conditional_slot(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "conditional_slots" %}{% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component" data-djc-id-a1bc3f>
            <div class="title">
            Title
            </div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_with_filled_conditional_slot(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "conditional_slots" %}
                {% fill "subtitle" %} My subtitle {% endfill %}
            {% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component" data-djc-id-a1bc40>
                <div class="title">
                    Title
                </div>
                <div class="subtitle">
                    My subtitle
                </div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_elif_of_complex_conditional_slots(self):
        template: types.django_html = """
            {% load component_tags %}
            {% component "complex_conditional_slots" %}
                {% fill "alt_subtitle" %} A different subtitle {% endfill %}
            {% endcomponent %}
        """
        expected = """
           <div class="frontmatter-component" data-djc-id-a1bc40>
             <div class="title">
                Title
             </div>
             <div class="subtitle">
                A different subtitle
             </div>
           </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_else_of_complex_conditional_slots(self):
        template: types.django_html = """
           {% load component_tags %}
           {% component "complex_conditional_slots" %}
           {% endcomponent %}
        """
        expected = """
           <div class="frontmatter-component" data-djc-id-a1bc3f>
             <div class="title">
             Title
             </div>
            <div class="warning">Nothing filled!</div>
           </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_with_negated_conditional_slot(self):
        @register("negated_conditional_slot")
        class ComponentWithNegatedConditionalSlot(Component):
            template: types.django_html = """
                {# Example from django-components/issues/98 #}
                {% load component_tags %}
                <div class="frontmatter-component">
                    <div class="title">{% slot "title" %}Title{% endslot %}</div>
                    {% if not component_vars.is_filled.subtitle %}
                    <div class="warning">Subtitle not filled!</div>
                    {% else %}
                        <div class="subtitle">{% slot "alt_subtitle" %}Why would you want this?{% endslot %}</div>
                    {% endif %}
                </div>
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "negated_conditional_slot" %}
                {# Whoops! Forgot to fill a slot! #}
            {% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component" data-djc-id-a1bc3f>
                <div class="title">
                Title
                </div>
                <div class="warning">Subtitle not filled!</div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_is_filled_vars_in_hooks(self):
        captured_before = None
        captured_after = None

        @register("is_filled_vars")
        class IsFilledVarsComponent(self.IsFilledVarsComponent):  # type: ignore[name-defined]
            def on_render_before(self, context: Context, template: Template) -> None:
                nonlocal captured_before
                captured_before = self.is_filled.copy()

            def on_render_after(self, context: Context, template: Template, content: str) -> None:
                nonlocal captured_after
                captured_after = self.is_filled.copy()

        template: types.django_html = """
            {% load component_tags %}
            {% component "is_filled_vars" %}
                bla bla
            {% endcomponent %}
        """
        Template(template).render(Context())

        expected = {"default": True}
        self.assertEqual(captured_before, expected)
        self.assertEqual(captured_after, expected)
