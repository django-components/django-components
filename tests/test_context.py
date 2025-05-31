from typing import Dict, Optional, cast

from django.http import HttpRequest
from django.template import Context, RequestContext, Template
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import Component, register, registry, types
from django_components.util.misc import gen_id

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


# Context processor that generates a unique ID. This is used to test that the context
# processor is generated only once, as each time this is called, it should generate a different ID.
def dummy_context_processor(request):
    return {"dummy": gen_id()}


#########################
# COMPONENTS
#########################


def gen_simple_component():
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ variable }}</strong>
        """

        def get_template_data(self, args, kwargs, slots, context):
            return {"variable": kwargs.get("variable", None)} if "variable" in kwargs else {}

    return SimpleComponent


def gen_variable_display_component():
    class VariableDisplay(Component):
        template: types.django_html = """
            {% load component_tags %}
            <h1>Shadowing variable = {{ shadowing_variable }}</h1>
            <h1>Uniquely named variable = {{ unique_variable }}</h1>
        """

        def get_template_data(self, args, kwargs, slots, context):
            context = {}
            if kwargs["shadowing_variable"] is not None:
                context["shadowing_variable"] = kwargs["shadowing_variable"]
            if kwargs["new_variable"] is not None:
                context["unique_variable"] = kwargs["new_variable"]
            return context

    return VariableDisplay


def gen_incrementer_component():
    class IncrementerComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <p class="incrementer">value={{ value }};calls={{ calls }}</p>
            {% slot 'content' %}{% endslot %}
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.call_count = 0

        def get_template_data(self, args, kwargs, slots, context):
            value = int(kwargs.get("value", 0))
            if hasattr(self, "call_count"):
                self.call_count += 1
            else:
                self.call_count = 1
            return {"value": value + 1, "calls": self.call_count}

    return IncrementerComponent


def gen_parent_component():
    class ParentComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component "variable_display" shadowing_variable='override' new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component "variable_display" shadowing_variable='slot_default_override' new_variable='slot_default_unique' %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_template_data(self, args, kwargs, slots, context):
            return {"shadowing_variable": "NOT SHADOWED"}

    return ParentComponent


def gen_parent_component_with_args():
    class ParentComponentWithArgs(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div>
                <h1>Parent content</h1>
                {% component "variable_display" shadowing_variable=inner_parent_value new_variable='unique_val' %}
                {% endcomponent %}
            </div>
            <div>
                {% slot 'content' %}
                    <h2>Slot content</h2>
                    {% component "variable_display" shadowing_variable='slot_default_override' new_variable=inner_parent_value %}
                    {% endcomponent %}
                {% endslot %}
            </div>
        """  # noqa

        def get_template_data(self, args, kwargs, slots, context):
            return {"inner_parent_value": kwargs["parent_value"]}

    return ParentComponentWithArgs


#########################
# TESTS
#########################


