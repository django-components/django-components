from typing import Any

from django_components.extension import extensions
from django_components.util.command import CommandArg, ComponentCommand


class ExtListCommand(ComponentCommand):
    """
    List all extensions.

    ```bash
    python manage.py components ext list
    ```

    Prints the list of installed extensions:

    ```txt
    Installed extensions:
    view
    my_extension
    ```

    If you need to omit the title in order to programmatically post-process the output,
    you can use the `--verbosity` (or `-v`) flag:

    ```bash
    python manage.py components ext list -v 0
    ```

    Which prints just:

    ```txt
    view
    my_extension
    ```
    """

    name = "list"
    help = "List all extensions."

    arguments = [
        CommandArg(
            ["-v", "--verbosity"],
            default=1,
            type=int,
            choices=[0, 1],
            help=("Verbosity level; 0=minimal output, 1=normal output"),
        ),
    ]

    def handle(self, *args: Any, **kwargs: Any) -> None:
        if kwargs["verbosity"] > 0:
            print("Installed extensions:")
        for extension in extensions.extensions:
            print(extension.name)
