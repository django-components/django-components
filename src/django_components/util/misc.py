import re
import sys
from collections import namedtuple
from collections.abc import Callable, Generator, Iterable
from dataclasses import fields, is_dataclass
from hashlib import md5
from importlib import import_module
from inspect import getmembers
from itertools import chain
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    TypeGuard,
    TypeVar,
    cast,
)
from urllib import parse

from django_components.constants import COMP_ID_PREFIX, UID_LENGTH
from django_components.util.nanoid import generate

if TYPE_CHECKING:
    from django_components.component import Component

T = TypeVar("T")
U = TypeVar("U")


# Based on nanoid implementation from
# https://github.com/puyuan/py-nanoid/tree/99e5b478c450f42d713b6111175886dccf16f156/nanoid
def gen_id() -> str:
    """Generate a unique ID that can be associated with a Node"""
    # Alphabet is only alphanumeric. Compared to the default alphabet used by nanoid,
    # we've omitted `-` and `_`.
    # With this alphabet, at 6 chars, the chance of collision is 1 in 3.3M.
    # See https://zelark.github.io/nano-id-cc/
    return generate(
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        size=UID_LENGTH,
    )


def gen_component_id() -> str:
    """Generate a unique ID for a component instance (e.g. for render_id)."""
    return COMP_ID_PREFIX + gen_id()


def is_str_wrapped_in_quotes(s: str) -> bool:
    return s.startswith(('"', "'")) and s[0] == s[-1] and len(s) >= 2


def snake_to_pascal(name: str) -> str:
    return "".join(word.title() for word in name.split("_"))


