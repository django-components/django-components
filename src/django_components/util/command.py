import sys
from argparse import Action, ArgumentParser
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Protocol, Sequence, Type, Union

if TYPE_CHECKING:
    from argparse import _ArgumentGroup, _FormatterClass

#############################
# Argparse typing
#############################

CommandLiteralAction = Literal[
    "append", "append_const", "count", "extend", "store", "store_const", "store_true", "store_false", "version"
]
"""
The basic type of action to be taken when this argument is encountered at the command line.

This is a subset of the values for `action` in
[`ArgumentParser.add_argument()`](https://docs.python.org/3/library/argparse.html#the-add-argument-method).
"""


@dataclass
class CommandArg:
    """
    Define a single positional argument or an option for a command.

    Fields on this class correspond to the arguments for
    [`ArgumentParser.add_argument()`](https://docs.python.org/3/library/argparse.html#the-add-argument-method)
    """  # noqa: E501

    name_or_flags: Union[str, Sequence[str]]
    """Either a name or a list of option strings, e.g. 'foo' or '-f', '--foo'."""
    action: Optional[Union[CommandLiteralAction, Action]] = None
    """The basic type of action to be taken when this argument is encountered at the command line."""
    nargs: Optional[Union[int, Literal["*", "+", "?"]]] = None
    """The number of command-line arguments that should be consumed."""
    const: Any = None
    """A constant value required by some action and nargs selections."""
    default: Any = None
    """
    The value produced if the argument is absent from the command line and if it is absent from the namespace object.
    """
    type: Optional[Union[Type, Callable[[str], Any]]] = None
    """The type to which the command-line argument should be converted."""
    choices: Optional[Sequence[Any]] = None
    """A sequence of the allowable values for the argument."""
    required: Optional[bool] = None
    """Whether or not the command-line option may be omitted (optionals only)."""
    help: Optional[str] = None
    """A brief description of what the argument does."""
    metavar: Optional[str] = None
    """A name for the argument in usage messages."""
    dest: Optional[str] = None
    """The name of the attribute to be added to the object returned by parse_args()."""
    version: Optional[str] = None
    """
    The version string to be added to the object returned by parse_args().

    MUST be used with `action='version'`.

    See https://docs.python.org/3/library/argparse.html#action
    """

    # NOTE: Support for deprecated was added in Python 3.13
    # See https://docs.python.org/3/library/argparse.html#deprecated
    deprecated: Optional[bool] = None
    """
    Whether or not use of the argument is deprecated.

    NOTE: This is supported only in Python 3.13+
    """

    def asdict(self) -> dict:
        """Convert the dataclass to a dictionary, stripping out fields with `None` values"""
        return _remove_none_values(asdict(self))


@dataclass
class CommandArgGroup:
    """
    Define a group of arguments for a command.

    Fields on this class correspond to the arguments for
    [`ArgumentParser.add_argument_group()`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument_group)
    """  # noqa: E501

    title: Optional[str] = None
    """
    Title for the argument group in help output; by default “positional arguments” if description is provided,
    otherwise uses title for positional arguments.
    """
    description: Optional[str] = None
    """
    Description for the argument group in help output, by default None
    """
    arguments: Sequence[CommandArg] = ()

    def asdict(self) -> dict:
        """Convert the dataclass to a dictionary, stripping out fields with `None` values"""
        return _remove_none_values(asdict(self))


