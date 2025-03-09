from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestComponentCommand:
    def test_root_command(self):
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command("components")
        output = out.getvalue()

        # NOTE: The full output is different in CI and locally, because of different whitespace wrapping
        # (probably due to different terminal widths). So we check only for parts of the output.
        #
        # The full expected output is:
        # ```
        # usage: components [-h] [--version] [-v {{0,1,2,3}}] [--settings SETTINGS] [--pythonpath PYTHONPATH]
        #                   [--traceback] [--no-color] [--force-color] [--skip-checks]
        #                   {{create,upgrade,ext}} ...
        #
        # The entrypoint for the 'components' commands.
        #
        # optional arguments:
        #   -h, --help            show this help message and exit
        #   --version             Show program's version number and exit.
        #   -v {{0,1,2,3}}, --verbosity {{0,1,2,3}}
        #                         Verbosity level; 0=minimal output, 1=normal output, 2=verbose output,
        #                         3=very verbose output
        #   --settings SETTINGS   The Python path to a settings module, e.g. "myproject.settings.main". If this
        #                         isn't provided, the DJANGO_SETTINGS_MODULE environment variable will be used.
        #   --pythonpath PYTHONPATH
        #                         A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".
        #   --traceback           Raise on CommandError exceptions.
        #   --no-color            Don't colorize the command output.
        #   --force-color         Force colorization of the command output.
        #   --skip-checks         Skip system checks.
        #
        # subcommands:
        #   {{create,upgrade,ext}}
        #     create              Create a new django component.
        #     upgrade             Upgrade django components syntax from '{{% component_block ... %}}' to
        #                         '{{% component ... %}}'.
        #     ext                 Run extension commands.
        # ```

        assert "usage: components" in output
        assert "The entrypoint for the 'components' commands." in output
        assert "-h, --help            show this help message and exit" in output
        assert "--version             Show program's version number and exit." in output
        assert "-v {0,1,2,3}" in output
        assert "--settings SETTINGS   The Python path to a settings module" in output
        assert "--pythonpath PYTHONPATH" in output
        assert "--traceback           Raise on CommandError exceptions." in output
        assert "--no-color            Don't colorize the command output." in output
        assert "--force-color         Force colorization of the command output." in output
        assert "--skip-checks         Skip system checks." in output
        assert "create              Create a new django component." in output
        assert "upgrade             Upgrade django components syntax" in output
        assert "ext                 Run extension commands." in output
