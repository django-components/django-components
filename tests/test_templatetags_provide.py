import gc
import re
from weakref import ref

import pytest
from django.template import Context, Template, TemplateSyntaxError
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.component import ComponentContext
from django_components.perfutil.component import component_context_cache, component_instance_cache
from django_components.perfutil.provide import component_provides, provide_cache, provide_references
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


# NOTE: By running garbage collection and then checking for empty caches,
#       we ensure that we are not introducing any memory leaks.
def _assert_clear_cache():
    # Ensure that finalizers have run
    gc.collect()

    assert provide_cache == {}
    assert provide_references == {}
    assert component_provides == {}
    assert component_instance_cache == {}
    assert component_context_cache == {}


@djc_test
class TestProvideTemplateTag:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_basic(self, components_settings):
        @register("injectee1")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=1 %}
                {% component "injectee1" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> injected: DepInject(key='hi', another=1) </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_basic_self_closing(self, components_settings):
        template_str: types.django_html = """
            {% load component_tags %}
            <div>
                {% provide "my_provide" key="hi" another=2 / %}
            </div>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div></div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_access_keys_in_python(self, components_settings):
        @register("injectee2")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> key: {{ key }} </div>
                <div> another: {{ another }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                my_provide = self.inject("my_provide")
                return {
                    "key": my_provide.key,
                    "another": my_provide.another,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=3 %}
                {% component "injectee2" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> key: hi </div>
            <div data-djc-id-ca1bc41> another: 3 </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_access_keys_in_django(self, components_settings):
        @register("injectee3")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> key: {{ my_provide.key }} </div>
                <div> another: {{ my_provide.another }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                my_provide = self.inject("my_provide")
                return {
                    "my_provide": my_provide,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=4 %}
                {% component "injectee3" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> key: hi </div>
            <div data-djc-id-ca1bc41> another: 4 </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_does_not_leak(self, components_settings):
        @register("injectee4")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=5 %}
            {% endprovide %}
            {% component "injectee4" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> injected: default </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_empty(self, components_settings):
        """Check provide tag with no kwargs"""

        @register("injectee5")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" %}
                {% component "injectee5" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee5" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc42> injected: DepInject() </div>
            <div data-djc-id-ca1bc43> injected: default </div>
        """,
        )
        _assert_clear_cache()

    @djc_test(components_settings={"context_behavior": "django"})
    def test_provide_no_inject(self):
        """Check that nothing breaks if we do NOT inject even if some data is provided"""

        @register("injectee6")
        class InjectComponent(Component):
            template: types.django_html = """
                <div></div>
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=6 %}
                {% component "injectee6" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee6" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc42></div>
            <div data-djc-id-ca1bc43></div>
        """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_single_quotes(self, components_settings):
        @register("injectee7")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide 'my_provide' key="hi" another=7 %}
                {% component "injectee7" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee7" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc42> injected: DepInject(key='hi', another=7) </div>
            <div data-djc-id-ca1bc43> injected: default </div>
        """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_as_var(self, components_settings):
        @register("injectee8")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide var_a key="hi" another=8 %}
                {% component "injectee8" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee8" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": "my_provide",
                },
            ),
        )

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc42> injected: DepInject(key='hi', another=8) </div>
            <div data-djc-id-ca1bc43> injected: default </div>
        """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_as_spread(self, components_settings):
        @register("injectee9")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide ...provide_props %}
                {% component "injectee9" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee9" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "provide_props": {
                        "name": "my_provide",
                        "key": "hi",
                        "another": 9,
                    },
                },
            ),
        )

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc42> injected: DepInject(key='hi', another=9) </div>
            <div data-djc-id-ca1bc43> injected: default </div>
        """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_no_name_raises(self, components_settings):
        @register("injectee10")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide key="hi" another=10 %}
                {% component "injectee10" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee10" %}
            {% endcomponent %}
        """
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'provide': missing a required argument: 'name'"),
        ):
            Template(template_str).render(Context({}))

        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_must_be_string_literal(self, components_settings):
        @register("injectee11")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide my_var key="hi" another=11 %}
                {% component "injectee11" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee11" %}
            {% endcomponent %}
        """
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Provide tag received an empty string. Key must be non-empty and a valid identifier"),
        ):
            Template(template_str).render(Context({}))

        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_must_be_identifier(self, components_settings):
        @register("injectee12")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "%heya%" key="hi" another=12 %}
                {% component "injectee12" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee12" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(TemplateSyntaxError):
            template.render(Context({}))
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_aggregate_dics(self, components_settings):
        @register("injectee13")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" var1:key="hi" var1:another=13 var2:x="y" %}
                {% component "injectee13" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> injected: DepInject(var1={'key': 'hi', 'another': 13}, var2={'x': 'y'}) </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_does_not_expose_kwargs_to_context(self, components_settings):
        """Check that `provide` tag doesn't assign the keys to the context like `with` tag does"""

        @register("injectee14")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            var_out: {{ var }}
            key_out: {{ key }}
            {% provide "my_provide" key="hi" another=14 %}
                var_in: {{ var }}
                key_in: {{ key }}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"var": "123"}))

        assertHTMLEqual(
            rendered,
            """
            var_out: 123
            key_out:
            var_in: 123
            key_in:
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_nested_in_provide_same_key(self, components_settings):
        """Check that inner `provide` with same key overshadows outer `provide`"""

        @register("injectee15")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=15 lost=0 %}
                {% provide "my_provide" key="hi1" another=16 new=3 %}
                    {% component "injectee15" %}
                    {% endcomponent %}
                {% endprovide %}

                {% component "injectee15" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee15" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc45> injected: DepInject(key='hi1', another=16, new=3) </div>
            <div data-djc-id-ca1bc46> injected: DepInject(key='hi', another=15, lost=0) </div>
            <div data-djc-id-ca1bc47> injected: default </div>
            """,
        )

        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_nested_in_provide_different_key(self, components_settings):
        """Check that `provide` tag with different keys don't affect each other"""

        @register("injectee16")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> first_provide: {{ first_provide|safe }} </div>
                <div> second_provide: {{ second_provide|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                first_provide = self.inject("first_provide", "default")
                second_provide = self.inject("second_provide", "default")
                return {
                    "first_provide": first_provide,
                    "second_provide": second_provide,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "first_provide" key="hi" another=17 lost=0 %}
                {% provide "second_provide" key="hi1" another=18 new=3 %}
                    {% component "injectee16" %}
                    {% endcomponent %}
                {% endprovide %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc43> first_provide: DepInject(key='hi', another=17, lost=0) </div>
            <div data-djc-id-ca1bc43> second_provide: DepInject(key='hi1', another=18, new=3) </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_in_include(self, components_settings):
        @register("injectee17")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=19 %}
                {% include "inject.html" %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div>
                <div data-djc-id-ca1bc41> injected: DepInject(key='hi', another=19) </div>
            </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slot_in_provide(self, components_settings):
        @register("injectee18")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide", "default")
                return {"var": var}

        @register("parent")
        class ParentComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" another=20 %}
                    {% slot "content" default %}{% endslot %}
                {% endprovide %}
            """

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "parent" %}
                {% component "injectee18" %}{% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc40 data-djc-id-ca1bc44>
                injected: DepInject(key='hi', another=20)
            </div>
            """,
        )
        _assert_clear_cache()

    # TODO - Enable once globals and finalizers are scoped to a single DJC instance")
    #        See https://github.com/django-components/django-components/issues/1413
    @pytest.mark.skip("#TODO")
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_component_inside_forloop(self, components_settings):
        @register("loop_component")
        class LoopComponent(Component):
            template: types.django_html = """
                <div>Item {{ item_num }}: {{ provided_value }}</div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                provided_data = self.inject("loop_provide")
                return {
                    "item_num": kwargs["item_num"],
                    "provided_value": provided_data.shared_value,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "loop_provide" shared_value="shared_data" %}
                {% for i in items %}
                    {% component "loop_component" item_num=i / %}
                {% endfor %}
            {% endprovide %}
        """

        template = Template(template_str)
        context = Context({"items": [1, 2, 3, 4, 5]})
        rendered = template.render(context)

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41>Item 1: shared_data</div>
            <div data-djc-id-ca1bc42>Item 2: shared_data</div>
            <div data-djc-id-ca1bc43>Item 3: shared_data</div>
            <div data-djc-id-ca1bc44>Item 4: shared_data</div>
            <div data-djc-id-ca1bc45>Item 5: shared_data</div>
            """,
        )

        # Ensure that finalizers have run
        gc.collect()

        # Ensure all caches are properly cleaned up even with multiple component instances
        _assert_clear_cache()

    # TODO - Enable once globals and finalizers are scoped to a single DJC instance")
    #        See https://github.com/django-components/django-components/issues/1413
    @pytest.mark.skip("#TODO")
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_component_inside_nested_forloop(self, components_settings):
        @register("nested_loop_component")
        class NestedLoopComponent(Component):
            template: types.django_html = """
                <span>{{ outer }}-{{ inner }}: {{ provided_value }}</span>
            """

            def get_template_data(self, args, kwargs, slots, context):
                provided_data = self.inject("nested_provide")
                return {
                    "outer": kwargs["outer"],
                    "inner": kwargs["inner"],
                    "provided_value": provided_data.nested_value,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "nested_provide" nested_value="nested_data" %}
                {% for outer in outer_items %}
                    {% for inner in inner_items %}
                        {% component "nested_loop_component" outer=outer inner=inner / %}
                    {% endfor %}
                {% endfor %}
            {% endprovide %}
        """

        template = Template(template_str)
        context = Context({"outer_items": ["A", "B"], "inner_items": [1, 2]})
        rendered = template.render(context)

        assertHTMLEqual(
            rendered,
            """
            <span data-djc-id-ca1bc41>A-1: nested_data</span>
            <span data-djc-id-ca1bc42>A-2: nested_data</span>
            <span data-djc-id-ca1bc43>B-1: nested_data</span>
            <span data-djc-id-ca1bc44>B-2: nested_data</span>
            """,
        )

        # Ensure all caches are properly cleaned up even with many component instances
        _assert_clear_cache()

    # TODO - Enable once globals and finalizers are scoped to a single DJC instance")
    #        See https://github.com/django-components/django-components/issues/1413
    @pytest.mark.skip("#TODO")
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_component_forloop_with_error(self, components_settings):
        @register("error_loop_component")
        class ErrorLoopComponent(Component):
            template = ""

            def get_template_data(self, args, kwargs, slots, context):
                provided_data = self.inject("error_provide")
                item_num = kwargs["item_num"]

                # Throw error on the third item
                if item_num == 3:
                    raise ValueError(f"Error on item {item_num}")

                return {
                    "item_num": item_num,
                    "provided_value": provided_data.error_value,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "error_provide" error_value="error_data" %}
                {% for i in items %}
                    {% component "error_loop_component" item_num=i / %}
                {% endfor %}
            {% endprovide %}
        """

        template = Template(template_str)
        context = Context({"items": [1, 2, 3, 4, 5]})

        with pytest.raises(ValueError, match=re.escape("Error on item 3")):
            template.render(context)

        # Ensure all caches are properly cleaned up even when errors occur
        _assert_clear_cache()


@djc_test
class TestInject:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_basic(self, components_settings):
        @register("injectee19")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("my_provide")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=21 %}
                {% component "injectee19" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> injected: DepInject(key='hi', another=21) </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_missing_key_raises_without_default(self, components_settings):
        @register("injectee20")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("abc")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "injectee20" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(KeyError):
            template.render(Context({}))

        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_missing_key_ok_with_default(self, components_settings):
        @register("injectee21")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("abc", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "injectee21" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3f> injected: default </div>
            """,
        )
        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_empty_string(self, components_settings):
        @register("injectee22")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=22 %}
                {% component "injectee22" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee22" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(KeyError):
            template.render(Context({}))

        _assert_clear_cache()

    # TODO - Enable once globals and finalizers are scoped to a single DJC instance")
    #        See https://github.com/django-components/django-components/issues/1413
    # @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    @djc_test(
        parametrize=(
            ["components_settings"],
            [
                [{"context_behavior": "isolated"}],
            ],
            ["isolated"],
        )
    )
    def test_inject_called_outside_rendering__persisted_ref(self, components_settings):
        comp = None

        @register("injectee23")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = self

                var = self.inject(key="my_provide")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" value=23 %}
                {% component "injectee23" / %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> injected: DepInject(key='hi', value=23) </div>
            """,
        )

        assert comp is not None

        # Check that we can inject the data even after the component was rendered.
        injected = comp.inject(key="my_provide", default="def")
        assert isinstance(injected, tuple)
        assert injected.key == "hi"  # type: ignore[attr-defined]
        assert injected.value == 23  # type: ignore[attr-defined]

        # NOTE: Because we kept the reference to the component, it's not garbage collected yet.
        gc.collect()

        assert provide_cache == {"a1bc40": ("hi", 23)}
        assert provide_references == {"a1bc40": {"ca1bc41"}}
        assert component_provides == {"ca1bc41": {"my_provide": "a1bc40"}}
        assert component_instance_cache == {}
        assert len(component_context_cache) == 1
        assert isinstance(component_context_cache["ca1bc41"], ComponentContext)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_called_outside_rendering__not_persisted(self, components_settings):
        comp = None

        @register("injectee24")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal comp
                comp = ref(self)

                var = self.inject(key="my_provide")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" value=23 %}
                {% component "injectee24" / %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41> injected: DepInject(key='hi', value=23) </div>
            """,
        )

        gc.collect()

        # We didn't keep the reference, so the caches should be cleared.
        assert comp is not None
        assert comp() is None
        _assert_clear_cache()

    # See https://github.com/django-components/django-components/pull/778
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_in_fill(self, components_settings):
        @register("injectee25")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <main>
                    {% slot "content" default / %}
                </main>
            """

            def get_template_data(self, args, kwargs, slots, context):
                data = self.inject("my_provide")
                return {"data": data}

        @register("provider")
        class Provider(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"data": kwargs["data"]}

            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" data=data %}
                    {% slot "content" default / %}
                {% endprovide %}
            """

        @register("parent")
        class Parent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"data": kwargs["data"]}

            template: types.django_html = """
                {% load component_tags %}
                {% component "provider" data=data %}
                    {% component "injectee25" %}
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

        rendered = Root.render()

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3e data-djc-id-ca1bc41 data-djc-id-ca1bc45 data-djc-id-ca1bc49>
                injected: DepInject(key='hi', data=123)
            </div>
            <main data-djc-id-ca1bc3e data-djc-id-ca1bc41 data-djc-id-ca1bc45 data-djc-id-ca1bc49>
                456
            </main>
            """,
        )
        _assert_clear_cache()

    # See https://github.com/django-components/django-components/pull/786
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_in_slot_in_fill(self, components_settings):
        @register("injectee26")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <main>
                    {% slot "content" default / %}
                </main>
            """

            def get_template_data(self, args, kwargs, slots, context):
                data = self.inject("my_provide")
                return {"data": data}

        @register("provider")
        class Provider(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"data": kwargs["data"]}

            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" data=data %}
                    {% slot "content" default / %}
                {% endprovide %}
            """

        @register("parent")
        class Parent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {"data": kwargs["data"]}

            template: types.django_html = """
                {% load component_tags %}
                {% component "provider" data=data %}
                    {% slot "content" default / %}
                {% endcomponent %}
            """

        @register("root")
        class Root(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% component "parent" data=123 %}
                    {% component "injectee26" / %}
                {% endcomponent %}
            """

        rendered = Root.render()

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3e data-djc-id-ca1bc41 data-djc-id-ca1bc44 data-djc-id-ca1bc48>
                injected: DepInject(key='hi', data=123)
            </div>
            <main data-djc-id-ca1bc3e data-djc-id-ca1bc41 data-djc-id-ca1bc44 data-djc-id-ca1bc48>
            </main>
            """,
        )
        _assert_clear_cache()


