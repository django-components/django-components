import re
from typing import Any

import pytest
from django.template import Context, Template, TemplateSyntaxError
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.perfutil.provide import provide_cache, provide_references, all_reference_ids

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestProvideTemplateTag:
    def _assert_clear_cache(self):
        assert provide_cache == {}
        assert provide_references == {}
        assert all_reference_ids == set()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_basic(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=1 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41> injected: DepInject(key='hi', another=1) </div>
            """,
        )
        self._assert_clear_cache()

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
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_access_keys_in_python(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> key: {{ key }} </div>
                <div> another: {{ another }} </div>
            """

            def get_context_data(self):
                my_provide = self.inject("my_provide")
                return {
                    "key": my_provide.key,
                    "another": my_provide.another,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=3 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41> key: hi </div>
            <div data-djc-id-a1bc41> another: 3 </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_access_keys_in_django(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> key: {{ my_provide.key }} </div>
                <div> another: {{ my_provide.another }} </div>
            """

            def get_context_data(self):
                my_provide = self.inject("my_provide")
                return {
                    "my_provide": my_provide,
                }

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=4 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41> key: hi </div>
            <div data-djc-id-a1bc41> another: 4 </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_does_not_leak(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=5 %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41> injected: default </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_empty(self, components_settings):
        """Check provide tag with no kwargs"""

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc42> injected: DepInject() </div>
            <div data-djc-id-a1bc43> injected: default </div>
        """,
        )
        self._assert_clear_cache()

    @djc_test(components_settings={"context_behavior": "django"})
    def test_provide_no_inject(self):
        """Check that nothing breaks if we do NOT inject even if some data is provided"""

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div></div>
            """

            def get_context_data(self):
                return {}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=6 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc42></div>
            <div data-djc-id-a1bc43></div>
        """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_single_quotes(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide 'my_provide' key="hi" another=7 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc42> injected: DepInject(key='hi', another=7) </div>
            <div data-djc-id-a1bc43> injected: default </div>
        """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_as_var(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide var_a key="hi" another=8 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(
            Context(
                {
                    "var_a": "my_provide",
                }
            )
        )

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc42> injected: DepInject(key='hi', another=8) </div>
            <div data-djc-id-a1bc43> injected: default </div>
        """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_as_spread(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide ...provide_props %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
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
                }
            )
        )

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc42> injected: DepInject(key='hi', another=9) </div>
            <div data-djc-id-a1bc43> injected: default </div>
        """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_no_name_raises(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide key="hi" another=10 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'provide': missing a required argument: 'name'"),
        ):
            Template(template_str).render(Context({}))

        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_must_be_string_literal(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide my_var key="hi" another=11 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Provide tag received an empty string. Key must be non-empty and a valid identifier"),
        ):
            Template(template_str).render(Context({}))

        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_name_must_be_identifier(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "%heya%" key="hi" another=12 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(TemplateSyntaxError):
            template.render(Context({}))
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_aggregate_dics(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" var1:key="hi" var1:another=13 var2:x="y" %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41> injected: DepInject(var1={'key': 'hi', 'another': 13}, var2={'x': 'y'}) </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_does_not_expose_kwargs_to_context(self, components_settings):
        """Check that `provide` tag doesn't assign the keys to the context like `with` tag does"""

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
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
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_nested_in_provide_same_key(self, components_settings):
        """Check that inner `provide` with same key overshadows outer `provide`"""

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=15 lost=0 %}
                {% provide "my_provide" key="hi1" another=16 new=3 %}
                    {% component "injectee" %}
                    {% endcomponent %}
                {% endprovide %}

                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc45> injected: DepInject(key='hi1', another=16, new=3) </div>
            <div data-djc-id-a1bc46> injected: DepInject(key='hi', another=15, lost=0) </div>
            <div data-djc-id-a1bc47> injected: default </div>
            """,
        )

        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_nested_in_provide_different_key(self, components_settings):
        """Check that `provide` tag with different keys don't affect each other"""

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> first_provide: {{ first_provide|safe }} </div>
                <div> second_provide: {{ second_provide|safe }} </div>
            """

            def get_context_data(self):
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
                    {% component "injectee" %}
                    {% endcomponent %}
                {% endprovide %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc43> first_provide: DepInject(key='hi', another=17, lost=0) </div>
            <div data-djc-id-a1bc43> second_provide: DepInject(key='hi1', another=18, new=3) </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_provide_in_include(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
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
                <div data-djc-id-a1bc41> injected: DepInject(key='hi', another=19) </div>
            </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slot_in_provide(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
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
                {% component "injectee" %}{% endcomponent %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc40 data-djc-id-a1bc44>
                injected: DepInject(key='hi', another=20)
            </div>
            """,
        )
        self._assert_clear_cache()


