"""
Shared runtime introspection helpers for discovery.

Discovery decides *what* to document by walking ``django_components`` at runtime,
the same way the old ``reference.py`` did. These predicates mirror its
``_is_*`` helpers so each page can include/exclude the right symbols (e.g. the
API page excludes everything that has its own dedicated page).
"""

from __future__ import annotations

import inspect
from typing import TypeGuard

import django_components
from django_components import Component
from django_components.node import BaseNode
from django_components.tag_formatter import TagFormatterABC


def public_names() -> list[str]:
    """Public names exported from the package (the ``__init__`` contract)."""
    names = getattr(django_components, "__all__", None)
    if names:
        return list(names)
    return [n for n in dir(django_components) if not n.startswith("_")]


def is_class(obj: object) -> TypeGuard[type]:
    # Exclude typing GenericAlias (e.g. List[int]) which inspect.isclass misjudges.
    return inspect.isclass(obj) and type(obj).__name__ != "GenericAlias"


def is_component_cls(obj: object) -> bool:
    return is_class(obj) and issubclass(obj, Component) and obj is not Component


def is_error_cls(obj: object) -> bool:
    return is_class(obj) and issubclass(obj, Exception) and obj is not Exception


def is_tag_formatter_cls(obj: object) -> TypeGuard[type]:
    return is_class(obj) and issubclass(obj, TagFormatterABC) and obj is not TagFormatterABC


def is_tag_formatter_instance(obj: object) -> bool:
    return isinstance(obj, TagFormatterABC)


def is_template_tag(obj: object) -> bool:
    return is_class(obj) and issubclass(obj, BaseNode)


def is_extension_hook_api(obj: object) -> bool:
    return is_class(obj) and bool(getattr(obj, "_extension_hook_api", False))


def is_extension_command_api(obj: object) -> bool:
    return is_class(obj) and bool(getattr(obj, "_extension_command_api", False))


def is_extension_url_api(obj: object) -> bool:
    return is_class(obj) and bool(getattr(obj, "_extension_url_api", False))
