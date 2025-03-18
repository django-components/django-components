from io import StringIO
from textwrap import dedent
from unittest.mock import patch

from django.core.management import call_command

from django_components import Component
from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestComponentListCommand:
    def test_list_default(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list")
        output = out.getvalue()

        assert output.strip() == dedent(
            """
            full_name                                                                                  path                                       
            ======================================================================================================================================
            django_components.components.dynamic.DynamicComponent                                      src/django_components/components/dynamic.py
            tests.test_command_list.TestComponentListCommand.test_list_default.<locals>.TestComponent  tests/test_command_list.py
            """
        ).strip()

    def test_list_all(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list", "--all")
        output = out.getvalue()

        assert output.strip() == dedent(
            """
            name              full_name                                                                              path                                       
            ====================================================================================================================================================
            DynamicComponent  django_components.components.dynamic.DynamicComponent                                  src/django_components/components/dynamic.py
            TestComponent     tests.test_command_list.TestComponentListCommand.test_list_all.<locals>.TestComponent  tests/test_command_list.py
            """
        ).strip()

    def test_list_specific_columns(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list", "--columns", "name,full_name")
        output = out.getvalue()

        assert output.strip() == dedent(
            """
            name              full_name                                                                                         
            ====================================================================================================================
            DynamicComponent  django_components.components.dynamic.DynamicComponent                                             
            TestComponent     tests.test_command_list.TestComponentListCommand.test_list_specific_columns.<locals>.TestComponent
            """
        ).strip()

    def test_list_simple(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list", "--simple")
        output = out.getvalue()

        assert output.strip() == dedent(
            """
            django_components.components.dynamic.DynamicComponent                                     src/django_components/components/dynamic.py
            tests.test_command_list.TestComponentListCommand.test_list_simple.<locals>.TestComponent  tests/test_command_list.py
            """
        ).strip()
