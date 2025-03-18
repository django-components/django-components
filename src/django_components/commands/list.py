import os
from typing import Any, Dict, List, Optional, Type

from django_components.component import all_components
from django_components.util.command import CommandArg, ComponentCommand
from django_components.util.misc import get_import_path, get_module_info


# This descriptor generates the list of command arguments (e.g. `--all`), such that
# their descriptions are dynamically generated based on the Command class.
class ListArgumentsDescriptor:
    # This will be called when accessing `ListCommand.arguments`
    def __get__(self, obj: Optional["ListCommand"], cls: Type["ListCommand"]) -> List[CommandArg]:
        command = obj or cls
        all_cols = command.columns
        default_cols = command.default_columns

        all_cols_input = ",".join(all_cols)
        all_cols_readable = ", ".join(all_cols)
        default_cols_input = ",".join(default_cols)

        return [
            CommandArg(
                ["--all"],
                action="store_true",
                # Format as e.g. `--columns name,full_name,path`
                help=f"Show all columns. Same as `--columns {all_cols_input}`.",
            ),
            CommandArg(
                ["--columns"],
                help=(
                    f"Comma-separated list of columns to show. Available columns: {all_cols_readable}. "
                    f"Defaults to `--columns {default_cols_input}`."
                ),
            ),
            CommandArg(
                ["-s", "--simple"],
                action="store_true",
                help="Only show table data, without headers. Use this option for generating machine-readable output.",
            ),
        ]


# Common base class for all `list` commands, so they all have the same arguments
# and same formatting.
class ListCommand(ComponentCommand):
    ####################
    # SUBCLASS API
    ####################

    columns: List[str]
    default_columns: List[str]

    def get_data(self) -> List[Dict[str, Any]]:
        return []

    ####################
    # INTERNAL
    ####################

    arguments = ListArgumentsDescriptor()  # type: ignore[assignment]

    def handle(self, *args: Any, **kwargs: Any) -> None:
        """
        This runs when the "list" command is called. This handler delegates to subclasses
        to define how to get the data with the `get_data` method and formats the results
        as an ASCII table.
        """
        if kwargs["all"] and kwargs["columns"]:
            raise ValueError("Cannot use --all and --columns together.")

        if kwargs["all"]:
            columns = self.columns
        elif kwargs["columns"]:
            columns = kwargs["columns"].split(",")
            for column in columns:
                if column not in self.columns:
                    raise ValueError(f"Invalid column: {column}")
        else:
            # Default columns
            columns = self.default_columns

        data = self.get_data()
        include_headers = not kwargs.get("simple", False)

        table = format_as_ascii_table(data, columns, include_headers=include_headers)
        print(table)


def format_as_ascii_table(data: List[Dict[str, Any]], headers: List[str], include_headers: bool = True) -> str:
    """
    Format a list of dictionaries as an ASCII table.

    Example:

    ```python
    data = [
        {"name": "ProjectPage", "full_name": "project.pages.project.ProjectPage", "path": "./project/pages/project"},
        {"name": "ProjectDashboard", "full_name": "project.components.dashboard.ProjectDashboard", "path": "./project/components/dashboard"},
        {"name": "ProjectDashboardAction", "full_name": "project.components.dashboard_action.ProjectDashboardAction", "path": "./project/components/dashboard_action"},
    ]
    headers = ["name", "full_name", "path"]
    print(format_as_ascii_table(data, headers))
    ```

    Which prints:

    ```txt
    name                      full_name                                                     path
    ==================================================================================================
    ProjectPage               project.pages.project.ProjectPage                             ./project/pages/project
    ProjectDashboard          project.components.dashboard.ProjectDashboard                 ./project/components/dashboard
    ProjectDashboardAction    project.components.dashboard_action.ProjectDashboardAction    ./project/components/dashboard_action
    ```
    """  # noqa: E501
    # Calculate the width of each column
    column_widths = {header: len(header) for header in headers}
    for row in data:
        for header in headers:
            row_value = str(row.get(header, ""))
            column_widths[header] = max(column_widths[header], len(row_value))

    # Create the header row
    header_row = "  ".join(f"{header:<{column_widths[header]}}" for header in headers)
    separator = "=" * len(header_row)

    # Create the data rows
    data_rows = []
    for row in data:
        row_values = [str(row.get(header, "")) for header in headers]
        data_row = "  ".join(f"{value:<{column_widths[header]}}" for value, header in zip(row_values, headers))
        data_rows.append(data_row)

    # Combine all parts into the final table
    if include_headers:
        table = "\n".join([header_row, separator] + data_rows)
    else:
        table = "\n".join(data_rows)
    return table


class ComponentListCommand(ListCommand):
    """
    List all components.

    ```bash
    python manage.py components list
    ```

    Prints the list of available components:

    ```txt
    full_name                                                     path
    ==================================================================================================
    project.pages.project.ProjectPage                             ./project/pages/project
    project.components.dashboard.ProjectDashboard                 ./project/components/dashboard
    project.components.dashboard_action.ProjectDashboardAction    ./project/components/dashboard_action
    ```

    To specify which columns to show, use the `--columns` flag:

    ```bash
    python manage.py components list --columns name,full_name,path
    ```

    Which prints:

    ```txt
    name                      full_name                                                     path
    ==================================================================================================
    ProjectPage               project.pages.project.ProjectPage                             ./project/pages/project
    ProjectDashboard          project.components.dashboard.ProjectDashboard                 ./project/components/dashboard
    ProjectDashboardAction    project.components.dashboard_action.ProjectDashboardAction    ./project/components/dashboard_action
    ```

    To print out all columns, use the `--all` flag:

    ```bash
    python manage.py components list --all
    ```
    
    If you need to omit the title in order to programmatically post-process the output,
    you can use the `--simple` (or `-s`) flag:

    ```bash
    python manage.py components list --simple
    ```

    Which prints just:

    ```txt
    ProjectPage               project.pages.project.ProjectPage                             ./project/pages/project
    ProjectDashboard          project.components.dashboard.ProjectDashboard                 ./project/components/dashboard
    ProjectDashboardAction    project.components.dashboard_action.ProjectDashboardAction    ./project/components/dashboard_action
    ```
    """  # noqa: E501
    name = "list"
    help = "List all components created in this project."

    columns = ["name", "full_name", "path"]
    default_columns = ["full_name", "path"]

    def get_data(self) -> List[Dict[str, Any]]:
        components = all_components()
        data: List[Dict[str, Any]] = []
        for component in components:
            full_name = get_import_path(component)
            module, module_name, module_file_path = get_module_info(component)

            # Make paths relative to CWD
            if module_file_path:
                module_file_path = os.path.relpath(module_file_path, os.getcwd())

            data.append(
                {
                    "name": component.__name__,
                    "full_name": full_name,
                    "path": module_file_path,
                }
            )
        return data