@dataclass
class CommandSubcommand:
    """
    Define a subcommand for a command.

    Fields on this class correspond to the arguments for
    [`ArgumentParser.add_subparsers.add_parser()`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_subparsers)
    """  # noqa: E501

    title: Optional[str] = None
    """
    Title for the sub-parser group in help output; by default “subcommands” if description is provided,
    otherwise uses title for positional arguments.
    """
    description: Optional[str] = None
    """
    Description for the sub-parser group in help output, by default `None`.
    """
    prog: Optional[str] = None
    """
    Usage information that will be displayed with sub-command help, by default the name of the program
    and any positional arguments before the subparser argument.
    """
    parser_class: Optional[Type[ArgumentParser]] = None
    """
    Class which will be used to create sub-parser instances, by default the class of
    the current parser (e.g. `ArgumentParser`).
    """
    action: Optional[Union[CommandLiteralAction, Action]] = None
    """
    The basic type of action to be taken when this argument is encountered at the command line.
    """
    dest: Optional[str] = None
    """
    Name of the attribute under which sub-command name will be stored; by default `None`
    and no value is stored.
    """
    required: Optional[bool] = None
    """
    Whether or not a subcommand must be provided, by default `False` (added in 3.7)
    """
    help: Optional[str] = None
    """
    Help for sub-parser group in help output, by default `None`.
    """
    metavar: Optional[str] = None
    """
    String presenting available subcommands in help; by default it is None and
    presents subcommands in form `{cmd1, cmd2, ..}`.
    """

    def asdict(self) -> dict:
        """Convert the dataclass to a dictionary, stripping out fields with `None` values"""
        return _remove_none_values(asdict(self))


@dataclass
class CommandParserInput:
    """
    Typing for the input to the
    [`ArgumentParser`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser)
    constructor.
    """

    prog: Optional[str] = None
    """The name of the program (default: `os.path.basename(sys.argv[0])`)"""
    usage: Optional[str] = None
    """The string describing the program usage (default: generated from arguments added to parser)"""
    description: Optional[str] = None
    """Text to display before the argument help (by default, no text)"""
    epilog: Optional[str] = None
    """Text to display after the argument help (by default, no text)"""
    parents: Optional[Sequence[ArgumentParser]] = None
    """A list of ArgumentParser objects whose arguments should also be included"""
    formatter_class: Optional[Type["_FormatterClass"]] = None
    """A class for customizing the help output"""
    prefix_chars: Optional[str] = None
    """The set of characters that prefix optional arguments (default: ‘-‘)"""
    fromfile_prefix_chars: Optional[str] = None
    """The set of characters that prefix files from which additional arguments should be read (default: `None`)"""
    argument_default: Optional[Any] = None
    """The global default value for arguments (default: `None`)"""
    conflict_handler: Optional[str] = None
    """The strategy for resolving conflicting optionals (usually unnecessary)"""
    add_help: Optional[bool] = None
    """Add a -h/--help option to the parser (default: `True`)"""
    allow_abbrev: Optional[bool] = None
    """Allows long options to be abbreviated if the abbreviation is unambiguous. (default: `True`)"""
    exit_on_error: Optional[bool] = None
    """Determines whether or not ArgumentParser exits with error info when an error occurs. (default: `True`)"""

    def asdict(self) -> dict:
        """Convert the dataclass to a dictionary, stripping out fields with `None` values"""
        return _remove_none_values(asdict(self))


#############################
# Command logic
#############################


