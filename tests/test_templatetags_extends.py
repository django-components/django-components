"""Catch-all for tests that use template tags and don't fit other files"""

from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, registry, types

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


def gen_slotted_component():
    class SlottedComponent(Component):
        template_file = "slotted_template.html"

    return SlottedComponent


def gen_blocked_and_slotted_component():
    class BlockedAndSlottedComponent(Component):
        template_file = "blocked_and_slotted_template.html"

    return BlockedAndSlottedComponent


def gen_component_inside_include():
    class ComponentInsideInclude(Component):
        template: types.django_html = """<div>Hello</div>"""

        class Media:
            css = "style.css"
            js = "script.js"

    return ComponentInsideInclude


#######################
# TESTS
#######################


@djc_test
class TestExtendsCompat:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_double_extends_on_main_template_and_component_one_component(self, components_settings):
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            <div data-djc-id-ca1bc40>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-ca1bc40>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_double_extends_on_main_template_and_component_two_identical_components(self, components_settings):
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            <div data-djc-id-ca1bc42>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-ca1bc42>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                            <div data-djc-id-ca1bc46>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-ca1bc46>
                                <header>SLOT OVERRIDEN 2</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_double_extends_on_main_template_and_component_two_different_components_same_parent(self, components_settings):  # noqa: E501
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        @register("second_extended_component")
        class _SecondExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template_str: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "second_extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
                {% endcomponent %}
            {% endblock %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            <div data-djc-id-ca1bc42>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-ca1bc42>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                            <div data-djc-id-ca1bc46>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-ca1bc46>
                                <header>SLOT OVERRIDEN 2</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_double_extends_on_main_template_and_component_two_different_components_different_parent(self, components_settings):  # noqa: E501
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        @register("second_extended_component")
        class _SecondExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template_2.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "second_extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            <div data-djc-id-ca1bc42>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-ca1bc42>
                                <header>SLOT OVERRIDEN</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                            <div data-djc-id-ca1bc46>BLOCK OVERRIDEN</div>
                            <custom-template data-djc-id-ca1bc46>
                                <header>SLOT OVERRIDEN 2</header>
                                <main>Default main</main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_extends_on_component_one_component(self, components_settings):
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html lang="en">
            <body>
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
            </body>
            </html>
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <div data-djc-id-ca1bc40>BLOCK OVERRIDEN</div>
                    <custom-template data-djc-id-ca1bc40>
                        <header>SLOT OVERRIDEN</header>
                        <main>Default main</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_extends_on_component_two_component(self, components_settings):
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html lang="en">
            <body>
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN
                    {% endfill %}
                {% endcomponent %}
                {% component "extended_component" %}
                    {% fill "header" %}
                        SLOT OVERRIDEN 2
                    {% endfill %}
                {% endcomponent %}
            </body>
            </html>
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <div data-djc-id-ca1bc42>BLOCK OVERRIDEN</div>
                    <custom-template data-djc-id-ca1bc42>
                        <header>SLOT OVERRIDEN</header>
                        <main>Default main</main>
                        <footer>Default footer</footer>
                    </custom-template>
                    <div data-djc-id-ca1bc46>BLOCK OVERRIDEN</div>
                    <custom-template data-djc-id-ca1bc46>
                        <header>SLOT OVERRIDEN 2</header>
                        <main>Default main</main>
                        <footer>Default footer</footer>
                    </custom-template>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_double_extends_on_main_template_and_nested_component(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template: types.django_html = """
                {% extends "blocked_and_slotted_template.html" %}
                {% block before_custom %}
                    <div>BLOCK OVERRIDEN</div>
                {% endblock %}
            """

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% component "slotted_component" %}
                    {% fill "main" %}
                        {% component "extended_component" %}
                            {% fill "header" %}
                                SLOT OVERRIDEN
                            {% endfill %}
                        {% endcomponent %}
                    {% endfill %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            <custom-template data-djc-id-ca1bc42>
                                <header>Default header</header>
                                <main>
                                    <div data-djc-id-ca1bc49>BLOCK OVERRIDEN</div>
                                    <custom-template data-djc-id-ca1bc49>
                                        <header>SLOT OVERRIDEN</header>
                                        <main>Default main</main>
                                        <footer>Default footer</footer>
                                    </custom-template>
                                </main>
                                <footer>Default footer</footer>
                            </custom-template>
                        </div>
                    </main>
                </body>
            </html>
        """

        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_double_extends_on_main_template_and_nested_component_and_include(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())
        registry.register("blocked_and_slotted_component", gen_blocked_and_slotted_component())

        @register("extended_component")
        class _ExtendedComponent(Component):
            template_file = "included.html"

        template: types.django_html = """
            {% extends 'block.html' %}
            {% load component_tags %}
            {% block body %}
                {% include 'included.html' %}
                {% component "extended_component" / %}
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            Variable: <strong></strong>
                            Variable: <strong data-djc-id-ca1bc3f></strong>
                        </div>
                    </main>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

        # second rendering after cache built
        rendered_2 = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

        expected_2 = """
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <main role="main">
                        <div class='container main-container'>
                            Variable: <strong></strong>
                            Variable: <strong data-djc-id-ca1bc41></strong>
                        </div>
                    </main>
                </body>
            </html>
        """
        assertHTMLEqual(rendered_2, expected_2)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slots_inside_extends(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        @register("slot_inside_extends")
        class SlotInsideExtendsComponent(Component):
            template: types.django_html = """
                {% extends "block_in_slot_in_component.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_extends" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc40 lang="en">
            <body>
                <custom-template data-djc-id-ca1bc45>
                    <header></header>
                    <main>BODY_FROM_FILL</main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slots_inside_include(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        @register("slot_inside_include")
        class SlotInsideIncludeComponent(Component):
            template: types.django_html = """
                {% include "block_in_slot_in_component.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_include" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc40 lang="en">
            <body>
                <custom-template data-djc-id-ca1bc45>
                    <header></header>
                    <main>BODY_FROM_FILL</main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    # In this case, `{% include %}` is NOT nested inside a `{% component %}` tag.
    # We need to ensure that the component inside the `{% include %}` is rendered as if with deps_strategy="ignore",
    # so the parent template decides how to render the JS/CSS.
    # See https://github.com/django-components/django-components/issues/1296
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_with_media_inside_include(self, components_settings):
        registry.register("test_component", gen_component_inside_include())

        template: types.django_html = """
            {% load component_tags %}
            <body>
                <outer>
                    {% include "component_inside_include_sub.html" %}
                </outer>
            </body>
        """

        rendered_raw = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected_raw = """
            <body>
                <outer>
                    <div data-djc-id-ca1bc3f>Hello</div>
                </outer>
            </body>
        """
        assertHTMLEqual(rendered_raw, expected_raw)

        template_obj = Template(template)
        context = Context()
        rendered = template_obj.render(context)

        # NOTE: It's important that the <script> tags are rendered outside of <div> and <outer> tags,
        # because that tells us that the JS/CSS is rendered by the parent template, not the component
        # inside the include.
        expected = """
            <body>
                <outer>
                    <div data-djc-id-ca1bc41>Hello</div>
                </outer>
                <script src="django_components/django_components.min.js"></script>
                <script type="application/json" data-djc>{"loadedCssUrls": ["c3R5bGUuY3Nz"],
                    "loadedJsUrls": ["c2NyaXB0Lmpz"],
                    "toLoadCssTags": [],
                    "toLoadJsTags": []}</script>
                <script src="script.js"></script>
            </body>
        """
        assertHTMLEqual(rendered, expected)

    # In this case, because `{% include %}` is rendered inside a `{% component %}` tag,
    # then the component inside the `{% include %}` knows it's inside another component.
    # So it's always rendered as if with deps_strategy="ignore".
    # See https://github.com/django-components/django-components/issues/1296
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_with_media_inside_include_inside_component(self, components_settings):
        registry.register("test_component", gen_component_inside_include())

        @register("component_inside_include")
        class CompInsideIncludeComponent(Component):
            template: types.django_html = """
                <body>
                    <outer>
                        {% include "component_inside_include_sub.html" %}
                    </outer>
                </body>
            """

        template: types.django_html = """
            {% load component_tags %}
            <html>
                {% component "component_inside_include" / %}
            </html>
        """

        rendered_raw = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected_raw = """
            <html>
                <body data-djc-id-ca1bc3f>
                    <outer>
                        <div data-djc-id-ca1bc41>Hello</div>
                    </outer>
                </body>
            </html>
        """
        assertHTMLEqual(rendered_raw, expected_raw)

        template_obj = Template(template)
        context = Context()
        rendered = template_obj.render(context)
        expected = """
            <html>
                <body data-djc-id-ca1bc43>
                    <outer>
                        <div data-djc-id-ca1bc45>Hello</div>
                    </outer>
                    <script src="django_components/django_components.min.js"></script>
                    <script type="application/json" data-djc>{"loadedCssUrls": ["c3R5bGUuY3Nz"],
                        "loadedJsUrls": ["c2NyaXB0Lmpz"],
                        "toLoadCssTags": [],
                        "toLoadJsTags": []}</script>
                    <script src="script.js"></script>
                </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_inside_block(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())
        template: types.django_html = """
            {% extends "block.html" %}
            {% load component_tags %}
            {% block body %}
            {% component "slotted_component" %}
                {% fill "header" %}{% endfill %}
                {% fill "main" %}
                TEST
                {% endfill %}
                {% fill "footer" %}{% endfill %}
            {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <main role="main">
                    <div class='container main-container'>
                        <custom-template data-djc-id-ca1bc42>
                            <header></header>
                            <main>TEST</main>
                            <footer></footer>
                        </custom-template>
                    </div>
                </main>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_block_inside_component(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        template: types.django_html = """
            {% extends "block_in_component.html" %}
            {% block body %}
            <div>
                58 giraffes and 2 pantaloons
            </div>
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template data-djc-id-ca1bc41>
                    <header></header>
                    <main>
                        <div> 58 giraffes and 2 pantaloons </div>
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_block_inside_component_parent(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        @register("block_in_component_parent")
        class BlockInCompParent(Component):
            template_file = "block_in_component_parent.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "block_in_component_parent" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc3f lang="en">
            <body>
                <custom-template data-djc-id-ca1bc43>
                    <header></header>
                    <main>
                        <div> 58 giraffes and 2 pantaloons </div>
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_block_does_not_affect_inside_component(self, components_settings):
        """
        Assert that when we call a component with `{% component %}`, that
        the `{% block %}` will NOT affect the inner component.
        """
        registry.register("slotted_component", gen_slotted_component())

        @register("block_inside_slot_v1")
        class BlockInSlotInComponent(Component):
            template_file = "block_in_slot_in_component.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "block_inside_slot_v1" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
            {% block inner %}
                wow
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc40 lang="en">
            <body>
                <custom-template data-djc-id-ca1bc49>
                    <header></header>
                    <main>BODY_FROM_FILL</main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
            wow
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slot_inside_block__slot_default_block_default(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc3f lang="en">
            <body>
                <custom-template data-djc-id-ca1bc44>
                    <header></header>
                    <main>
                        Helloodiddoo
                        Default inner
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slot_inside_block__slot_default_block_override(self, components_settings):
        registry.clear()
        registry.register("slotted_component", gen_slotted_component())

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
                {% block inner %}
                    INNER BLOCK OVERRIDEN
                {% endblock %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc3f lang="en">
            <body>
                <custom-template data-djc-id-ca1bc44>
                    <header></header>
                    <main>
                        Helloodiddoo
                        INNER BLOCK OVERRIDEN
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slot_inside_block__slot_overriden_block_default(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}
                {% fill "body" %}
                    SLOT OVERRIDEN
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc40 lang="en">
            <body>
                <custom-template data-djc-id-ca1bc45>
                    <header></header>
                    <main>
                        Helloodiddoo
                        SLOT OVERRIDEN
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_slot_inside_block__slot_overriden_block_overriden(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
                {% block inner %}
                    {% load component_tags %}
                    {% slot "new_slot" %}{% endslot %}
                {% endblock %}
                whut
            """

        # NOTE: The "body" fill will NOT show up, because we override the `inner` block
        # with a different slot. But the "new_slot" WILL show up.
        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}
                {% fill "body" %}
                    SLOT_BODY__OVERRIDEN
                {% endfill %}
                {% fill "new_slot" %}
                    SLOT_NEW__OVERRIDEN
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc41 lang="en">
            <body>
                <custom-template data-djc-id-ca1bc47>
                    <header></header>
                    <main>
                        Helloodiddoo
                        SLOT_NEW__OVERRIDEN
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_inject_inside_block(self, components_settings):
        registry.register("slotted_component", gen_slotted_component())

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_template_data(self, args, kwargs, slots, context):
                var = self.inject("block_provide")
                return {"var": var}

        template: types.django_html = """
            {% extends "block_in_component_provide.html" %}
            {% load component_tags %}
            {% block body %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template data-djc-id-ca1bc44>
                    <header></header>
                    <main>
                        <div data-djc-id-ca1bc4b> injected: DepInject(hello='from_block') </div>
                    </main>
                    <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_using_template_file_extends_relative_file(self, components_settings):
        @register("relative_file_component_using_template_file")
        class RelativeFileComponentUsingTemplateFile(Component):
            template_file = "relative_extends.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "relative_file_component_using_template_file" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc3f="" lang="en">
              <body>
                <main role="main">
                  <div class='container main-container'>
                    BLOCK OVERRIDEN
                  </div>
                </main>
              </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_component_using_get_template_name_extends_relative_file(self, components_settings):
        @register("relative_file_component_using_get_template_name")
        class RelativeFileComponentUsingGetTemplateName(Component):
            def get_template_name(self, context):
                return "relative_extends.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "relative_file_component_using_get_template_name" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
        expected = """
            <!DOCTYPE html>
            <html data-djc-id-ca1bc3f="" lang="en">
              <body>
                <main role="main">
                  <div class='container main-container'>
                    BLOCK OVERRIDEN
                  </div>
                </main>
              </body>
            </html>
        """
        assertHTMLEqual(rendered, expected)