# When there is `{% component %}` that's a descendant of `{% provide %}`,
# then the cache entry is NOT removed as soon as we have rendered the children (nodelist)
# of `{% provide %}`.
#
# Instead, we manage the state ourselves, and remove the cache entry
# when the component rendered is done.
@djc_test
class TestProvideCache:
    def test_provide_outside_component(self):
        @register("injectee27")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <div> Ran: {{ ran }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                assert len(provide_cache) == 1

                data = self.inject("my_provide")
                return {"data": data, "ran": True}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=23 %}
                {% component "injectee27" / %}
            {% endprovide %}
        """

        _assert_clear_cache()

        template = Template(template_str)
        _assert_clear_cache()

        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc41>
                injected: DepInject(key='hi', another=23)
            </div>
            <div data-djc-id-ca1bc41>
                Ran: True
            </div>
            """,
        )
        _assert_clear_cache()

    # Cache should be cleared even if there is an error.
    def test_provide_outside_component_with_error(self):
        @register("injectee28")
        class Injectee(Component):
            template = ""

            def get_template_data(self, args, kwargs, slots, context):
                assert len(provide_cache) == 1
                data = self.inject("my_provide")

                raise ValueError("Oops")
                return {"data": data, "ran": True}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=24 %}
                {% component "injectee28" / %}
            {% endprovide %}
        """

        _assert_clear_cache()

        template = Template(template_str)
        _assert_clear_cache()

        with pytest.raises(ValueError, match=re.escape("Oops")):
            template.render(Context({}))

        _assert_clear_cache()

    def test_provide_inside_component(self):
        @register("injectee29")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <div> Ran: {{ ran }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                assert len(provide_cache) == 1

                data = self.inject("my_provide")
                return {"data": data, "ran": True}

        @register("root")
        class Root(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" another=25 %}
                    {% component "injectee29" / %}
                {% endprovide %}
            """

        _assert_clear_cache()

        rendered = Root.render()

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-ca1bc3e data-djc-id-ca1bc42>
                injected: DepInject(key='hi', another=25)
            </div>
            <div data-djc-id-ca1bc3e data-djc-id-ca1bc42>
                Ran: True
            </div>
            """,
        )
        _assert_clear_cache()

    def test_provide_inside_component_with_error(self):
        @register("injectee30")
        class Injectee(Component):
            template = ""

            def get_template_data(self, args, kwargs, slots, context):
                assert len(provide_cache) == 1

                data = self.inject("my_provide")
                raise ValueError("Oops")
                return {"data": data, "ran": True}

        @register("root")
        class Root(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" another=26 %}
                    {% component "injectee30" / %}
                {% endprovide %}
            """

        _assert_clear_cache()

        with pytest.raises(ValueError, match=re.escape("Oops")):
            Root.render()

        _assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_cache_not_cleaned_while_active(self, components_settings):
        @register("injectee31")
        class Injectee(Component):
            template: types.django_html = """
                <div>{{ value }}</div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                data = self.inject("my_provide")
                return {"value": data.value}

        @register("root")
        class Root(Component):
            template: types.django_html = """
                <div>{{ content|safe }}</div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                # Nested synchronous rendering triggers GC between components.
                nested_template = Template(
                    """
                    {% load component_tags %}
                    {% for i in "xxxxxxxxxx" %}
                        {% provide "my_provide" value="hello" %}
                            {% component "injectee31" %}{% endcomponent %}
                            {% component "injectee31" %}{% endcomponent %}
                            {% component "injectee31" %}{% endcomponent %}
                        {% endprovide %}
                    {% endfor %}
                """
                )
                content = nested_template.render(Context({}))
                return {"content": content}

        _assert_clear_cache()

        rendered = Root.render()

        # 10 iterations * 3 components = 30 occurrences
        assert rendered.count(">hello</div>") == 30
        _assert_clear_cache()
