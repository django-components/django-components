import re

import pytest
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.tag_formatter import ShorthandComponentFormatter

from django_components.testing import djc_test
from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config({"autodiscover": False})


class MultiwordStartTagFormatter(ShorthandComponentFormatter):
    def start_tag(self, name):
        return f"{name} comp"


class MultiwordBlockEndTagFormatter(ShorthandComponentFormatter):
    def end_tag(self, name):
        return f"end {name}"


class SlashEndTagFormatter(ShorthandComponentFormatter):
    def end_tag(self, name):
        return f"/{name}"


# Create a TagFormatter class to validate the public interface
def create_validator_tag_formatter(tag_name: str):
    class ValidatorTagFormatter(ShorthandComponentFormatter):
        def start_tag(self, name):
            assert name == tag_name
            return super().start_tag(name)

        def end_tag(self, name):
            assert name == tag_name
            return super().end_tag(name)

        def parse(self, tokens):
            assert isinstance(tokens, list)
            assert tokens[0] == tag_name
            return super().parse(tokens)

    return ValidatorTagFormatter()


@djc_test
class TestComponentTag:
    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_formatter_default_inline(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" / %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

    @djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
    def test_formatter_default_block(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" %}
                OVERRIDEN!
            {% endcomponent %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": "django_components.component_formatter",
        },
    )
    def test_formatter_component_inline(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" / %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": "django_components.component_formatter",
        },
    )
    def test_formatter_component_block(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% component "simple" %}
                OVERRIDEN!
            {% endcomponent %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": "django_components.component_shorthand_formatter",
        },
    )
    def test_formatter_shorthand_inline(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple / %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": "django_components.component_shorthand_formatter",
        },
    )
    def test_formatter_shorthand_block(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple %}
                OVERRIDEN!
            {% endsimple %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": SlashEndTagFormatter(),
        },
    )
    def test_forward_slash_in_end_tag(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple %}
                OVERRIDEN!
            {% /simple %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                OVERRIDEN!
            </div>
            hello2
            """,
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": ShorthandComponentFormatter(),
        },
    )
    def test_import_formatter_by_value(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple %}
                OVERRIDEN!
            {% endsimple %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            <div data-djc-id-a1bc3f>
                OVERRIDEN!
            </div>
            """,
        )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": MultiwordStartTagFormatter(),
        },
    )
    def test_raises_on_invalid_start_tag(self, components_settings):
        with pytest.raises(
            ValueError,
            match=re.escape("MultiwordStartTagFormatter returned an invalid tag for start_tag: 'simple comp'"),
        ):

            @register("simple")
            class SimpleComponent(Component):
                template = """{% load component_tags %}"""

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": MultiwordBlockEndTagFormatter(),
        },
    )
    def test_raises_on_invalid_block_end_tag(self, components_settings):
        with pytest.raises(
            ValueError,
            match=re.escape("MultiwordBlockEndTagFormatter returned an invalid tag for end_tag: 'end simple'"),
        ):

            @register("simple")
            class SimpleComponent(Component):
                template: types.django_html = """
                    {% load component_tags %}
                    <div>
                        {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                    </div>
                """

            Template(
                """
                {% load component_tags %}
                {% simple %}
                    OVERRIDEN!
                {% bar %}
            """
            )

    @djc_test(
        parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR,
        components_settings={
            "tag_formatter": create_validator_tag_formatter("simple"),
        },
    )
    def test_method_args(self, components_settings):
        @register("simple")
        class SimpleComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                hello1
                <div>
                    {% slot "content" default %} SLOT_DEFAULT {% endslot %}
                </div>
                hello2
            """

        template = Template(
            """
            {% load component_tags %}
            {% simple / %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc3f>
                SLOT_DEFAULT
            </div>
            hello2
            """,
        )

        template = Template(
            """
            {% load component_tags %}
            {% simple %}
                OVERRIDEN!
            {% endsimple %}
        """
        )
        rendered = template.render(Context())
        assertHTMLEqual(
            rendered,
            """
            hello1
            <div data-djc-id-a1bc42>
                OVERRIDEN!
            </div>
            hello2
            """,
        )
