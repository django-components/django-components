from typing import Any

from django_components.commands.list import ListCommand
from django_components.extension import extensions


class ExtListCommand(ListCommand):
    """
    List all extensions.

    ```bash
    python manage.py components ext list
    ```

    Prints the list of installed extensions:

    ```txt
    name
    ==============
    view
    my_extension
    ```

    To specify which columns to show, use the `--columns` flag:

    ```bash
    python manage.py components ext list --columns name
    ```

    Which prints:

    ```txt
    name
    ==============
    view
    my_extension
    ```

    To print out all columns, use the `--all` flag:

    ```bash
    python manage.py components ext list --all
    ```

    If you need to omit the title in order to programmatically post-process the output,
    you can use the `--simple` (or `-s`) flag:

    ```bash
    python manage.py components ext list --simple
    ```

    Which prints just:

    ```txt
    view
    my_extension
    ```
    """

    name = "list"
    help = "List all extensions."

    columns = ("name",)
    default_columns = ("name",)

    def get_data(self) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for extension in extensions.extensions:
            data.append(
                {
                    "name": extension.name,
                },
            )
        return data
