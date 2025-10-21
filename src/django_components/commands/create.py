import sys
from pathlib import Path
from textwrap import dedent
from typing import Any

from django.conf import settings
from django.core.management.base import CommandError

from django_components.util.command import CommandArg, ComponentCommand, style_success, style_warning


class CreateCommand(ComponentCommand):
    """
    ### Usage

    To use the command, run the following command in your terminal:

    ```bash
    python manage.py components create <name> --path <path> --js <js_filename> --css <css_filename> --template <template_filename> --force --verbose --dry-run
    ```

    Replace `<name>`, `<path>`, `<js_filename>`, `<css_filename>`, and `<template_filename>` with your desired values.

    ### Examples

    Here are some examples of how you can use the command:

    **Creating a Component with Default Settings**

    To create a component with the default settings, you only need to provide the name of the component:

    ```bash
    python manage.py components create my_component
    ```

    This will create a new component named `my_component` in the `components` directory of your Django project. The JavaScript, CSS, and template files will be named `script.js`, `style.css`, and `template.html`, respectively.

    **Creating a Component with Custom Settings**

    You can also create a component with custom settings by providing additional arguments:

    ```bash
    python manage.py components create new_component --path my_components --js my_script.js --css my_style.css --template my_template.html
    ```

    This will create a new component named `new_component` in the `my_components` directory. The JavaScript, CSS, and template files will be named `my_script.js`, `my_style.css`, and `my_template.html`, respectively.

    **Overwriting an Existing Component**

    If you want to overwrite an existing component, you can use the `--force` option:

    ```bash
    python manage.py components create my_component --force
    ```

    This will overwrite the existing `my_component` if it exists.

    **Simulating Component Creation**

    If you want to simulate the creation of a component without actually creating any files, you can use the `--dry-run` option:

    ```bash
    python manage.py components create my_component --dry-run
    ```

    This will simulate the creation of `my_component` without creating any files.
    """  # noqa: E501

    name = "create"
    help = "Create a new django component."

    arguments = (
        CommandArg(
            name_or_flags="name",
            help="The name of the component to create. This is a required argument.",
        ),
        CommandArg(
            name_or_flags="--path",
            help=(
                "The path to the component's directory. This is an optional argument. "
                "If not provided, the command will use the `COMPONENTS.dirs` setting from your Django settings."
            ),
            default=None,
        ),
        CommandArg(
            name_or_flags="--js",
            help="The name of the JavaScript file. This is an optional argument. The default value is `script.js`.",
            default="script.js",
        ),
        CommandArg(
            name_or_flags="--css",
            help="The name of the CSS file. This is an optional argument. The default value is `style.css`.",
            default="style.css",
        ),
        CommandArg(
            name_or_flags="--template",
            help="The name of the template file. This is an optional argument. The default value is `template.html`.",
            default="template.html",
        ),
        CommandArg(
            name_or_flags="--force",
            help="This option allows you to overwrite existing files if they exist. This is an optional argument.",
            action="store_true",
        ),
        CommandArg(
            name_or_flags="--verbose",
            help=(
                "This option allows the command to print additional information during component creation. "
                "This is an optional argument."
            ),
            action="store_true",
        ),
        CommandArg(
            name_or_flags="--dry-run",
            help=(
                "This option allows you to simulate component creation without actually creating any files. "
                "This is an optional argument. The default value is `False`."
            ),
            action="store_true",
        ),
    )

    def handle(self, *_args: Any, **kwargs: Any) -> None:
        name = kwargs["name"]

        if not name:
            raise CommandError("You must specify a component name")

        # TODO_V3 - BASE_DIR should be taken from Components' settings
        base_dir = getattr(settings, "BASE_DIR", None)

        path = kwargs["path"]
        js_filename = kwargs["js"]
        css_filename = kwargs["css"]
        template_filename = kwargs["template"]
        force = kwargs["force"]
        verbose = kwargs["verbose"]
        dry_run = kwargs["dry_run"]

        if path:
            component_path = Path(path) / name
        elif base_dir:
            component_path = Path(base_dir) / "components" / name
        else:
            raise CommandError("You must specify a path or set BASE_DIR in your django settings")

        if component_path.exists():
            if not force:
                raise CommandError(
                    f'The component "{name}" already exists at {component_path}. Use --force to overwrite.',
                )

            if verbose:
                msg = f'The component "{name}" already exists at {component_path}. Overwriting...'
            else:
                msg = f'The component "{name}" already exists. Overwriting...'

            sys.stdout.write(style_warning(msg) + "\n")

        if not dry_run:
            component_path.mkdir(parents=True, exist_ok=force)

            js_path = component_path / js_filename
            with js_path.open("w") as f:
                script_content = dedent(
                    f"""
                    window.addEventListener('load', (event) => {{
                        console.log("{name} component is fully loaded");
                    }});
                """,
                )
                f.write(script_content.strip())

            css_path = component_path / css_filename
            with css_path.open("w") as f:
                style_content = dedent(
                    f"""
                    .component-{name} {{
                        background: red;
                    }}
                """,
                )
                f.write(style_content.strip())

            template_path = component_path / template_filename
            with template_path.open("w") as f:
                template_content = dedent(
                    f"""
                    <div class="component-{name}">
                        Hello from {name} component!
                        <br>
                        This is {{ param }} context value.
                    </div>
                """,
                )
                f.write(template_content.strip())

            py_path = component_path / f"{name}.py"
            with py_path.open("w") as f:
                py_content = dedent(
                    f"""
                    from django_components import Component, register

                    @register("{name}")
                    class {name.capitalize()}(Component):
                        template_file = "{template_filename}"
                        js_file = "{js_filename}"
                        css_file = "{css_filename}"

                        class Kwargs:
                            param: str = "sample value"

                        def get_template_data(self, args, kwargs: Kwargs, slots, context):
                            return {{
                                "param": kwargs.param,
                            }}
                """,
                )
                f.write(py_content.strip())

        if verbose:
            msg = f"Successfully created {name} component at {component_path}"
        else:
            msg = f"Successfully created {name} component"
        sys.stdout.write(style_success(msg) + "\n")
