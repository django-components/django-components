import sys
from io import StringIO
from textwrap import dedent
from unittest.mock import patch

from django.core.management import call_command
from django_components import CommandArg, CommandArgGroup, ComponentCommand, ComponentExtension
from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})

# NOTE: Argparse changed how the optional args are displayed in Python 3.11+
if sys.version_info >= (3, 10):
    OPTIONS_TITLE = "options"
else:
    OPTIONS_TITLE = "optional arguments"


class EmptyExtension(ComponentExtension):
    name = "empty"


class DummyCommand(ComponentCommand):
    name = "dummy_cmd"
    help = "Dummy command description."

    arguments = [
        CommandArg(
            name_or_flags="--foo",
            help="Foo description.",
        ),
        CommandArgGroup(
            title="group bar",
            description="Group description.",
            arguments=[
                CommandArg(
                    name_or_flags="--bar",
                    help="Bar description.",
                ),
                CommandArg(
                    name_or_flags="--baz",
                    help="Baz description.",
                ),
            ],
        ),
    ]

    def handle(self, *args, **kwargs):
        kwargs.pop("_command")
        kwargs.pop("_parser")
        sorted_kwargs = dict(sorted(kwargs.items()))
        print(f"DummyCommand.handle: args={args}, kwargs={sorted_kwargs}")


class DummyExtension(ComponentExtension):
    name = "dummy"

    commands = [
        DummyCommand,
    ]


@djc_test
class TestExtensionsCommand:
    def test_root_command(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext")
        output = out.getvalue()

        assert (
            output
            == dedent(
                f"""
                usage: components ext [-h] {{list,run}} ...

                Run extension commands.

                {OPTIONS_TITLE}:
                  -h, --help  show this help message and exit

                subcommands:
                  {{list,run}}
                    list      List all extensions.
                    run       Run a command added by an extension.
                """
            ).lstrip()
        )


@djc_test
class TestExtensionsListCommand:
    def test_list_default_extensions(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "list")
        output = out.getvalue()

        assert output.strip() == "name    \n========\ncache   \ndefaults\nview"

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_list_extra_extensions(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "list")
        output = out.getvalue()

        assert output.strip() == "name    \n========\ncache   \ndefaults\nview    \nempty   \ndummy"

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_list_all(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "list", "--all")
        output = out.getvalue()

        assert output.strip() == "name    \n========\ncache   \ndefaults\nview    \nempty   \ndummy"

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_list_specific_columns(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "list", "--columns", "name")
        output = out.getvalue()

        assert output.strip() == "name    \n========\ncache   \ndefaults\nview    \nempty   \ndummy"

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_list_simple(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "list", "--simple")
        output = out.getvalue()

        assert output.strip() == "cache   \ndefaults\nview    \nempty   \ndummy"


@djc_test
class TestExtensionsRunCommand:
    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_run_command_root(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "run")
        output = out.getvalue()

        assert (
            output
            == dedent(
                f"""
                usage: components ext run [-h] {{cache,defaults,view,empty,dummy}} ...

                Run a command added by an extension.

                {OPTIONS_TITLE}:
                  -h, --help            show this help message and exit

                subcommands:
                  {{cache,defaults,view,empty,dummy}}
                    cache               Run commands added by the 'cache' extension.
                    defaults            Run commands added by the 'defaults' extension.
                    view                Run commands added by the 'view' extension.
                    empty               Run commands added by the 'empty' extension.
                    dummy               Run commands added by the 'dummy' extension.
                """
            ).lstrip()
        )

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_run_command_ext_empty(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "run", "empty")
        output = out.getvalue()

        assert (
            output
            == dedent(
                f"""
                usage: components ext run empty [-h]

                Run commands added by the 'empty' extension.

                {OPTIONS_TITLE}:
                  -h, --help  show this help message and exit
                """
            ).lstrip()
        )

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_run_command_ext_with_commands(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "run", "dummy")
        output = out.getvalue()

        assert (
            output
            == dedent(
                f"""
                usage: components ext run dummy [-h] {{dummy_cmd}} ...

                Run commands added by the 'dummy' extension.

                {OPTIONS_TITLE}:
                  -h, --help   show this help message and exit

                subcommands:
                  {{dummy_cmd}}
                    dummy_cmd  Dummy command description.
                """
            ).lstrip()
        )

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_run_command_ext_command(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components", "ext", "run", "dummy", "dummy_cmd")
        output = out.getvalue()

        # NOTE: The dummy command prints out the kwargs, which is what we check for here
        assert (
            output
            == dedent(
                """
                DummyCommand.handle: args=(), kwargs={'bar': None, 'baz': None, 'foo': None, 'force_color': False, 'no_color': False, 'pythonpath': None, 'settings': None, 'skip_checks': True, 'traceback': False, 'verbosity': 1}
                """  # noqa: E501
            ).lstrip()
        )

    @djc_test(
        components_settings={"extensions": [EmptyExtension, DummyExtension]},
    )
    def test_prints_error_if_command_not_found(self):
        out = StringIO()
        with patch("sys.stderr", new=out):
            try:
                call_command("components", "ext", "run", "dummy", "dummy_cmd_not_found")
            except SystemExit:
                output = out.getvalue()

        assert "invalid choice: 'dummy_cmd_not_found'" in output
