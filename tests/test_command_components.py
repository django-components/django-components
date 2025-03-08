import sys
from io import StringIO
from textwrap import dedent
from unittest.mock import patch

from django.core.management import call_command
from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


# NOTE: Argparse changed how the optional args are displayed in Python 3.11+
if sys.version_info >= (3, 11):
    OPTIONS_TITLE = "options"
else:
    OPTIONS_TITLE = "optional arguments"


@djc_test
class TestComponentCommand:
    def test_root_command(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components")
        output = out.getvalue()
        assert output == dedent(f"""
            usage: components [-h] [--version] [-v {{0,1,2,3}}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback]
                              [--no-color] [--force-color] [--skip-checks]
                              {{create,upgrade,ext}} ...

            The entrypoint for the 'components' commands.

            {OPTIONS_TITLE}:
              -h, --help            show this help message and exit
              --version             Show program's version number and exit.
              -v {{0,1,2,3}}, --verbosity {{0,1,2,3}}
                                    Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output
              --settings SETTINGS   The Python path to a settings module, e.g. "myproject.settings.main". If this isn't provided,
                                    the DJANGO_SETTINGS_MODULE environment variable will be used.
              --pythonpath PYTHONPATH
                                    A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".
              --traceback           Raise on CommandError exceptions.
              --no-color            Don't colorize the command output.
              --force-color         Force colorization of the command output.
              --skip-checks         Skip system checks.

            subcommands:
              {{create,upgrade,ext}}
                create              Create a new django component.
                upgrade             Upgrade django components syntax from '{{% component_block ... %}}' to '{{% component ... %}}'.
                ext                 Run extension commands.
        """).lstrip()  # noqa: E501
