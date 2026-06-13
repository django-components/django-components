"""
Griffe extensions for the API reference, ported from the old mkdocs setup
(``docs_old/scripts/extensions.py``).

Both extensions enrich griffe objects at load time by prepending HTML to their
docstrings:

- ``RuntimeBasesExtension`` adds a ``Bases: ...`` line (replacing mkdocstrings'
  ``show_bases``, but resolving base names from the runtime objects so aliases /
  reassignments are followed correctly).
- ``SourceCodeExtension`` adds a "See source code" link to the symbol on GitHub.

They were verified portable in spike 5 section 8: they depend only on griffe plus
two strings (repo URL + branch), with no mkdocstrings runtime dependency. The
one change from the original is that the repo URL + branch now come from Django
settings instead of ``mkdocs.yml``.
"""

from __future__ import annotations

import griffe

from apps.docs.griffe_extensions.runtime_bases import RuntimeBasesExtension
from apps.docs.griffe_extensions.source_code import SourceCodeExtension

__all__ = ["RuntimeBasesExtension", "SourceCodeExtension", "build_extensions"]


def build_extensions() -> griffe.Extensions:
    """
    The extension set to pass to ``griffe.load(extensions=...)``.

    Order matters (same as the old mkdocs config): bases first, then the source
    link, so the rendered docstring reads "Bases / body / source link".
    """
    return griffe.load_extensions(RuntimeBasesExtension(), SourceCodeExtension())
