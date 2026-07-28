"""
``ReferenceManagementCommand`` - renders one CLI command (feature 4.27).

The most bespoke entry renderer: a command isn't a griffe symbol, so this
re-imports the command class, builds its argparse parser, and lays out a usage
block, source link, summary, the argument sections (options / positionals /
subcommands), and the command's description. Subcommands link to their own
sections on the page (the command-tree layout).
"""

from __future__ import annotations

import html
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from apps.docs.reference.commands import CommandArg, parse_command_args, strip_ansi
from apps.docs.reference.discovery.kinds import slugify_anchor
from apps.docs.reference.docstring import render_markdown
from apps.docs.reference.runtime import import_symbol, source_link

from django_components import Component, register, types
from django_components.util.command import setup_parser_from_command

if TYPE_CHECKING:
    from argparse import ArgumentParser

    from apps.docs.reference.discovery.kinds import ReferenceEntry


@register("reference_management_command")
class ReferenceManagementCommand(Component):
    class Kwargs:
        entry: ReferenceEntry
        current_url: str

    template: types.django_html = """
        <div class="doc doc-object doc-command">
            <h2 id="{{ anchor }}" class="doc doc-heading">
                <span class="doc doc-object-name doc-command-name">{{ display_name }}</span>
                <a class="headerlink" href="#{{ anchor }}" title="Permanent link">¤</a>
            </h2>
            <div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{{ usage }}</code></pre></div>
                {{ source_html|safe }}
                {{ summary_html|safe }}
                {{ args_html|safe }}
                {{ description_html|safe }}
            </div>
        </div>
    """

    def get_template_data(self, args: Any, kwargs: Kwargs, slots: Any, context: Any) -> dict[str, Any]:
        entry: ReferenceEntry = kwargs.entry
        current_url = kwargs.current_url
        command_cls = import_symbol(entry.dotted_path)
        path = entry.display_name
        parser = setup_parser_from_command(command_cls)

        # argparse escapes `%` as `%%` in help strings; undo it.
        summary = (command_cls.help or "").replace("%%", "%")

        return {
            "anchor": entry.canonical_anchor,
            "display_name": path,
            "usage": _usage(parser, path),
            "source_html": source_link(command_cls),
            "summary_html": render_markdown(summary, current_url=current_url),
            "args_html": _render_args(parse_command_args(parser), path),
            "description_html": render_markdown(dedent(command_cls.__doc__ or ""), current_url=current_url),
        }


def _usage(parser: ArgumentParser, path: str) -> str:
    raw = strip_ansi(parser.format_usage())
    body = raw.removeprefix("usage: ")
    # `body` opens with the command's own (short) name; prefix the full invocation.
    parent = " ".join(path.split()[:-1])
    prefix = f"python manage.py {parent}".rstrip() + " "
    return f"usage: {prefix}{body}".rstrip()


def _render_args(sections: dict[str, list[CommandArg]], path: str) -> str:
    blocks: list[str] = []
    for title, args in sections.items():
        if not args:
            continue
        items: list[str] = []
        for arg in args:
            names = arg["names"]
            desc = html.escape(arg["desc"])
            if title == "subcommands":
                sub_anchor = slugify_anchor(f"{path} {names[0]}")
                label = f'<a href="#{sub_anchor}"><code>{html.escape(names[0])}</code></a>'
            else:
                label = ", ".join(f"<code>{html.escape(n)}</code>" for n in names)
            items.append(f"<li>{label}{f' &ndash; {desc}' if desc else ''}</li>")
        blocks.append(
            '<div class="doc-section doc-command-args">'
            f'<p class="doc-section-title">{html.escape(title.title())}</p>'
            f"<ul>{''.join(items)}</ul></div>"
        )
    return "".join(blocks)
