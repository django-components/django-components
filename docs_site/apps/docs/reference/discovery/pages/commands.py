"""
Discovery for the CLI Commands reference page (feature 4.9).

Port of ``gen_reference_commands``: all commands live under ``components`` and
declare their subcommands statically, so we walk the tree from
``ComponentsRootCommand`` depth-first. Each command becomes one entry; the entry
carries the command's full path (e.g. ``"components ext run"``) as the display
name and the command class's import path so the renderer can re-import it and
introspect its argparse parser.

The legacy file-based commands (``startcomponent`` / ``upgradecomponent``) are
deliberately excluded - they're marked TODO_v1-REMOVE in the source.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage
from django_components.commands.components import ComponentsRootCommand

if TYPE_CHECKING:
    from django_components.util.command import ComponentCommand

_PREFACE = (
    "These are the [Django management commands]"
    "(https://docs.djangoproject.com/en/5.2/ref/django-admin) that installing "
    "`django_components` adds. All of them live under the `components` command."
)


def discover() -> ReferencePage:
    """Build the Commands ``ReferencePage`` by walking the command tree."""
    entries: list[ReferenceEntry] = []
    _walk(ComponentsRootCommand, (), entries)
    return ReferencePage(
        slug="commands",
        title="CLI commands",
        preface_md=_PREFACE,
        entries=tuple(entries),
        layout="command_tree",
        description="API reference - the django-components CLI commands.",
    )


def _walk(cmd_cls: type[ComponentCommand], parent_path: tuple[str, ...], entries: list[ReferenceEntry]) -> None:
    path = (*parent_path, cmd_cls.name)
    entries.append(
        ReferenceEntry(
            kind="management_command",
            dotted_path=f"{cmd_cls.__module__}.{cmd_cls.__qualname__}",
            display_name=" ".join(path),
        )
    )
    for subcommand in cmd_cls.subcommands:
        _walk(subcommand, path, entries)
