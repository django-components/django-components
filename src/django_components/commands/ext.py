from django_components.commands.ext_list import ExtListCommand
from django_components.commands.ext_run import ExtRunCommand
from django_components.util.command import ComponentCommand


class ExtCommand(ComponentCommand):
    """
    Run extension commands.

    ```bash
    python manage.py components ext list
    python manage.py components ext run <extension> <command>
    ```
    """

    name = "ext"
    help = "Run extension commands."

    subcommands = [
        ExtListCommand,
        ExtRunCommand,
    ]
