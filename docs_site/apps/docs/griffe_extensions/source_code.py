"""
``SourceCodeExtension`` - prepends a "See source code" GitHub link to docstrings.

Replacement for mkdocstrings' ``show_source``. Ported from
``the old mkdocs scripts/extensions.py``, with two changes:

- The repo URL + branch come from Django settings, not ``mkdocs.yml``.
- The file path is computed relative to ``REPO_ROOT`` from griffe's absolute
  ``filepath`` (in this project griffe resolves the package to an absolute path,
  so ``relative_filepath`` is not repo-relative).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import griffe
from django.conf import settings


def format_source_code_html(relative_filepath: Path, lineno: int | None) -> str:
    """Build the "See source code" anchor pointing at the file on GitHub."""
    repo_url = str(settings.REPO_URL).strip("/ ")
    branch = settings.SOURCE_CODE_GIT_BRANCH
    lineno_hash = f"#L{lineno}" if lineno is not None else ""
    # blob/<branch>/<path>#L<n> is the canonical GitHub file+line URL, e.g.
    # https://github.com/django-components/django-components/blob/master/src/django_components/library.py#L9
    url = f"{repo_url}/blob/{branch}/{relative_filepath.as_posix()}{lineno_hash}"
    # Open in a new tab so readers don't lose their place in the docs.
    return f'\n\n<a class="doc-source-link" href="{url}" target="_blank">See source code</a>\n\n'


class SourceCodeExtension(griffe.Extension):
    """Griffe extension that prepends a source-code link to docstrings."""

    def __init__(self, *, skip_docstringless: bool = True) -> None:
        # Same policy as RuntimeBasesExtension: don't synthesize a docstring for
        # a docstring-less symbol just to carry the source link.
        self.skip_docstringless = skip_docstringless

    def on_instance(self, *, obj: griffe.Object, **_kwargs: Any) -> None:
        if self.skip_docstringless and obj.docstring is None:
            return

        # Skip individual class-member attributes (e.g. NamedTuple fields). A
        # per-field source link is noise and would pollute structured field-doc
        # extraction (the hook "Available data" table). Classes, functions /
        # methods, modules and module-level attributes still get the link.
        if obj.kind is griffe.Kind.ATTRIBUTE and obj.parent is not None and obj.parent.kind is griffe.Kind.CLASS:
            return

        rel = self._repo_relative_path(obj.filepath)
        if rel is None:
            return

        html = format_source_code_html(rel, obj.lineno)
        obj.docstring = obj.docstring or griffe.Docstring("", parent=obj)
        obj.docstring.value = html + obj.docstring.value

    @staticmethod
    def _repo_relative_path(filepath: Path | list[Path] | None) -> Path | None:
        # Namespace packages report a list of paths; symbols we document always
        # live in a single file. Anything else (None / outside the repo) gets no
        # source link rather than a broken one.
        if not isinstance(filepath, Path):
            return None
        try:
            return filepath.resolve().relative_to(Path(settings.REPO_ROOT).resolve())
        except ValueError:
            return None
