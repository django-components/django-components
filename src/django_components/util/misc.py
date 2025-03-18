import re
import sys
from hashlib import md5
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple, Type, TypeVar, Union

from django_components.util.nanoid import generate

if TYPE_CHECKING:
    from django_components.component import Component

T = TypeVar("T")


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
        size=6,
    )


def is_str_wrapped_in_quotes(s: str) -> bool:
    return s.startswith(('"', "'")) and s[0] == s[-1] and len(s) >= 2


def snake_to_pascal(name: str) -> str:
    return "".join(word.title() for word in name.split("_"))


def is_identifier(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value.isidentifier():
        return False
    return True


def any_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return any(p.search(string) is not None for p in patterns)


def no_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return all(p.search(string) is None for p in patterns)


# See https://stackoverflow.com/a/2020083/9788634
def get_import_path(cls_or_fn: Type[Any]) -> str:
    """
    Get the full import path for a class or a function, e.g. `"path.to.MyClass"`
    """
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
            except Exception:
                module = None
    else:
        module = None

    if module:
        module_file_path: Optional[str] = getattr(module, "__file__", None)
    else:
        module_file_path = None

    return module, module_name, module_file_path


def default(val: Optional[T], default: T) -> T:
    return val if val is not None else default


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


def hash_comp_cls(comp_cls: Type["Component"]) -> str:
    full_name = get_import_path(comp_cls)
    comp_cls_hash = md5(full_name.encode()).hexdigest()[0:6]
    return comp_cls.__name__ + "_" + comp_cls_hash