@djc_test
class TestInject:
    def _assert_clear_cache(self):
        assert provide_cache == {}
        assert provide_references == {}
        assert all_reference_ids == set()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_basic(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("my_provide")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=21 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41> injected: DepInject(key='hi', another=21) </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_missing_key_raises_without_default(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("abc")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(KeyError):
            template.render(Context({}))

        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_missing_key_ok_with_default(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("abc", "default")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc3f> injected: default </div>
            """,
        )
        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_empty_string(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("")
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=22 %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endprovide %}
            {% component "injectee" %}
            {% endcomponent %}
        """
        template = Template(template_str)

        with pytest.raises(KeyError):
            template.render(Context({}))

        self._assert_clear_cache()

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_raises_on_called_outside_get_context_data(self, components_settings):
        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("abc", "default")
                return {"var": var}

        comp = InjectComponent("")
        with pytest.raises(RuntimeError):
            comp.inject("abc", "def")

        self._assert_clear_cache()

    # See https://github.com/django-components/django-components/pull/778
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_in_fill(self, components_settings):
        @register("injectee")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <main>
                    {% slot "content" default / %}
                </main>
            """

            def get_context_data(self):
                data = self.inject("my_provide")
                return {"data": data}

        @register("provider")
        class Provider(Component):
            def get_context_data(self, data: Any) -> Any:
                return {"data": data}

            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" data=data %}
                    {% slot "content" default / %}
                {% endprovide %}
            """

        @register("parent")
        class Parent(Component):
            def get_context_data(self, data: Any) -> Any:
                return {"data": data}

            template: types.django_html = """
                {% load component_tags %}
                {% component "provider" data=data %}
                    {% component "injectee" %}
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
            <div data-djc-id-a1bc3e data-djc-id-a1bc41 data-djc-id-a1bc45 data-djc-id-a1bc49>
                injected: DepInject(key='hi', data=123)
            </div>
            <main data-djc-id-a1bc3e data-djc-id-a1bc41 data-djc-id-a1bc45 data-djc-id-a1bc49>
                456
            </main>
            """,
        )
        self._assert_clear_cache()

    # See https://github.com/django-components/django-components/pull/786
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_in_slot_in_fill(self, components_settings):
        @register("injectee")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <main>
                    {% slot "content" default / %}
                </main>
            """

            def get_context_data(self):
                data = self.inject("my_provide")
                return {"data": data}

        @register("provider")
        class Provider(Component):
            def get_context_data(self, data: Any) -> Any:
                return {"data": data}

            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" data=data %}
                    {% slot "content" default / %}
                {% endprovide %}
            """

        @register("parent")
        class Parent(Component):
            def get_context_data(self, data: Any) -> Any:
                return {"data": data}

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
                    {% component "injectee" / %}
                {% endcomponent %}
            """

        rendered = Root.render()

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc3e data-djc-id-a1bc41 data-djc-id-a1bc44 data-djc-id-a1bc48>
                injected: DepInject(key='hi', data=123)
            </div>
            <main data-djc-id-a1bc3e data-djc-id-a1bc41 data-djc-id-a1bc44 data-djc-id-a1bc48>
            </main>
            """,
        )
        self._assert_clear_cache()


# When there is `{% component %}` that's a descendant of `{% provide %}`,
# then the cache entry is NOT removed as soon as we have rendered the children (nodelist)
# of `{% provide %}`.
#
# Instead, we manage the state ourselves, and remove the cache entry
# when the component rendered is done.
@djc_test
class TestProvideCache:
    def _assert_clear_cache(self):
        assert provide_cache == {}
        assert provide_references == {}
        assert all_reference_ids == set()

    def test_provide_outside_component(self):
        @register("injectee")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <div> Ran: {{ ran }} </div>
            """

            def get_context_data(self):
                assert len(provide_cache) == 1

                data = self.inject("my_provide")
                return {"data": data, "ran": True}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=23 %}
                {% component "injectee" / %}
            {% endprovide %}
        """

        self._assert_clear_cache()

        template = Template(template_str)
        self._assert_clear_cache()

        rendered = template.render(Context({}))

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc41>
                injected: DepInject(key='hi', another=23)
            </div>
            <div data-djc-id-a1bc41>
                Ran: True
            </div>
            """,
        )
        self._assert_clear_cache()

    # Cache should be cleared even if there is an error.
    def test_provide_outside_component_with_error(self):

        @register("injectee")
        class Injectee(Component):
            template = ""

            def get_context_data(self):
                assert len(provide_cache) == 1
                data = self.inject("my_provide")

                raise ValueError("Oops")
                return {"data": data, "ran": True}

        template_str: types.django_html = """
            {% load component_tags %}
            {% provide "my_provide" key="hi" another=24 %}
                {% component "injectee" / %}
            {% endprovide %}
        """

        self._assert_clear_cache()

        template = Template(template_str)
        self._assert_clear_cache()

        with pytest.raises(ValueError, match=re.escape("Oops")):
            template.render(Context({}))

        self._assert_clear_cache()

    def test_provide_inside_component(self):
        @register("injectee")
        class Injectee(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div> injected: {{ data|safe }} </div>
                <div> Ran: {{ ran }} </div>
            """

            def get_context_data(self):
                assert len(provide_cache) == 1

                data = self.inject("my_provide")
                return {"data": data, "ran": True}

        @register("root")
        class Root(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" another=25 %}
                    {% component "injectee" / %}
                {% endprovide %}
            """

        self._assert_clear_cache()

        rendered = Root.render()

        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc3e data-djc-id-a1bc42>
                injected: DepInject(key='hi', another=25)
            </div>
            <div data-djc-id-a1bc3e data-djc-id-a1bc42>
                Ran: True
            </div>
            """,
        )
        self._assert_clear_cache()

    def test_provide_inside_component_with_error(self):
        @register("injectee")
        class Injectee(Component):
            template = ""

            def get_context_data(self):
                assert len(provide_cache) == 1

                data = self.inject("my_provide")
                raise ValueError("Oops")
                return {"data": data, "ran": True}

        @register("root")
        class Root(Component):
            template: types.django_html = """
                {% load component_tags %}
                {% provide "my_provide" key="hi" another=26 %}
                    {% component "injectee" / %}
                {% endprovide %}
            """

        self._assert_clear_cache()

        with pytest.raises(ValueError, match=re.escape("Oops")):
            Root.render()

        self._assert_clear_cache()