def is_identifier(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.isidentifier()


def any_regex_match(string: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(string) is not None for p in patterns)


def no_regex_match(string: str, patterns: list[re.Pattern]) -> bool:
    return all(p.search(string) is None for p in patterns)


# See https://stackoverflow.com/a/2020083/9788634
def get_import_path(cls_or_fn: type[Any]) -> str:
    """Get the full import path for a class or a function, e.g. `"path.to.MyClass"`"""
    module = cls_or_fn.__module__
    if module == "builtins":
        return cls_or_fn.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + cls_or_fn.__qualname__


def get_module_info(
    cls_or_fn: type[Any] | Callable[..., Any],
) -> tuple[ModuleType | None, str | None, str | None]:
    """Get the module, module name and module file path where the class or function is defined."""
    module_name: str | None = getattr(cls_or_fn, "__module__", None)

    if module_name:
        if module_name in sys.modules:
            module = sys.modules[module_name]
        else:
            try:
                module = import_module(module_name)
            except Exception:  # noqa: BLE001
                module = None
    else:
        module = None

    if module:
        module_file_path: str | None = getattr(module, "__file__", None)
    else:
        module_file_path = None

    return module, module_name, module_file_path


def default(val: T | None, default: U | Callable[[], U] | type[T], factory: bool = False) -> T | U:
    if val is not None:
        return val
    if factory:
        default_func = cast("Callable[[], U]", default)
        return default_func()
    return cast("U", default)


def get_index(lst: list[Any], key: Callable[[Any], bool]) -> int | None:
    """Get the index of the first item in the list that satisfies the key"""
    for i in range(len(lst)):
        if key(lst[i]):
            return i
    return None


def get_last_index(lst: list[Any], key: Callable[[Any], bool]) -> int | None:
    """Get the index of the last item in the list that satisfies the key"""
    for index, item in enumerate(reversed(lst)):
        if key(item):
            return len(lst) - 1 - index
    return None


def is_nonempty_str(txt: str | None) -> TypeGuard[str]:
    return txt is not None and bool(txt.strip())


# Convert Component class to something like `TableComp_a91d03`
def hash_comp_cls(comp_cls: type["Component"]) -> str:
    full_name = get_import_path(comp_cls)
    name_hash = md5(full_name.encode()).hexdigest()[0:6]  # noqa: S324
    return comp_cls.__name__ + "_" + name_hash


# String is a glob if it contains at least one of `?`, `*`, or `[`
is_glob_re = re.compile(r"[?*[]")


def is_glob(filepath: str) -> bool:
    return is_glob_re.search(filepath) is not None


def flatten(lst: Iterable[Iterable[T]]) -> list[T]:
    return list(chain.from_iterable(lst))


def to_dict(data: Any) -> dict:
    """
    Convert object to a dict.

    Handles `dict`, `NamedTuple`, and `dataclass`.
    """
    if isinstance(data, dict):
        return data
    if hasattr(data, "_asdict"):  # Case: NamedTuple
        return data._asdict()
    if is_dataclass(data):  # Case: dataclass
        # NOTE: This is same as `asdict`, but without recursing into nested dataclasses
        return {f.name: getattr(data, f.name) for f in fields(data)}

    return dict(data)


def format_url(url: str, query: dict[str, Any] | None = None, fragment: str | None = None) -> str:
    """
    Given a URL, add to it query parameters and a fragment, returning an updated URL.

    ```py
    url = format_url(url="https://example.com", query={"foo": "bar"}, fragment="baz")
    # https://example.com?foo=bar#baz
    ```

    `query` and `fragment` are optional, and not applied if `None`.

    Boolean `True` values in query parameters are rendered as flag parameters without values.

    `False` and `None` values in query parameters are omitted.

    ```py
    url = format_url(
        url="https://example.com",
        query={"foo": "bar", "baz": None, "enabled": True, "debug": False},
    )
    # https://example.com?foo=bar&enabled
    ```
    """
    parts = parse.urlsplit(url)
    fragment_enc = parse.quote(fragment or parts.fragment, safe="")
    base_qs = dict(parse.parse_qsl(parts.query))
    # Filter out `None` and `False` values
    filtered_query = {k: v for k, v in (query or {}).items() if v is not None and v is not False}
    merged = {**base_qs, **filtered_query}

    # Handle boolean True values as flag parameters (no explicit value)
    query_parts = []
    for key, value in merged.items():
        if value is True:
            query_parts.append(parse.quote_plus(str(key)))
        else:
            query_parts.append(f"{parse.quote_plus(str(key))}={parse.quote_plus(str(value))}")

    encoded_qs = "&".join(query_parts)

    return parse.urlunsplit(parts._replace(query=encoded_qs, fragment=fragment_enc))


def format_as_ascii_table(
    data: list[dict[str, Any]],
    headers: list[str] | tuple[str, ...] | set[str],
    include_headers: bool = True,
) -> str:
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
        data_row = "  ".join(
            f"{value:<{column_widths[header]}}" for value, header in zip(row_values, headers, strict=False)
        )
        data_rows.append(data_row)

    # Combine all parts into the final table
    table = "\n".join([header_row, separator, *data_rows]) if include_headers else "\n".join(data_rows)
    return table


def is_generator(obj: Any) -> TypeGuard[Generator[Any, Any, Any]]:
    """Check if an object is a generator with send method."""
    return hasattr(obj, "send")


def convert_class_to_namedtuple(cls: type[Any]) -> type[tuple[Any, ...]]:
    # Construct fields for a NamedTuple. Unfortunately one can't further subclass the subclass of `NamedTuple`,
    # so we need to construct a new class with the same fields.
    # NamedTuple has:
    # - Required fields, which are defined without values (annotations only)
    # - Optional fields with defaults
    # ```py
    # class Z:
    #     b: str          # Required, annotated
    #     a: int = None   # Optional, annotated
    #     c = 1           # NOT A FIELD! Class var!
    # ```
    # Annotations are stored in `X.__annotations__`, while the defaults are regular class attributes
    # NOTE: We ignore dunder methods
    # NOTE 2: All fields with default values must come after fields without defaults.
    field_names = list(cls.__annotations__.keys())

    # Get default values from the original class and set them on the new NamedTuple class
    field_names_set = set(field_names)
    defaults = {}
    class_attrs = {}
    for name, value in getmembers(cls):
        if name.startswith("__"):
            continue
        # Field default
        if name in field_names_set:
            defaults[name] = value
        else:
            # Class attribute
            class_attrs[name] = value

    # Figure out how many tuple fields have defaults. We need to know this
    # because NamedTuple functional syntax uses the pattern where defaults
    # are applied from the end.
    # Final call then looks like this:
    # `namedtuple("MyClass", ["a", "b", "c", "d"], defaults=[3, 4])`
    # with defaults c=3 and d=4
    num_fields_with_defaults = len(defaults)
    if num_fields_with_defaults:
        defaults_list = [defaults[name] for name in field_names[-num_fields_with_defaults:]]
    else:
        defaults_list = []
    tuple_cls = namedtuple(cls.__name__, field_names, defaults=defaults_list)  # type: ignore[misc]  # noqa: PYI024

    # `collections.namedtuple` doesn't allow to specify annotations, so we pass them afterwards
    tuple_cls.__annotations__ = cls.__annotations__
    # Likewise, `collections.namedtuple` doesn't allow to specify class vars
    for name, value in class_attrs.items():
        setattr(tuple_cls, name, value)

    return tuple_cls


def extract_regex_matches(s: bytes, pattern: re.Pattern) -> tuple[bytes, list[re.Match[bytes]]]:
    """
    Extract all matches from a bytes string using a regex pattern.

    Returns the string without the matched parts, and a list of matches.
    """
    matches: list[re.Match[bytes]] = []

    def on_replace_match(match: re.Match[bytes]) -> bytes:
        matches.append(match)
        return b""

    content = pattern.sub(on_replace_match, s)
    return (content, matches)
