import re
import sys
from dataclasses import asdict, is_dataclass
from hashlib import md5
from importlib import import_module
from itertools import chain
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Type, TypeVar, Union, cast
from urllib import parse

from django_components.constants import UID_LENGTH
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


def is_str_wrapped_in_quotes(s: str) -> bool:
    return s.startswith(('"', "'")) and s[0] == s[-1] and len(s) >= 2


def snake_to_pascal(name: str) -> str:
    return "".join(word.title() for word in name.split("_"))


def is_identifier(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.isidentifier()


def any_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return any(p.search(string) is not None for p in patterns)


def no_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return all(p.search(string) is None for p in patterns)


# See https://stackoverflow.com/a/2020083/9788634
def get_import_path(cls_or_fn: Type[Any]) -> str:
    """Get the full import path for a class or a function, e.g. `"path.to.MyClass"`"""
    module = cls_or_fn.__module__
    if module == "builtins":
        return cls_or_fn.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + cls_or_fn.__qualname__


def get_module_info(
    cls_or_fn: Union[Type[Any], Callable[..., Any]],
) -> Tuple[Optional[ModuleType], Optional[str], Optional[str]]:
    """Get the module, module name and module file path where the class or function is defined."""
    module_name: Optional[str] = getattr(cls_or_fn, "__module__", None)

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
        module_file_path: Optional[str] = getattr(module, "__file__", None)
    else:
        module_file_path = None

    return module, module_name, module_file_path


def default(val: Optional[T], default: Union[U, Callable[[], U], Type[T]], factory: bool = False) -> Union[T, U]:
    if val is not None:
        return val
    if factory:
        default_func = cast("Callable[[], U]", default)
        return default_func()
    return cast("U", default)


def get_index(lst: List, key: Callable[[Any], bool]) -> Optional[int]:
    """Get the index of the first item in the list that satisfies the key"""
    for i in range(len(lst)):
        if key(lst[i]):
            return i
    return None


def get_last_index(lst: List, key: Callable[[Any], bool]) -> Optional[int]:
    """Get the index of the last item in the list that satisfies the key"""
    for index, item in enumerate(reversed(lst)):
        if key(item):
            return len(lst) - 1 - index
    return None


def is_nonempty_str(txt: Optional[str]) -> bool:
    return txt is not None and bool(txt.strip())


# Convert Component class to something like `TableComp_a91d03`
def hash_comp_cls(comp_cls: Type["Component"]) -> str:
    full_name = get_import_path(comp_cls)
    name_hash = md5(full_name.encode()).hexdigest()[0:6]  # noqa: S324
    return comp_cls.__name__ + "_" + name_hash


# String is a glob if it contains at least one of `?`, `*`, or `[`
is_glob_re = re.compile(r"[?*[]")


def is_glob(filepath: str) -> bool:
    return is_glob_re.search(filepath) is not None


def flatten(lst: Iterable[Iterable[T]]) -> List[T]:
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
        return asdict(data)  # type: ignore[arg-type]

    return dict(data)


def format_url(url: str, query: Optional[Dict] = None, fragment: Optional[str] = None) -> str:
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
    data: List[Dict[str, Any]],
    headers: Union[List[str], Tuple[str, ...], Set[str]],
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
        data_row = "  ".join(f"{value:<{column_widths[header]}}" for value, header in zip(row_values, headers))
        data_rows.append(data_row)

    # Combine all parts into the final table
    table = "\n".join([header_row, separator, *data_rows]) if include_headers else "\n".join(data_rows)
    return table
