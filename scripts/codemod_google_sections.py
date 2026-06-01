# ruff: noqa: T201
"""
Codemod: rename `**X:**`-style pseudo-section headings to true Google-style
`X:` headings, so griffe's Google parser picks them up as structured
sections. Per spike 5 §11.4 (docs_site/design/DESIGN_spike_5.md).

Run with `--dry-run` to preview; without it to apply in place.

Scope:
    - src/django_components/**/*.py (docstrings)

What this codemod handles (safe, mechanical):
    `**Example:**`   -> `Example:`     (griffe accepts singular)
    `**Examples:**`  -> `Examples:`
    `**Note:**`      -> `Note:`
    `**Notes:**`     -> `Notes:`
    `**Warning:**`   -> `Warning:`
    `**Warnings:**`  -> `Warnings:`
    `**Returns:**`   -> `Returns:`
    `**Yields:**`    -> `Yields:`
    `**Attributes:**` -> `Attributes:`

What this codemod does NOT handle (needs manual restructuring of the
following bullet list into Google's `name: desc` indented form, NOT
a single-line text substitution):
    `**Args:**`       (8 hits)
    `**Arguments:**`  (3 hits)
    `**Raises:**`     (3 hits)

What this codemod deliberately leaves alone (not Google-canonical, would
break griffe parsing or has no semantic equivalent):
    `**Slots:**`, `**Python:**`, `**Options:**`, `**Inputs:**`,
    `**Location:**`, `**Subcommands:**`, `**Dictionary:**`

The bold form on these stays. They render as bold sub-headings in both
the old and the new builder.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Free-form sections that griffe Google parser recognizes by name. Bullet-list
# ones (Args, Arguments, Raises) are deliberately omitted: their content needs
# a bullet -> bare-indent restructure that isn't a single-line substitution.
FREE_FORM_SECTIONS = (
    "Example",
    "Examples",
    "Note",
    "Notes",
    "Warning",
    "Warnings",
    "Returns",
    "Yields",
    "Attributes",
)

# Match `**X:**` at line start (with optional leading whitespace).
PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)\*\*(?P<name>" + "|".join(FREE_FORM_SECTIONS) + r"):\*\*[ \t]*$",
    re.MULTILINE,
)

# Only sweep src/django_components docstrings. docs/*.md is mostly hand-authored
# prose where `**Example:**` is intentionally a bold sub-heading, not a Google
# docstring section.
SCOPE = [
    ("src/django_components", "**/*.py"),
]


def rewrite_match(m: re.Match[str]) -> str:
    indent = m.group("indent")
    name = m.group("name")
    return f"{indent}{name}:"


def rewrite_file(path: Path, *, dry_run: bool) -> int:
    """Return the number of transformations made (or that would be made)."""
    content = path.read_text(encoding="utf-8")
    new_content, n_subs = PATTERN.subn(rewrite_match, content)
    if n_subs and not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return n_subs


def gather_files() -> list[Path]:
    files: list[Path] = []
    for subdir, pattern in SCOPE:
        files.extend(sorted((REPO_ROOT / subdir).glob(pattern)))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing.",
    )
    args = parser.parse_args()

    files = gather_files()
    total = 0
    file_count = 0

    for f in files:
        n = rewrite_file(f, dry_run=args.dry_run)
        if n:
            total += n
            file_count += 1

    verb = "would change" if args.dry_run else "changed"
    print(f"{verb} {total} pseudo-section heading(s) across {file_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
