from django_components.commands.create import CreateCommand
from django_components.commands.ext import ExtCommand
from django_components.commands.upgrade import UpgradeCommand
from django_components.util.command import ComponentCommand


# TODO_V3 - This command should be called standalone as "components":
#           `python -m components start <name>`
#           `components start <name>`
class ComponentsRootCommand(ComponentCommand):
    """
    The entrypoint for the "components" commands.

    ```bash
    python manage.py components start <name>
    python manage.py components upgrade <name>
    python manage.py components ext list
    python manage.py components ext run <extension> <command>
    ```
    """

    name = "components"
    help = "The entrypoint for the 'components' commands."

    subcommands = [
        CreateCommand,
        UpgradeCommand,
        ExtCommand,
    ]
