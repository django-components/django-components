"""
argparse introspection for the management-commands reference (feature 4.27).

Management commands aren't griffe symbols - they're argparse parsers. Following
spike 5 section 2, we keep the runtime-introspection path the old ``reference.py``
used: let ``ArgumentParser`` format its own arguments, then parse that text back
into structured sections (options / positional arguments / subcommands). It pokes
at a few argparse internals because there's no public API for "give me the
arguments", exactly as the old generator did.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from argparse import ArgumentParser

_ARG_LINE = re.compile(r"^  \S")
# "subcommands:\n  {create,upgrade,ext}" -> drop the brace line
_SUBCOMMANDS_BRACE = re.compile(r"subcommands:\n.*?\}", re.DOTALL)
# ANSI SGR (color) escape, e.g. "\x1b[1;34m". Python 3.14's argparse colorizes
# its help output, and those codes both leak into the rendered HTML and break the
# plain-text section parsing below (the "subcommands:" split, the arg-line regex).
_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color escape codes so help text can be parsed and rendered as plain text."""
    return _ANSI_SGR.sub("", text)


class CommandArg(TypedDict):
    names: list[str]  # e.g. ["-h", "--help"] or ["create"]
    desc: str


def parse_command_args(parser: ArgumentParser) -> dict[str, list[CommandArg]]:
    """Structured args keyed by section title (e.g. ``{"options": [{names, desc}]}``)."""
    return _parse(strip_ansi(_format_args(parser)))


def _format_args(parser: ArgumentParser) -> str:
    # Mirror ArgumentParser.format_help() but emit only the argument groups.
    formatter = parser._get_formatter()
    for group in parser._action_groups:
        formatter.start_section(group.title)
        formatter.add_text(group.description)
        formatter.add_arguments(group._group_actions)
        formatter.end_section()
    return formatter.format_help()


def _parse(text: str) -> dict[str, list[CommandArg]]:
    text = _flatten_subcommands(text)

    section: str | None = None
    data: dict[str, list[CommandArg]] = {}
    for line in text.split("\n"):
        if not line:
            section = None
            continue
        if section is None:
            section = line.rstrip().rstrip(":")
            data.setdefault(section, [])
            continue
        if _ARG_LINE.match(line):
            names, _, desc = line.strip().partition("  ")
            data[section].append({"names": names.split(", "), "desc": desc.strip()})
        elif data.get(section):
            # Continuation of the previous argument's description (wrapped line).
            data[section][-1]["desc"] = f"{data[section][-1]['desc']} {line.strip()}".strip()
    return data


def _flatten_subcommands(text: str) -> str:
    """Drop the ``{a,b,c}`` brace line and dedent subcommand rows from 4 to 2 spaces."""
    if "subcommands:" not in text:
        return text
    text = _SUBCOMMANDS_BRACE.sub("subcommands:", text)
    before, after = text.split("subcommands:\n", 1)
    dedented = "\n".join(line[2:] if line.startswith(" " * 4) else line for line in after.split("\n"))
    return before + "subcommands:\n" + dedented
