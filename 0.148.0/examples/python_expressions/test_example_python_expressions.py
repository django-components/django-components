from dataclasses import dataclass

import pytest
from django.template import Context, Template

from django_components import registry, types
from django_components.testing import djc_test


@dataclass
class User:
    username: str
    status: str
    role: str
    points: int
    is_admin: bool = False

    def __post_init__(self):
        # Derive is_admin from role if not explicitly set to True
        if not self.is_admin:
            self.is_admin = self.role == "admin"


@dataclass
class Item:
    title: str


def _import_components():
    from docs.examples.python_expressions.component import Button, SearchInput, UserCard  # noqa: PLC0415

    registry.register("button", Button)
    registry.register("user_card", UserCard)
    registry.register("search_input", SearchInput)


@pytest.mark.django_db
@djc_test
class TestPythonExpressions:
    def test_negating_boolean(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "button" text="Submit" disabled=(not editable) / %}
        """
        template = Template(template_str)

        # When editable is False, disabled should be True
        rendered = template.render(Context({"editable": False}))
        assert "disabled" in rendered

        # When editable is True, disabled should be False
        rendered = template.render(Context({"editable": True}))
        assert "disabled" not in rendered

    def test_conditional_expression(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "button" text="Delete" variant=(my_user.is_admin and 'danger' or 'primary') / %}
        """
        template = Template(template_str)

        # When user is admin, variant should be 'danger'
        user_admin = User(username="admin", status="active", role="admin", points=100, is_admin=True)
        rendered = template.render(Context({"my_user": user_admin}))
        assert "bg-red-600" in rendered

        # When user is not admin, variant should be 'primary'
        user_regular = User(username="user", status="active", role="user", points=50, is_admin=False)
        rendered = template.render(Context({"my_user": user_regular}))
        assert "bg-blue-600" in rendered

    def test_method_calls(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "button" text=(name.upper()) / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"name": "hello"}))
        assert "HELLO" in rendered

    def test_complex_expressions(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "user_card"
                username=my_user.username
                is_active=(my_user.status == 'active')
                is_admin=(my_user.role == 'admin')
                score=(my_user.points + bonus_points)
            / %}
        """
        template = Template(template_str)

        my_user = User(
            username="johndoe",
            status="active",
            role="admin",
            points=100,
        )

        rendered = template.render(
            Context(
                {
                    "my_user": my_user,
                    "bonus_points": 25,
                }
            )
        )

        assert "johndoe" in rendered
        assert "125" in rendered  # 100 + 25
        assert "Admin" in rendered

    def test_list_operations(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "button"
                text=(items[0].title if items else 'No Items')
                disabled=(items_len == 0)
            / %}
        """
        template = Template(template_str)

        # With items
        items = [Item(title="First Item")]
        rendered = template.render(Context({"items": items, "items_len": len(items)}))
        assert "First Item" in rendered
        assert "disabled" not in rendered

        # Without items
        rendered = template.render(Context({"items": [], "items_len": 0}))
        assert "No Items" in rendered
        assert "disabled" in rendered

    def test_dictionary_operations(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "button"
                text=(config.get('button_text', 'Submit'))
                variant=(config.get('button_style', 'primary'))
            / %}
        """
        template = Template(template_str)

        # With config
        rendered = template.render(Context({"config": {"button_style": "secondary"}}))
        assert "bg-gray-200" in rendered
        assert "Submit" in rendered

        # Without config (default)
        rendered = template.render(Context({"config": {"button_text": "Save"}}))
        assert "bg-blue-600" in rendered
        assert "Save" in rendered
        assert "Submit" not in rendered
