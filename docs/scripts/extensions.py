from pathlib import Path
from typing import Any, List, Optional, Type

import griffe
from mkdocs_util import get_mkdocstrings_plugin_handler_options, import_object, load_config

from django_components.util.misc import get_import_path

SOURCE_CODE_GIT_BRANCH = "master"


mkdocstrings_config = get_mkdocstrings_plugin_handler_options() or {}
is_skip_docstring: bool = mkdocstrings_config.get("show_if_no_docstring", "false") != "true"


# Replacement for `show_bases: true`. Our implementation takes base names from the runtime
# objects, effectively resolving aliases / reassignments.
class RuntimeBasesExtension(griffe.Extension):
    """Griffe extension that lists class bases."""

    def on_class_instance(self, cls: griffe.Class, **_kwargs: Any) -> None:
        if is_skip_docstring and cls.docstring is None:
            return

        runtime_cls: Type = import_object(cls)

        bases_formatted: List[str] = []
        for base in runtime_cls.__bases__:
            bases_formatted.append(f"<code>{get_import_path(base)}</code>")

        html = f'<p class="doc doc-class-bases">Bases: {", ".join(bases_formatted) or "-"}</p>'

        cls.docstring = cls.docstring or griffe.Docstring("", parent=cls)
        cls.docstring.value = html + "\n\n" + cls.docstring.value


class SourceCodeExtension(griffe.Extension):
    """Griffe extension that adds link to the source code at the end of the docstring."""

    def on_instance(self, obj: griffe.Object, **_kwargs: Any) -> None:
        if is_skip_docstring and obj.docstring is None:
            return

        html = _format_source_code_html(obj.relative_filepath, obj.lineno)
        obj.docstring = obj.docstring or griffe.Docstring("", parent=obj)
        obj.docstring.value = html + obj.docstring.value


def _format_source_code_html(relative_filepath: Path, lineno: Optional[int]) -> str:
    # Remove trailing slash and whitespace
    repo_url = load_config()["repo_url"].strip("/ ")
    branch_path = f"tree/{SOURCE_CODE_GIT_BRANCH}"
    lineno_hash = f"#L{lineno}" if lineno is not None else ""
    # Generate URL pointing to the source file like
    # https://github.com/django-components/django-components/blob/master/src/django_components/components/dynamic.py#L8
    url = f"{repo_url}/{branch_path}/{relative_filepath}{lineno_hash}"

    # Open in new tab
    html = f'\n\n<a href="{url}" target="_blank">See source code</a>\n\n'

    return html
