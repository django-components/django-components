from django.template import Context
from django.template.base import Template, Token, TokenType
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.util.template_parser import parse_template

from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


def token2tuple(token: Token):
    return (
        token.token_type,
        token.contents,
        (token.position[0], token.position[1]),
        token.lineno,
    )


@djc_test
class TestTemplateParser:
    def test_template_text(self):
        tokens = parse_template("Hello world")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.TEXT, "Hello world", (0, 11), 1),
        ]

        assert token_tuples == expected_tokens

    def test_template_variable(self):
        tokens = parse_template("Hello {{ name }}")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.TEXT, "Hello ", (0, 6), 1),
            (TokenType.VAR, "name", (6, 16), 1),
        ]

        assert token_tuples == expected_tokens

    # NOTE(Juro): IMO this should be a TemplateSyntaxError, but Django doesn't raise it
    def test_template_variable_unterminated(self):
        tokens = parse_template("Hello {{ name")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.TEXT, "Hello {{ name", (0, 13), 1),
        ]

        assert token_tuples == expected_tokens

    def test_template_tag(self):
        tokens = parse_template("{% component 'my_comp' key=val %}")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.BLOCK, "component 'my_comp' key=val", (0, 33), 1),
        ]

        assert token_tuples == expected_tokens

    # NOTE(Juro): IMO this should be a TemplateSyntaxError, but Django doesn't raise it
    def test_template_tag_unterminated(self):
        tokens = parse_template("{% if true")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.TEXT, "{% if true", (0, 10), 1),
        ]

        assert token_tuples == expected_tokens

    def test_template_comment(self):
        tokens = parse_template("Hello{# this is a comment #}World")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.TEXT, "Hello", (0, 5), 1),
            (TokenType.COMMENT, "this is a comment", (5, 28), 1),
            (TokenType.TEXT, "World", (28, 33), 1),
        ]

        assert token_tuples == expected_tokens

    # NOTE(Juro): IMO this should be a TemplateSyntaxError, but Django doesn't raise it
    def test_template_comment_unterminated(self):
        tokens = parse_template("{# comment")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.TEXT, "{# comment", (0, 10), 1),
        ]

        assert token_tuples == expected_tokens

    def test_template_verbatim(self):
        tokens = parse_template(
            """{% verbatim %}
                {{ this_is_not_a_var }}
                {% this_is_not_a_tag %}
            {% endverbatim %}"""
        )

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.BLOCK, "verbatim", (0, 14), 1),
            (TokenType.TEXT, "\n                ", (14, 31), 1),
            (TokenType.TEXT, "{{ this_is_not_a_var }}", (31, 54), 2),
            (TokenType.TEXT, "\n                ", (54, 71), 2),
            (TokenType.TEXT, "{% this_is_not_a_tag %}", (71, 94), 3),
            (TokenType.TEXT, "\n            ", (94, 107), 3),
            (TokenType.BLOCK, "endverbatim", (107, 124), 4),
        ]

        assert token_tuples == expected_tokens

    def test_template_verbatim_with_name(self):
        tokens = parse_template(
            """{% verbatim myblock %}
                {{ this_is_not_a_var }}
                {% verbatim %}
                {% endverbatim %}
                {% endverbatim blockname %}
            {% endverbatim myblock %}"""
        )

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.BLOCK, "verbatim myblock", (0, 22), 1),
            (TokenType.TEXT, "\n                ", (22, 39), 1),
            (TokenType.TEXT, "{{ this_is_not_a_var }}", (39, 62), 2),
            (TokenType.TEXT, "\n                ", (62, 79), 2),
            (TokenType.TEXT, "{% verbatim %}", (79, 93), 3),
            (TokenType.TEXT, "\n                ", (93, 110), 3),
            (TokenType.TEXT, "{% endverbatim %}", (110, 127), 4),
            (TokenType.TEXT, "\n                ", (127, 144), 4),
            (TokenType.TEXT, "{% endverbatim blockname %}", (144, 171), 5),
            (TokenType.TEXT, "\n            ", (171, 184), 5),
            (TokenType.BLOCK, "endverbatim myblock", (184, 209), 6),
        ]

        assert token_tuples == expected_tokens

    def test_template_nested_tags(self):
        tokens = parse_template("""{% component 'test' "{% lorem var_a w %}" %}""")

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.BLOCK, "component 'test' \"{% lorem var_a w %}\"", (0, 44), 1),
        ]

        assert token_tuples == expected_tokens

    def test_brackets_and_percent_in_text(self):
        tokens = parse_template('{% component \'test\' \'"\' "{%}" bool_var="{% noop is_active %}" / %}')

        token_tuples = [token2tuple(token) for token in tokens]

        expected_tokens = [
            (TokenType.BLOCK, 'component \'test\' \'"\' "{%}" bool_var="{% noop is_active %}" /', (0, 66), 1),
        ]

        assert token_tuples == expected_tokens

    def test_template_mixed(self):
        tokens = parse_template(
            """Hello {{ name }}
            {# greeting #}
            {% if show_greeting %}
                <h1>Welcome!</h1>
                {% component 'test' key="{% lorem var_a w %}" %}
                    {% verbatim %}
                        {% endcomponent %}
                    {% endverbatim %}
                {% endcomponent %}
            {% endif %}"""
        )

        token_tuples = [token2tuple(token) for token in tokens]
        expected_tokens = [
            (TokenType.TEXT, "Hello ", (0, 6), 1),
            (TokenType.VAR, "name", (6, 16), 1),
            (TokenType.TEXT, "\n            ", (16, 29), 1),
            (TokenType.COMMENT, "greeting", (29, 43), 2),
            (TokenType.TEXT, "\n            ", (43, 56), 2),
            (TokenType.BLOCK, "if show_greeting", (56, 78), 3),
            (TokenType.TEXT, "\n                <h1>Welcome!</h1>\n                ", (78, 129), 3),
            (TokenType.BLOCK, "component 'test' key=\"{% lorem var_a w %}\"", (129, 177), 5),
            (TokenType.TEXT, "\n                    ", (177, 198), 5),
            (TokenType.BLOCK, "verbatim", (198, 212), 6),
            (TokenType.TEXT, "\n                        ", (212, 237), 6),
            (TokenType.TEXT, "{% endcomponent %}", (237, 255), 7),
            (TokenType.TEXT, "\n                    ", (255, 276), 7),
            (TokenType.BLOCK, "endverbatim", (276, 293), 8),
            (TokenType.TEXT, "\n                ", (293, 310), 8),
            (TokenType.BLOCK, "endcomponent", (310, 328), 9),
            (TokenType.TEXT, "\n            ", (328, 341), 9),
            (TokenType.BLOCK, "endif", (341, 352), 10),
        ]

        assert token_tuples == expected_tokens

    # Check that a template that contains `{% %}` inside of a component tag is parsed correctly
    def test_component_mixed(self):
        @register("test")
        class Test(Component):
            template: types.django_html = """
                {% load component_tags %}
                Var: {{ var }}
                Slot: {% slot "content" default / %}
            """

            def get_context_data(self, var: str) -> dict:
                return {"var": var}

        template_str: types.django_html = """
            {% load component_tags %}
            <div>
                Hello {{ name }}
                {# greeting #}
                {% if show_greeting %}
                    <h1>Welcome!</h1>
                    {% component 'test' var="{% lorem var_a w %}" %}
                        {% verbatim %}
                            {% endcomponent %}
                        {% endverbatim %}
                    {% endcomponent %}
                {% endif %}
            </div>
        """
        template = Template(template_str)
        rendered = template.render(Context({"name": "John", "show_greeting": True, "var_a": 2}))

        assertHTMLEqual(
            rendered,
            """
            <div>
                Hello John
                <h1>Welcome!</h1>
                Var: lorem ipsum
                Slot: {% endcomponent %}
            </div>
            """,
        )
