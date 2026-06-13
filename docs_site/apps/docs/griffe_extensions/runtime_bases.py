"""
``RuntimeBasesExtension`` - prepends a "Bases: ..." line to class docstrings.

Replacement for mkdocstrings' ``show_bases: true``. Base names are taken from
the *runtime* objects (via a real import), which resolves aliases and
reassignments that static analysis would miss. Ported from
``docs_old/scripts/extensions.py``.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

import griffe

from django_components.util.misc import get_import_path


def import_object(obj: griffe.Object | griffe.Alias) -> Any:
    """Import and return the runtime object a griffe object refers to."""
    module = import_module(obj.module.path)
    return getattr(module, obj.name)


class RuntimeBasesExtension(griffe.Extension):
    """Griffe extension that prepends a ``Bases: ...`` line to class docstrings."""

    def __init__(self, *, skip_docstringless: bool = True) -> None:
        # Matches the old mkdocstrings global default (`show_if_no_docstring:
        # false`): when a class has no docstring, don't synthesize one just to
        # carry the bases line - that would make every docstring-less symbol
        # look documented. Pages that want docstring-less symbols shown
        # (e.g. exceptions) all carry real docstrings, so this never bites them.
        self.skip_docstringless = skip_docstringless

    def on_class_instance(self, *, cls: griffe.Class, **_kwargs: Any) -> None:
        if self.skip_docstringless and cls.docstring is None:
            return

        runtime_cls: type = import_object(cls)

        bases_formatted = [f"<code>{get_import_path(base)}</code>" for base in runtime_cls.__bases__]
        html = f'<p class="doc doc-class-bases">Bases: {", ".join(bases_formatted) or "-"}</p>'

        cls.docstring = cls.docstring or griffe.Docstring("", parent=cls)
        cls.docstring.value = html + "\n\n" + cls.docstring.value