class CommandHandler(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> None: ...  # noqa: E704


class ComponentCommand:
    """
    Definition of a CLI command.

    This class is based on Python's [`argparse`](https://docs.python.org/3/library/argparse.html)
    module and Django's [`BaseCommand`](https://docs.djangoproject.com/en/5.1/howto/custom-management-commands/)
    class. `ComponentCommand` allows you to define:

    - Command name, description, and help text
    - Arguments and options (e.g. `--name John`)
    - Group arguments (see [argparse groups](https://docs.python.org/3/library/argparse.html#argument-groups))
    - Subcommands (e.g. `components ext run my_ext hello`)
    - Handler behavior

    Each extension can add its own commands, which will be available to run with `components ext run`.

    Extensions use the `ComponentCommand` class to define their commands.

    For example, if you define and install the following extension:

    ```python
    from django_components ComponentCommand, ComponentExtension

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

    name: str
    """The name of the command - this is what is used to call the command"""
    help: Optional[str] = None
    """The help text for the command"""
    arguments: Sequence[Union[CommandArg, CommandArgGroup]] = ()
    """argparse arguments for the command"""
    subcommands: Sequence[Type["ComponentCommand"]] = ()
    """Subcommands for the command"""

    handle: Optional[CommandHandler] = None
    """
    The function that is called when the command is run. If `None`, the command will
    print the help message.
    """

    parser_input: Optional[CommandParserInput] = None
    """
    The input to use when creating the `ArgumentParser` for this command. If `None`,
    the default values will be used.
    """
    subparser_input: Optional[CommandSubcommand] = None
    """
    The input to use when this command is a subcommand installed with `add_subparser()`.
    If `None`, the default values will be used.
    """


def setup_parser_from_command(command: Type[ComponentCommand]) -> ArgumentParser:
    """
    Create an `ArgumentParser` instance from a `ComponentCommand`.

    The `ArgumentParser` will:

    - Set help message and command name
    - Add arguments to the parser
    - Add subcommands recursively
    """
    parser_kwargs = {}
    if hasattr(command, "parser_input") and command.parser_input:
        parser_kwargs = command.parser_input.asdict()

    # NOTE: Command name is always present
    parser_kwargs["prog"] = command.name
    if command.help is not None:
        parser_kwargs["description"] = command.help

    parser = ArgumentParser(**parser_kwargs)

    _setup_parser_from_command(parser, command)
    return parser


# Recursively setup the parser and its subcommands
def _setup_parser_from_command(
    parser: ArgumentParser,
    command: Union[Type[ComponentCommand], Type[ComponentCommand]],
) -> ArgumentParser:
    # Attach the command to the data returned by `parser.parse_args()`, so we know
    # which command was matched.
    parser.set_defaults(_command=command(), _parser=parser)

    # Apply arguments to the parser. Arguments may be defined as a group.
    for arg in command.arguments:
        if isinstance(arg, CommandArgGroup):
            group_data = arg.asdict()
            group_args: List[Dict] = group_data.pop("arguments")
            arg_group = parser.add_argument_group(**group_data)
            for group_arg in group_args:
                # NOTE: Seems that dataclass's `asdict()` calls `asdict()` also on the
                # nested dataclass fields. Thus we need to apply `_remove_none_values()`
                # to the nested dataclass fields.
                group_arg = _remove_none_values(group_arg)

                _setup_command_arg(arg_group, group_arg)
        else:
            _setup_command_arg(parser, arg.asdict())

    # Add subcommands to the parser
    if command.subcommands:
        subparsers = parser.add_subparsers(title="subcommands")
        for subcommand in command.subcommands:
            subparser_data: Dict[str, Any] = {}
            if getattr(subcommand, "subparser_input", None) and subcommand.subparser_input:
                subparser_data = subcommand.subparser_input.asdict()

            subparser_data["name"] = subcommand.name
            if subcommand.help:
                subparser_data["help"] = subcommand.help
                subparser_data["description"] = subcommand.help

            subparser = subparsers.add_parser(**subparser_data)
            _setup_parser_from_command(subparser, subcommand)

    return parser


def _setup_command_arg(parser: Union[ArgumentParser, "_ArgumentGroup"], arg: dict) -> None:
    # NOTE: Support for deprecated was added in Python 3.13
    # See https://docs.python.org/3/library/argparse.html#deprecated
    if sys.version_info < (3, 13) and "deprecated" in arg:
        raise ValueError("'deprecated' command argument requires Python 3.13+")

    name_or_flags = arg.pop("name_or_flags")
    if isinstance(name_or_flags, str):
        name_or_flags = [name_or_flags]
    parser.add_argument(*name_or_flags, **arg)


def _remove_none_values(data: dict) -> dict:
    new_data = {}
    for key, val in data.items():
        if val is not None:
            new_data[key] = val
    return new_data


def style_success(message: str) -> str:
    """Style the message with green text"""
    return f"\033[92m{message}\033[0m"  # Green text


def style_warning(message: str) -> str:
    """Style the message with yellow text"""
    return f"\033[93m{message}\033[0m"  # Yellow text
