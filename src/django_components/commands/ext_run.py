from typing import Any, List, Optional, Type

from django_components.extension import extensions
from django_components.util.command import ComponentCommand


# Scope the extension-specific commands to the extension name, so users call these commands like:
# `python manage.py components ext run <extension> <command>`
#
# We achieve that by creating temporary `ComponentCommand` subclasses for each extension. E.g.
# ```python
# class ExtCommand(ComponentCommand):
#     name = "my_ext"
#     help = "Run commands added by the 'my_ext' extension."
#     subcommands = [
#         ...commands
#     ]
# ```
def _gen_subcommands() -> List[Type[ComponentCommand]]:
    commands: List[Type[ComponentCommand]] = []
    for extension in extensions.extensions:
        ExtCommand = type(
            "ExtCommand",
            (ComponentCommand,),
            {
                "name": extension.name,
                "help": f"Run commands added by the '{extension.name}' extension.",
                "subcommands": extension.commands,
            },
        )

        commands.append(ExtCommand)

    return commands


# This descriptor generates the list of subcommands of the `components ext run` command dynamically when accessed.
# This is because this list depends on the settings and extensions. In tests, the settings and available extensions
# may change between each test case. So we have to ensure we access the latest settings when accessing this property.
#
# NOTE: This is possible, because Django sets up the project and settings BEFORE the commands are loaded.
class SubcommandsDescriptor:
    def __get__(self, obj: Any, objtype: Optional[Type] = None) -> List[Type[ComponentCommand]]:
        # This will be called when accessing ExtRunCommand.subcommands
        # or instance.subcommands
        return _gen_subcommands()


class ExtRunCommand(ComponentCommand):
    """
    Run a command added by an [extension](../../concepts/advanced/extensions).

    Each extension can add its own commands, which will be available to run with this command.

    For example, if you define and install the following extension:

    ```python
    from django_components import ComponentCommand, ComponentExtension

    class HelloCommand(ComponentCommand):
        name = "hello"
        help = "Say hello"
        def handle(self, *args, **kwargs):
            print("Hello, world!")

    class MyExt(ComponentExtension):
        name = "my_ext"
        commands = [HelloCommand]
    ```

    You can run the `hello` command with:

    ```bash
    python manage.py components ext run my_ext hello
    ```

    You can also define arguments for the command, which will be passed to the command's `handle` method.

    ```python
    from django_components import CommandArg, ComponentCommand, ComponentExtension

    class HelloCommand(ComponentCommand):
        name = "hello"
        help = "Say hello"
        arguments = [
            CommandArg(name="name", help="The name to say hello to"),
            CommandArg(name=["--shout", "-s"], action="store_true"),
        ]

        def handle(self, name: str, *args, **kwargs):
            shout = kwargs.get("shout", False)
            msg = f"Hello, {name}!"
            if shout:
                msg = msg.upper()
            print(msg)
    ```

    You can run the command with:

    ```bash
    python manage.py components ext run my_ext hello --name John --shout
    ```

    !!! note

        Command arguments and options are based on Python's `argparse` module.

        For more information, see the [argparse documentation](https://docs.python.org/3/library/argparse.html).
    """

    name = "run"
    help = "Run a command added by an extension."
    subcommands = SubcommandsDescriptor()  # type: ignore