@djc_test
class TestContext:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_component_context_shadows_parent_with_unfilled_slots_and_component_tag(
        self, components_settings,
    ):
        registry.register(name="variable_display", component=gen_variable_display_component())
        registry.register(name="parent_component", component=gen_parent_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        assertInHTML("<h1 data-djc-id-ca1bc43>Shadowing variable = override</h1>", rendered)
        assertInHTML("<h1 data-djc-id-ca1bc44>Shadowing variable = slot_default_override</h1>", rendered)
        assert "Shadowing variable = NOT SHADOWED" not in rendered

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_component_instances_have_unique_context_with_unfilled_slots_and_component_tag(
        self, components_settings,
    ):
        registry.register(name="variable_display", component=gen_variable_display_component())
        registry.register(name="parent_component", component=gen_parent_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        assertInHTML("<h1 data-djc-id-ca1bc43>Uniquely named variable = unique_val</h1>", rendered)
        assertInHTML(
            "<h1 data-djc-id-ca1bc44>Uniquely named variable = slot_default_unique</h1>",
            rendered,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_component_context_shadows_parent_with_filled_slots(self, components_settings):
        registry.register(name="variable_display", component=gen_variable_display_component())
        registry.register(name="parent_component", component=gen_parent_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component 'variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context())

        assertInHTML("<h1 data-djc-id-ca1bc45>Shadowing variable = override</h1>", rendered)
        assertInHTML("<h1 data-djc-id-ca1bc46>Shadowing variable = shadow_from_slot</h1>", rendered)
        assert "Shadowing variable = NOT SHADOWED" not in rendered

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_component_instances_have_unique_context_with_filled_slots(self, components_settings):
        registry.register(name="variable_display", component=gen_variable_display_component())
        registry.register(name="parent_component", component=gen_parent_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component 'variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context())

        assertInHTML("<h1 data-djc-id-ca1bc45>Uniquely named variable = unique_val</h1>", rendered)
        assertInHTML("<h1 data-djc-id-ca1bc46>Uniquely named variable = unique_from_slot</h1>", rendered)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_component_context_shadows_outer_context_with_unfilled_slots_and_component_tag(
        self, components_settings,
    ):
        registry.register(name="variable_display", component=gen_variable_display_component())
        registry.register(name="parent_component", component=gen_parent_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"shadowing_variable": "NOT SHADOWED"}))

        assertInHTML("<h1 data-djc-id-ca1bc43>Shadowing variable = override</h1>", rendered)
        assertInHTML("<h1 data-djc-id-ca1bc44>Shadowing variable = slot_default_override</h1>", rendered)
        assert "Shadowing variable = NOT SHADOWED" not in rendered

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_nested_component_context_shadows_outer_context_with_filled_slots(
        self, components_settings,
    ):
        registry.register(name="variable_display", component=gen_variable_display_component())
        registry.register(name="parent_component", component=gen_parent_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_component' %}
                {% fill 'content' %}
                    {% component 'variable_display' shadowing_variable='shadow_from_slot' new_variable='unique_from_slot' %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
        """  # NOQA
        template = Template(template_str)
        rendered = template.render(Context({"shadowing_variable": "NOT SHADOWED"}))

        assertInHTML("<h1 data-djc-id-ca1bc45>Shadowing variable = override</h1>", rendered)
        assertInHTML("<h1 data-djc-id-ca1bc46>Shadowing variable = shadow_from_slot</h1>", rendered)
        assert "Shadowing variable = NOT SHADOWED" not in rendered


@djc_test
class TestParentArgs:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_parent_args_can_be_drawn_from_context(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
        registry.register(name="parent_with_args", component=gen_parent_component_with_args())
        registry.register(name="variable_display", component=gen_variable_display_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_with_args' parent_value=parent_value %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"parent_value": "passed_in"}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3f>
                <h1>Parent content</h1>
                <h1 data-djc-id-ca1bc43>Shadowing variable = passed_in</h1>
                <h1 data-djc-id-ca1bc43>Uniquely named variable = unique_val</h1>
            </div>
            <div data-djc-id-ca1bc3f>
                <h2>Slot content</h2>
                <h1 data-djc-id-ca1bc44>Shadowing variable = slot_default_override</h1>
                <h1 data-djc-id-ca1bc44>Uniquely named variable = passed_in</h1>
            </div>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_parent_args_available_outside_slots(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
        registry.register(name="parent_with_args", component=gen_parent_component_with_args())
        registry.register(name="variable_display", component=gen_variable_display_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_with_args' parent_value='passed_in' %}{%endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context())

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3f>
                <h1>Parent content</h1>
                <h1 data-djc-id-ca1bc43>Shadowing variable = passed_in</h1>
                <h1 data-djc-id-ca1bc43>Uniquely named variable = unique_val</h1>
            </div>
            <div data-djc-id-ca1bc3f>
                <h2>Slot content</h2>
                <h1 data-djc-id-ca1bc44>Shadowing variable = slot_default_override</h1>
                <h1 data-djc-id-ca1bc44>Uniquely named variable = passed_in</h1>
            </div>
            """,
        )
        assert "Shadowing variable = NOT SHADOWED" not in rendered

    @djc_test(
        parametrize=(
            ["components_settings", "first_val", "second_val"],
            [
                [{"context_behavior": "django"}, "passed_in", "passed_in"],
                [{"context_behavior": "isolated"}, "passed_in", ""],
            ],
            ["django", "isolated"],
        )
    )
    def test_parent_args_available_in_slots(self, components_settings, first_val, second_val):
        registry.register(name="incrementer", component=gen_incrementer_component())
        registry.register(name="parent_with_args", component=gen_parent_component_with_args())
        registry.register(name="variable_display", component=gen_variable_display_component())

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'parent_with_args' parent_value='passed_in' %}
                {% fill 'content' %}
                    {% component 'variable_display' shadowing_variable='value_from_slot' new_variable=inner_parent_value %}
                    {% endcomponent %}
                {% endfill %}
            {% endcomponent %}
            """  # noqa: E501
        template = Template(template_str)
        rendered = template.render(Context())

        assertHTMLEqual(
            rendered,
            f"""
            <div data-djc-id-ca1bc41>
                <h1>Parent content</h1>
                <h1 data-djc-id-ca1bc45>Shadowing variable = {first_val}</h1>
                <h1 data-djc-id-ca1bc45>Uniquely named variable = unique_val</h1>
            </div>
            <div data-djc-id-ca1bc41>
                <h1 data-djc-id-ca1bc46>Shadowing variable = value_from_slot</h1>
                <h1 data-djc-id-ca1bc46>Uniquely named variable = {second_val}</h1>
            </div>
            """,
        )


@djc_test
class TestContextCalledOnce:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_one_context_call_with_simple_component(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip().replace("\n", "")
        assertHTMLEqual(
            rendered,
            '<p class="incrementer" data-djc-id-ca1bc3f>value=1;calls=1</p>',
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_one_context_call_with_simple_component_and_arg(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' value='2' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        assertHTMLEqual(
            rendered,
            """
            <p class="incrementer" data-djc-id-ca1bc3f>value=3;calls=1</p>
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_one_context_call_with_component(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        assertHTMLEqual(rendered, '<p class="incrementer" data-djc-id-ca1bc3f>value=1;calls=1</p>')

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_one_context_call_with_component_and_arg(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'incrementer' value='3' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context()).strip()

        assertHTMLEqual(rendered, '<p class="incrementer" data-djc-id-ca1bc3f>value=4;calls=1</p>')

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_one_context_call_with_slot(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
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

        assertHTMLEqual(
            rendered,
            """
            <p class="incrementer" data-djc-id-ca1bc40>value=1;calls=1</p>
            <p data-djc-id-ca1bc40>slot</p>
            """,
            rendered,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_one_context_call_with_slot_and_arg(self, components_settings):
        registry.register(name="incrementer", component=gen_incrementer_component())
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

        assertHTMLEqual(
            rendered,
            """
            <p class="incrementer" data-djc-id-ca1bc40>value=4;calls=1</p>
            <p data-djc-id-ca1bc40>slot</p>
            """,
            rendered,
        )


@djc_test
class TestComponentsCanAccessOuterContext:
    @djc_test(
        parametrize=(
            ["components_settings", "expected_value"],
            [
                [{"context_behavior": "django"}, "outer_value"],
                [{"context_behavior": "isolated"}, ""],
            ],
            ["django", "isolated"],
        )
    )
    def test_simple_component_can_use_outer_context(self, components_settings, expected_value):
        registry.register(name="simple_component", component=gen_simple_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        assertHTMLEqual(
            rendered,
            f"""
            Variable: <strong data-djc-id-ca1bc3f> {expected_value} </strong>
            """,
        )


@djc_test
class TestIsolatedContext:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_simple_component_can_pass_outer_context_in_args(self, components_settings):
        registry.register(name="simple_component", component=gen_simple_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' variable=variable only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        assert "outer_value" in rendered

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_simple_component_cannot_use_outer_context(self, components_settings):
        registry.register(name="simple_component", component=gen_simple_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        assert "outer_value" not in rendered


@djc_test
class TestIsolatedContextSetting:
    @djc_test(components_settings={"context_behavior": "isolated"})
    def test_component_tag_includes_variable_with_isolated_context_from_settings(
        self,
    ):
        registry.register(name="simple_component", component=gen_simple_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' variable=variable %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        assert "outer_value" in rendered

    @djc_test(components_settings={"context_behavior": "isolated"})
    def test_component_tag_excludes_variable_with_isolated_context_from_settings(
        self,
    ):
        registry.register(name="simple_component", component=gen_simple_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        assert "outer_value" not in rendered

    @djc_test(components_settings={"context_behavior": "isolated"})
    def test_component_includes_variable_with_isolated_context_from_settings(
        self,
    ):
        registry.register(name="simple_component", component=gen_simple_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' variable=variable %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        assert "outer_value" in rendered

    @djc_test(components_settings={"context_behavior": "isolated"})
    def test_component_excludes_variable_with_isolated_context_from_settings(
        self,
    ):
        registry.register(name="simple_component", component=gen_simple_component())
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'simple_component' %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"}))
        assert "outer_value" not in rendered


@djc_test
class TestContextProcessors:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_context_in_template(self, components_settings):
        context_processors_data: Optional[Dict] = None
        inner_request: Optional[HttpRequest] = None

        @register("test")
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal inner_request
                context_processors_data = self.context_processors_data
                inner_request = self.request

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test" %}
            {% endcomponent %}
        """
        request = HttpRequest()
        request_context = RequestContext(request)

        template = Template(template_str)
        rendered = template.render(request_context)

        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert inner_request == request

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_context_in_template_nested(self, components_settings):
        context_processors_data = None
        context_processors_data_child = None
        parent_request: Optional[HttpRequest] = None
        child_request: Optional[HttpRequest] = None

        @register("test_parent")
        class TestParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component "test_child" / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal parent_request
                context_processors_data = self.context_processors_data
                parent_request = self.request

        @register("test_child")
        class TestChildComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data_child
                nonlocal child_request
                context_processors_data_child = self.context_processors_data
                child_request = self.request

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test_parent" / %}
        """
        request = HttpRequest()
        request_context = RequestContext(request)

        template = Template(template_str)
        rendered = template.render(request_context)

        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert list(context_processors_data_child.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert parent_request == request
        assert child_request == request

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_context_in_template_slot(self, components_settings):
        context_processors_data = None
        context_processors_data_child = None
        parent_request: Optional[HttpRequest] = None
        child_request: Optional[HttpRequest] = None

        @register("test_parent")
        class TestParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% slot "content" default / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal parent_request
                context_processors_data = self.context_processors_data
                parent_request = self.request

        @register("test_child")
        class TestChildComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data_child
                nonlocal child_request
                context_processors_data_child = self.context_processors_data
                child_request = self.request

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test_parent" %}
                {% component "test_child" / %}
            {% endcomponent %}
        """
        request = HttpRequest()
        request_context = RequestContext(request)

        template = Template(template_str)
        rendered = template.render(request_context)

        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert list(context_processors_data_child.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert parent_request == request
        assert child_request == request

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_context_in_python(self, components_settings):
        context_processors_data = None
        inner_request: Optional[HttpRequest] = None

        @register("test")
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal inner_request
                context_processors_data = self.context_processors_data
                inner_request = self.request

        request = HttpRequest()
        request_context = RequestContext(request)
        rendered = TestComponent.render(context=request_context)

        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert inner_request == request

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_context_in_python_nested(self, components_settings):
        context_processors_data: Optional[Dict] = None
        context_processors_data_child: Optional[Dict] = None
        parent_request: Optional[HttpRequest] = None
        child_request: Optional[HttpRequest] = None

        @register("test_parent")
        class TestParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component "test_child" / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal parent_request
                context_processors_data = self.context_processors_data
                parent_request = self.request

        @register("test_child")
        class TestChildComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data_child
                nonlocal child_request
                context_processors_data_child = self.context_processors_data
                child_request = self.request

        request = HttpRequest()
        request_context = RequestContext(request)

        rendered = TestParentComponent.render(request_context)
        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert list(context_processors_data_child.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert parent_request == request
        assert child_request == request

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_in_python(self, components_settings):
        context_processors_data: Optional[Dict] = None
        inner_request: Optional[HttpRequest] = None

        @register("test")
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal inner_request
                context_processors_data = self.context_processors_data
                inner_request = self.request

        request = HttpRequest()
        rendered = TestComponent.render(request=request)

        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert inner_request == request

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_request_in_python_nested(self, components_settings):
        context_processors_data: Optional[Dict] = None
        context_processors_data_child: Optional[Dict] = None
        parent_request: Optional[HttpRequest] = None
        child_request: Optional[HttpRequest] = None

        @register("test_parent")
        class TestParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component "test_child" / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal parent_request
                context_processors_data = self.context_processors_data
                parent_request = self.request

        @register("test_child")
        class TestChildComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data_child
                nonlocal child_request
                context_processors_data_child = self.context_processors_data
                child_request = self.request

        request = HttpRequest()
        rendered = TestParentComponent.render(request=request)

        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert list(context_processors_data_child.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert parent_request == request
        assert child_request == request

    # No request, regular Context
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_no_context_processor_when_non_request_context_in_python(self, components_settings):
        context_processors_data: Optional[Dict] = None
        inner_request: Optional[HttpRequest] = None

        @register("test")
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal inner_request
                context_processors_data = self.context_processors_data
                inner_request = self.request

        rendered = TestComponent.render(context=Context())

        assert "csrfmiddlewaretoken" not in rendered
        assert list(context_processors_data.keys()) == []  # type: ignore[union-attr]
        assert inner_request is None

    # No request, no Context
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_no_context_processor_when_non_request_context_in_python_2(self, components_settings):
        context_processors_data: Optional[Dict] = None
        inner_request: Optional[HttpRequest] = None

        @register("test")
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal inner_request
                context_processors_data = self.context_processors_data
                inner_request = self.request

        rendered = TestComponent.render()

        assert "csrfmiddlewaretoken" not in rendered
        assert list(context_processors_data.keys()) == []  # type: ignore[union-attr]
        assert inner_request is None

    # Yes request, regular Context
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_context_processor_when_regular_context_and_request_in_python(self, components_settings):
        context_processors_data: Optional[Dict] = None
        inner_request: Optional[HttpRequest] = None

        @register("test")
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                nonlocal inner_request
                context_processors_data = self.context_processors_data
                inner_request = self.request

        request = HttpRequest()
        rendered = TestComponent.render(Context(), request=request)

        assert "csrfmiddlewaretoken" in rendered
        assert list(context_processors_data.keys()) == ["csrf_token"]  # type: ignore[union-attr]
        assert inner_request == request

    @djc_test(django_settings={
        "TEMPLATES": [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": ["tests/templates/", "tests/components/"],
                "OPTIONS": {
                    "builtins": [
                        "django_components.templatetags.component_tags",
                    ],
                    "context_processors": [
                        "tests.test_context.dummy_context_processor",
                    ],
                },
            }
        ],
    })
    def test_data_generated_only_once(self):
        context_processors_data: Optional[Dict] = None
        context_processors_data_child: Optional[Dict] = None

        @register("test_parent")
        class TestParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component "test_child" / %}
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data
                context_processors_data = self.context_processors_data

        @register("test_child")
        class TestChildComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal context_processors_data_child
                context_processors_data_child = self.context_processors_data

        request = HttpRequest()
        TestParentComponent.render(request=request)

        parent_data = cast(dict, context_processors_data)
        child_data = cast(dict, context_processors_data_child)

        # Check that the context processors data is reused across the components with
        # the same request.
        assert list(parent_data.keys()) == ["csrf_token", "dummy"]
        assert list(child_data.keys()) == ["csrf_token", "dummy"]

        assert parent_data["dummy"] == "a1bc3f"
        assert child_data["dummy"] == "a1bc3f"
        assert parent_data["csrf_token"] == child_data["csrf_token"]

    def test_context_processors_data_outside_of_rendering(self):
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

        request = HttpRequest()
        component = TestComponent(request=request)
        data = component.context_processors_data

        assert list(data.keys()) == ["csrf_token"]

    def test_request_outside_of_rendering(self):
        class TestComponent(Component):
            template: types.django_html = """{% csrf_token %}"""

        request = HttpRequest()
        component = TestComponent(request=request)

        assert component.request == request


@djc_test
class TestOuterContextProperty:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_outer_context_property_with_component(self, components_settings):
        @register("outer_context_component")
        class OuterContextComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_template_data(self, args, kwargs, slots, context):
                return self.outer_context.flatten()  # type: ignore[union-attr]

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'outer_context_component' only %}{% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"variable": "outer_value"})).strip()
        assert "outer_value" in rendered


# TODO_v1: Remove, superseded by `component_vars.slots`
@djc_test
class TestContextVarsIsFilled:
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

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_is_filled_vars(self, components_settings):
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
            <div class="frontmatter-component" data-djc-id-ca1bc42>
                title: True
                my_title: False
                my_title_1: False
                my_title_2: True
                escape_this_________: True
            </div>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_is_filled_vars_default(self, components_settings):
        registry.register("is_filled_vars", self.IsFilledVarsComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "is_filled_vars" %}
                bla bla
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <div class="frontmatter-component" data-djc-id-ca1bc3f>
                bla bla
                title: False
                my_title: False
                my_title_1: False
                my_title_2: False
                escape_this_________: False
            </div>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_simple_component_with_conditional_slot(self, components_settings):
        registry.register("conditional_slots", self.ComponentWithConditionalSlots)

        template: types.django_html = """
            {% load component_tags %}
            {% component "conditional_slots" %}{% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component" data-djc-id-ca1bc3f>
            <div class="title">
            Title
            </div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_with_filled_conditional_slot(self, components_settings):
        registry.register("conditional_slots", self.ComponentWithConditionalSlots)

        template: types.django_html = """
            {% load component_tags %}
            {% component "conditional_slots" %}
                {% fill "subtitle" %} My subtitle {% endfill %}
            {% endcomponent %}
        """
        expected = """
            <div class="frontmatter-component" data-djc-id-ca1bc40>
                <div class="title">
                    Title
                </div>
                <div class="subtitle">
                    My subtitle
                </div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_elif_of_complex_conditional_slots(self, components_settings):
        registry.register(
            "complex_conditional_slots",
            self.ComponentWithComplexConditionalSlots,
        )

        template: types.django_html = """
            {% load component_tags %}
            {% component "complex_conditional_slots" %}
                {% fill "alt_subtitle" %} A different subtitle {% endfill %}
            {% endcomponent %}
        """
        expected = """
           <div class="frontmatter-component" data-djc-id-ca1bc40>
             <div class="title">
                Title
             </div>
             <div class="subtitle">
                A different subtitle
             </div>
           </div>
        """
        rendered = Template(template).render(Context({}))
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_else_of_complex_conditional_slots(self, components_settings):
        registry.register(
            "complex_conditional_slots",
            self.ComponentWithComplexConditionalSlots,
        )

        template: types.django_html = """
           {% load component_tags %}
           {% component "complex_conditional_slots" %}
           {% endcomponent %}
        """
        expected = """
           <div class="frontmatter-component" data-djc-id-ca1bc3f>
             <div class="title">
             Title
             </div>
            <div class="warning">Nothing filled!</div>
           </div>
        """
        rendered = Template(template).render(Context({}))
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_with_negated_conditional_slot(self, components_settings):
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
            <div class="frontmatter-component" data-djc-id-ca1bc3f>
                <div class="title">
                Title
                </div>
                <div class="warning">Subtitle not filled!</div>
            </div>
        """
        rendered = Template(template).render(Context({}))
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_is_filled_vars_in_hooks(self, components_settings):
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
        assert captured_before == expected
        assert captured_after == expected
