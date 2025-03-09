from argparse import ArgumentParser
from typing import Any, Optional, Type

import django
from django.core.management.base import BaseCommand as DjangoCommand

from django_components.util.command import (
    CommandArg,
    ComponentCommand,
    _setup_command_arg,
    setup_parser_from_command,
)

# Django command arguments added to all commands
# NOTE: Many of these MUST be present for the command to work with Django
DJANGO_COMMAND_ARGS = [
    CommandArg(
        "--version",
        action="version",
        version=django.get_version(),
        help="Show program's version number and exit.",
    ),
    CommandArg(
        ["-v", "--verbosity"],
        default=1,
        type=int,
        choices=[0, 1, 2, 3],
        help=("Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, " "3=very verbose output"),
    ),
    CommandArg(
        "--settings",
        help=(
            "The Python path to a settings module, e.g. "
            '"myproject.settings.main". If this isn\'t provided, the '
            "DJANGO_SETTINGS_MODULE environment variable will be used."
        ),
    ),
    CommandArg(
        "--pythonpath",
        help=("A directory to add to the Python path, e.g. " '"/home/djangoprojects/myproject".'),
    ),
    CommandArg(
        "--traceback",
        action="store_true",
        help="Raise on CommandError exceptions.",
    ),
    CommandArg(
        "--no-color",
        action="store_true",
        help="Don't colorize the command output.",
    ),
    CommandArg(
        "--force-color",
        action="store_true",
        help="Force colorization of the command output.",
    ),
    CommandArg(
        "--skip-checks",
        action="store_true",
        help="Skip system checks.",
    ),
]


def load_as_django_command(command: Type[ComponentCommand]) -> Type[DjangoCommand]:
    """
    Create a Django `Command` class from a `ComponentCommand` class.

    The created class can be used as a Django command by placing it in
    the `management/commands/` module.

    ```python
    # management/commands/mycommand.py
    from django_components.compat.django import load_as_django_command
    from myapp.commands.mycommand import MyCommand

    # NOTE: MUST be assigned to a variable named `Command`
    Command = load_as_django_command(MyCommand)
    ```
    """

    # Define a Command class that delegates to our command_class
    class Command(DjangoCommand):
        help = command.help

        def __init__(self) -> None:
            self._command = command()

        def create_parser(self, prog_name: str, subcommand: str, **kwargs: Any) -> ArgumentParser:
            parser = setup_parser_from_command(command)
            for arg in DJANGO_COMMAND_ARGS:
                _setup_command_arg(parser, arg.asdict())

            return parser

        # This is the entrypoint for the command - After argparser has resolved the args,
        # this is where we forward the args to the command handler.
        def handle(self, *args: Any, **options: Any) -> None:
            # Case: (Sub)command matched and it HAS handler
            resolved_command: Optional[ComponentCommand] = options.get("_command", None)
            if resolved_command and resolved_command.handle:
                resolved_command.handle(*args, **options)
                return

            # Case: (Sub)command matched and it DOES NOT have handler (e.g. subcommand used for routing)
            cmd_parser: Optional[ArgumentParser] = options.get("_parser", None)
            if cmd_parser:
                cmd_parser.print_help()
                return

            # Case: (Sub)command did not match - Print help for the main command
            self.print_help(self._command.name, "")

    Command.__doc__ = command.__doc__

    return Command
