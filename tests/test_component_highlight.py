from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.extensions.debug_highlight import COLORS, apply_component_highlight
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


def _prepare_template() -> Template:
    @register("inner")
    class InnerComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div class="inner">
                <div>
                    1: {% slot "content" default / %}
                </div>
                <div>
                    2: {% slot "content" default / %}
                </div>
            </div>
        """

    @register("outer")
    class OuterComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div class="outer">
                {% component "inner" %}
                    {{ content }}
                {% endcomponent %}
            </div>
        """

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "content": kwargs["content"],
            }

    template_str: types.django_html = """
        {% load component_tags %}
        {% for item in items %}
            <div class="item">
                {% component "outer" content=item / %}
            </div>
        {% endfor %}
    """
    template = Template(template_str)
    return template


@djc_test
class TestComponentHighlight:
    def test_component_highlight_fn(self):
        # Test component highlighting
        test_html = "<div>Test content</div>"
        component_name = "TestComponent"
        result = apply_component_highlight("component", test_html, component_name)

        # Check that the output contains the component name
        assert component_name in result
        # Check that the output contains the original HTML
        assert test_html in result
        # Check that the component colors are used
        assert COLORS["component"].text_color in result
        assert COLORS["component"].border_color in result

    def test_slot_highlight_fn(self):
        # Test slot highlighting
        test_html = "<span>Slot content</span>"
        slot_name = "content-slot"
        result = apply_component_highlight("slot", test_html, slot_name)

        # Check that the output contains the slot name
        assert slot_name in result
        # Check that the output contains the original HTML
        assert test_html in result
        # Check that the slot colors are used
        assert COLORS["slot"].text_color in result
        assert COLORS["slot"].border_color in result

    @djc_test(
        components_settings={
            "extensions_defaults": {
                "debug_highlight": {"highlight_components": True},
            },
        },
    )
    def test_component_highlight_extension(self):
        template = _prepare_template()
        rendered = template.render(Context({"items": [1, 2]}))

        expected = """
            <div class="item">
                <style>
                    .component-highlight-a1bc45::before {
                        content: "outer (ca1bc3f): ";
                        font-weight: bold;
                        color: #2f14bb;
                    }
                </style>
                <div class="component-highlight-a1bc45" style="border: 1px solid blue">
                    <div class="outer" data-djc-id-ca1bc3f="">
                        <style>
                            .component-highlight-a1bc44::before {
                                content: "inner (ca1bc41): ";
                                font-weight: bold;
                                color: #2f14bb;
                            }
                        </style>
                        <div class="component-highlight-a1bc44" style="border: 1px solid blue">
                            <div class="inner" data-djc-id-ca1bc41="">
                                <div>
                                    1: 1
                                </div>
                                <div>
                                    2: 1
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="item">
                <style>
                    .component-highlight-a1bc49::before {
                        content: "outer (ca1bc46): ";
                        font-weight: bold;
                        color: #2f14bb;
                    }
                </style>
                <div class="component-highlight-a1bc49" style="border: 1px solid blue">
                    <div class="outer" data-djc-id-ca1bc46="">
                        <style>
                            .component-highlight-a1bc48::before {
                                content: "inner (ca1bc47): ";
                                font-weight: bold;
                                color: #2f14bb;
                            }
                        </style>
                        <div class="component-highlight-a1bc48" style="border: 1px solid blue">
                            <div class="inner" data-djc-id-ca1bc47="">
                                <div>
                                    1: 2
                                </div>
                                <div>
                                    2: 2
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
        assertHTMLEqual(rendered, expected)

    # TODO_v1 - Remove this test once we've removed the `debug_highlight_components` setting.
    @djc_test(components_settings={"debug_highlight_components": True})
    def test_component_highlight_extension__legacy(self):
        template = _prepare_template()
        rendered = template.render(Context({"items": [1, 2]}))

        expected = """
            <div class="item">
                <style>
                    .component-highlight-a1bc45::before {
                        content: "outer (ca1bc3f): ";
                        font-weight: bold;
                        color: #2f14bb;
                    }
                </style>
                <div class="component-highlight-a1bc45" style="border: 1px solid blue">
                    <div class="outer" data-djc-id-ca1bc3f="">
                        <style>
                            .component-highlight-a1bc44::before {
                                content: "inner (ca1bc41): ";
                                font-weight: bold;
                                color: #2f14bb;
                            }
                        </style>
                        <div class="component-highlight-a1bc44" style="border: 1px solid blue">
                            <div class="inner" data-djc-id-ca1bc41="">
                                <div>
                                    1: 1
                                </div>
                                <div>
                                    2: 1
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="item">
                <style>
                    .component-highlight-a1bc49::before {
                        content: "outer (ca1bc46): ";
                        font-weight: bold;
                        color: #2f14bb;
                    }
                </style>
                <div class="component-highlight-a1bc49" style="border: 1px solid blue">
                    <div class="outer" data-djc-id-ca1bc46="">
                        <style>
                            .component-highlight-a1bc48::before {
                                content: "inner (ca1bc47): ";
                                font-weight: bold;
                                color: #2f14bb;
                            }
                        </style>
                        <div class="component-highlight-a1bc48" style="border: 1px solid blue">
                            <div class="inner" data-djc-id-ca1bc47="">
                                <div>
                                    1: 2
                                </div>
                                <div>
                                    2: 2
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
        assertHTMLEqual(rendered, expected)

    @djc_test(
        components_settings={
            "extensions_defaults": {
                "debug_highlight": {"highlight_slots": True},
            },
        },
    )
    def test_slot_highlight_extension(self):
        template = _prepare_template()
        rendered = template.render(Context({"items": [1, 2]}))

        expected = """
            <div class="item">
                <div class="outer" data-djc-id-ca1bc3f="">
                    <div class="inner" data-djc-id-ca1bc41="">
                        <div>
                            1:
                            <style>
                                .slot-highlight-a1bc44::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc44" style="border: 1px solid #e40c0c">
                                1
                            </div>
                        </div>
                        <div>
                            2:
                            <style>
                                .slot-highlight-a1bc45::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc45" style="border: 1px solid #e40c0c">
                                1
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="item">
                <div class="outer" data-djc-id-ca1bc46="">
                    <div class="inner" data-djc-id-ca1bc47="">
                        <div>
                            1:
                            <style>
                                .slot-highlight-a1bc48::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc48" style="border: 1px solid #e40c0c">
                                2
                            </div>
                        </div>
                        <div>
                            2:
                            <style>
                                .slot-highlight-a1bc49::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc49" style="border: 1px solid #e40c0c">
                                2
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
        assertHTMLEqual(rendered, expected)

    # TODO_v1 - Remove this test once we've removed the `debug_highlight_slots` setting.
    @djc_test(components_settings={"debug_highlight_slots": True})
    def test_slot_highlight_extension__legacy(self):
        template = _prepare_template()
        rendered = template.render(Context({"items": [1, 2]}))

        expected = """
            <div class="item">
                <div class="outer" data-djc-id-ca1bc3f="">
                    <div class="inner" data-djc-id-ca1bc41="">
                        <div>
                            1:
                            <style>
                                .slot-highlight-a1bc44::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc44" style="border: 1px solid #e40c0c">
                                1
                            </div>
                        </div>
                        <div>
                            2:
                            <style>
                                .slot-highlight-a1bc45::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc45" style="border: 1px solid #e40c0c">
                                1
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="item">
                <div class="outer" data-djc-id-ca1bc46="">
                    <div class="inner" data-djc-id-ca1bc47="">
                        <div>
                            1:
                            <style>
                                .slot-highlight-a1bc48::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc48" style="border: 1px solid #e40c0c">
                                2
                            </div>
                        </div>
                        <div>
                            2:
                            <style>
                                .slot-highlight-a1bc49::before {
                                    content: "InnerComponent - content: ";
                                    font-weight: bold;
                                    color: #bb1414;
                                }
                            </style>
                            <div class="slot-highlight-a1bc49" style="border: 1px solid #e40c0c">
                                2
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """
        assertHTMLEqual(rendered, expected)

    def test_highlight_on_component_class(self):
        @register("inner")
        class InnerComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="inner">
                    <div>
                        1: {% slot "content" default / %}
                    </div>
                    <div>
                        2: {% slot "content" default / %}
                    </div>
                </div>
            """

            class DebugHighlight:
                highlight_components = True
                highlight_slots = True

        template = Template(
            """
            {% load component_tags %}
            {% component "inner" %}
                {{ content }}
            {% endcomponent %}
        """,
        )
        rendered = template.render(Context({"content": "Hello, world!"}))

        expected = """
            <style>
                .component-highlight-a1bc44::before {
                    content: "inner (ca1bc3f): ";
                    font-weight: bold;
                    color: #2f14bb;
                }
            </style>
            <div class="component-highlight-a1bc44" style="border: 1px solid blue">
                <div class="inner" data-djc-id-ca1bc3f="">
                    <div>
                        1:
                        <style>
                            .slot-highlight-a1bc42::before {
                                content: "InnerComponent - content: ";
                                font-weight: bold;
                                color: #bb1414;
                            }
                        </style>
                        <div class="slot-highlight-a1bc42" style="border: 1px solid #e40c0c">
                            Hello, world!
                        </div>
                    </div>
                    <div>
                        2:
                        <style>
                            .slot-highlight-a1bc43::before {
                                content: "InnerComponent - content: ";
                                font-weight: bold;
                                color: #bb1414;
                            }
                        </style>
                        <div class="slot-highlight-a1bc43" style="border: 1px solid #e40c0c">
                            Hello, world!
                        </div>
                    </div>
                </div>
            </div>
        """
        assertHTMLEqual(rendered, expected)
