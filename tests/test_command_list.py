import re
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from django_components import Component
from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


# Either back or forward slash
SLASH = r"[\/]"


@djc_test
class TestComponentListCommand:
    def test_list_default(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list")
        output = out.getvalue()

        # TODO
        print("OUTPUT:\n", output)

        # NOTE: When we run all tests, the output is different, as other test files define components
        # outside of the `@djc_test` decorator, and thus they leak into the output. Since this affects also
        # the formatting (how much whitespace there is), regex is used to check for the headers and the expected
        # components.
        #
        # The output should look like this:
        #
        # full_name                                                                                  path
        # ======================================================================================================================================
        # django_components.components.dynamic.DynamicComponent                                      src/django_components/components/dynamic.py
        # tests.test_command_list.TestComponentListCommand.test_list_default.<locals>.TestComponent  tests/test_command_list.py

        # Check first line of output
        assert re.compile(
            # full_name   path
            r"full_name\s+path\s+"
        ).search(output.strip().split("\n")[0])

        # Check that the output contains the built-in component
        assert re.compile(
            # django_components.components.dynamic.DynamicComponent   src/django_components/components/dynamic.py
            # or
            # django_components.components.dynamic.DynamicComponent   .tox/py311/lib/python3.11/site-packages/django_components/components/dynamic.py
            r"django_components\.components\.dynamic\.DynamicComponent\s+[\w\/\.-]+django_components{SLASH}components{SLASH}dynamic\.py".format(
                SLASH=SLASH
            )
        ).search(output)

        # Check that the output contains the test component
        assert re.compile(
            # tests.test_command_list.TestComponentListCommand.test_list_default.<locals>.TestComponent   tests/test_command_list.py
            r"tests\.test_command_list\.TestComponentListCommand\.test_list_default\.<locals>\.TestComponent\s+tests{SLASH}test_command_list\.py".format(
                SLASH=SLASH
            )
        ).search(output)

    def test_list_all(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list", "--all")
        output = out.getvalue()

        # TODO
        print("OUTPUT:\n", output)

        # NOTE: When we run all tests, the output is different, as other test files define components
        # outside of the `@djc_test` decorator, and thus they leak into the output. Since this affects also
        # the formatting (how much whitespace there is), regex is used to check for the headers and the expected
        # components.
        #
        # The output should look like this:
        #
        # name              full_name                                                                              path
        # ====================================================================================================================================================
        # DynamicComponent  django_components.components.dynamic.DynamicComponent                                  src/django_components/components/dynamic.py
        # TestComponent     tests.test_command_list.TestComponentListCommand.test_list_all.<locals>.TestComponent  tests/test_command_list.py

        # Check first line of output
        assert re.compile(
            # name   full_name   path
            r"name\s+full_name\s+path\s+"
        ).search(output.strip().split("\n")[0])

        # Check that the output contains the built-in component
        assert re.compile(
            # DynamicComponent  django_components.components.dynamic.DynamicComponent   src/django_components/components/dynamic.py
            # or
            # DynamicComponent  django_components.components.dynamic.DynamicComponent   .tox/py311/lib/python3.11/site-packages/django_components/components/dynamic.py
            r"DynamicComponent\s+django_components\.components\.dynamic\.DynamicComponent\s+[\w\/\.-]+django_components{SLASH}components{SLASH}dynamic\.py".format(
                SLASH=SLASH
            )
        ).search(output)

        # Check that the output contains the test component
        assert re.compile(
            # TestComponent   tests.test_command_list.TestComponentListCommand.test_list_all.<locals>.TestComponent   tests/test_command_list.py
            r"TestComponent\s+tests\.test_command_list\.TestComponentListCommand\.test_list_all\.<locals>\.TestComponent\s+tests{SLASH}test_command_list\.py".format(
                SLASH=SLASH
            )
        ).search(output)

    def test_list_specific_columns(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list", "--columns", "name,full_name")
        output = out.getvalue()

        # TODO
        print("OUTPUT:\n", output)

        # NOTE: When we run all tests, the output is different, as other test files define components
        # outside of the `@djc_test` decorator, and thus they leak into the output. Since this affects also
        # the formatting (how much whitespace there is), regex is used to check for the headers and the expected
        # components.
        #
        # The output should look like this:
        #
        # name              full_name
        # ====================================================================================================================
        # DynamicComponent  django_components.components.dynamic.DynamicComponent
        # TestComponent     tests.test_command_list.TestComponentListCommand.test_list_specific_columns.<locals>.TestComponent

        # Check first line of output
        assert re.compile(
            # name   full_name
            r"name\s+full_name"
        ).search(output.strip().split("\n")[0])

        # Check that the output contains the built-in component
        assert re.compile(
            # DynamicComponent  django_components.components.dynamic.DynamicComponent
            r"DynamicComponent\s+django_components\.components\.dynamic\.DynamicComponent"
        ).search(output)

        # Check that the output contains the test component
        assert re.compile(
            # TestComponent   tests.test_command_list.TestComponentListCommand.test_list_specific_columns.<locals>.TestComponent
            r"TestComponent\s+tests\.test_command_list\.TestComponentListCommand\.test_list_specific_columns\.<locals>\.TestComponent"
        ).search(output)

    def test_list_simple(self):
        class TestComponent(Component):
            template = ""

        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "list", "--simple")
        output = out.getvalue()

        # TODO
        print("OUTPUT:\n", output)

        # NOTE: When we run all tests, the output is different, as other test files define components
        # outside of the `@djc_test` decorator, and thus they leak into the output. Since this affects also
        # the formatting (how much whitespace there is), regex is used to check for the headers and the expected
        # components.
        #
        # The output should look like this:
        #
        # django_components.components.dynamic.DynamicComponent                                     src/django_components/components/dynamic.py
        # tests.test_command_list.TestComponentListCommand.test_list_simple.<locals>.TestComponent  tests/test_command_list.py

        # Check first line of output is omitted
        assert re.compile(
            # full_name   path
            r"full_name\s+path\s+"
        ).search(output.strip().split("\n")[0]) is None

        # Check that the output contains the built-in component
        assert re.compile(
            # django_components.components.dynamic.DynamicComponent   src/django_components/components/dynamic.py
            # or
            # django_components.components.dynamic.DynamicComponent   .tox/py311/lib/python3.11/site-packages/django_components/components/dynamic.py
            r"django_components\.components\.dynamic\.DynamicComponent\s+[\w\/\.-]+django_components{SLASH}components{SLASH}dynamic\.py".format(
                SLASH=SLASH
            )
        ).search(output)

        # Check that the output contains the test component
        assert re.compile(
            # tests.test_command_list.TestComponentListCommand.test_list_simple.<locals>.TestComponent  tests/test_command_list.py
            r"tests\.test_command_list\.TestComponentListCommand\.test_list_simple\.<locals>\.TestComponent\s+tests{SLASH}test_command_list\.py".format(
                SLASH=SLASH
            )
        ).search(output)
