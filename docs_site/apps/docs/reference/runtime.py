"""
Runtime-introspection helpers for renderers that work off live classes.

Some reference kinds aren't well modelled by griffe's static view - management
commands (argparse) and template tags (the metaclass-set ``_signature``). Those
renderers re-import the class and read its runtime attributes; these two helpers
are the shared plumbing (import by dotted path, build a source-code link).
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any

from django.conf import settings

from apps.docs.griffe_extensions.source_code import format_source_code_html


def import_symbol(dotted_path: str) -> Any:
    """Import and return the object at ``module.path.Qualname``."""
    module_path, _, qualname = dotted_path.rpartition(".")
    return getattr(importlib.import_module(module_path), qualname)


def source_link(obj: type) -> str:
    """A "See source code" link for a runtime class (its defining file + line)."""
    try:
        rel = Path(inspect.getfile(obj)).resolve().relative_to(Path(settings.REPO_ROOT).resolve())
    except (TypeError, ValueError):
        return ""
    try:
        lineno: int | None = inspect.findsource(obj)[1] + 1
    except (OSError, TypeError):
        lineno = None
    return format_source_code_html(rel, lineno)
