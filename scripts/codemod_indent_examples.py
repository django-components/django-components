# ruff: noqa: T201
"""
Codemod: convert `Example:` / `Examples:` blocks in docstrings to a shape
griffe's Google parser recognizes as `DocstringSectionKind.examples`.

Per spike 5 §11.4 follow-up. Griffe requires THREE things at once for a
section to be picked up (verified against griffe ~1.x source at
griffe/_internal/docstrings/google.py:_section_kind +
parse_google's admonition branch):

1. The heading keyword is in griffe's section-kind dict. For examples
   that means `Examples:` (plural) ONLY. Singular `Example:` is treated
   as an admonition (which renders as plain text).
2. The body is indented one level past the heading.
3. There is NO blank line between the heading and the body (a blank
   line trips griffe's "extraneous blank line below section title"
   detector and the section is silently skipped to plain text).

This codemod applies all three changes in one pass, and also treats
peer-level `!!!` admonitions and `##` markdown headings (at the same
indent as the `Examples:` heading) as SECTION TERMINATORS so they
aren't accidentally absorbed into the body.

Scope:
    - src/django_components/**/*.py (docstrings only)

Per-block transformations applied (where applicable):

    A. Rename `Example:` -> `Examples:` (singular -> plural).
    B. Collapse the blank line immediately after the heading.
    C. Indent every non-blank body line by 4 spaces, until end-of-section.

End-of-section is signaled by ANY of (and only OUTSIDE a fenced code block):
    - line is dedented below the heading's indent
    - line is the closing triple-double-quote/triple-single-quote at
      indent <= heading's indent
    - line is another Google section heading at heading's indent
      (Args, Arguments, Returns, Yields, Raises, Note, Notes, Warning,
       Warnings, Attributes, Methods, Example, Examples)
    - line at heading's indent starts with `!!!` (Material admonition,
      peer-level)
    - line at heading's indent starts with `##` (markdown H2/H3/...,
      peer-level)

The fence-state tracking matters: inside a ``` fenced code block, Python
comments like `# Get the URL...` would otherwise trip the `##` rule (since
`#+\\s` matches one OR more hashes). Fence-aware walking treats every
line inside the fence as body, including the fence's open/close lines.

Blank lines inside the body are kept blank (no indent applied).

The codemod is conservative: when the first non-blank line below the
heading is already at >= heading_indent + 4 (already canonical),
transformations B+C are skipped for that block; A is still applied if
the heading is singular.

Re-running on the new tree is a no-op.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

HEADING_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>Example|Examples):[ \t]*$")

GOOGLE_SECTION_TERMINATOR_RE = re.compile(
    r"^[ \t]*(?:Args|Arguments|Attributes|Returns|Yields|Raises|Note|Notes|"
    r"Warning|Warnings|Examples?|Methods):[ \t]*$",
)

# Closing triple-quote: the quote at line start (after whitespace) optionally
# followed by a trailing comment like `# noqa: E501`. The earlier stricter form
# `..."""\s*$` missed lines like `    """  # noqa: E501` and caused the
# codemod to walk past the docstring boundary, indenting Python code.
CLOSING_TRIPLE_QUOTE_RE = re.compile(r'^[ \t]*("""|\'\'\')')

# Peer-level structures that should NOT be absorbed into the Examples body.
# At the same indent as the Examples heading, these are taken as terminators:
#   - `!!! warning` / `!!! note` etc. — Material admonitions.
#   - `## ` / `### ` — markdown headings.
#   - `**Foo:**` — bold markdown pseudo-sections (e.g. `**Slots:**`,
#     `**Component URL:**`). These are non-Google headings griffe doesn't
#     recognize but humans wrote at the docstring's base indent as peers.
PEER_ADMONITION_RE = re.compile(r"^[ \t]*!!!\s")
PEER_MARKDOWN_HEADING_RE = re.compile(r"^[ \t]*#+\s")
# Allow backticks inside the label, e.g. **Passing `request` to a component:**.
PEER_BOLD_PSEUDO_SECTION_RE = re.compile(r"^[ \t]*\*\*[^\n*]+:\*\*[ \t]*$")

SCOPE = [("src/django_components", "**/*.py")]


def leading_ws_width(line: str) -> int:
    """Count leading spaces (tabs counted as 4 per ruff config; codebase is spaces)."""
    return len(line) - len(line.lstrip(" \t"))


def _is_section_terminator(line: str, heading_indent: int) -> bool:
    """Return True iff the line at `heading_indent` indent ends the section."""
    current_indent = leading_ws_width(line)
    if current_indent < heading_indent:
        return True
    if current_indent <= heading_indent and CLOSING_TRIPLE_QUOTE_RE.match(line):
        return True
    if current_indent == heading_indent:
        if GOOGLE_SECTION_TERMINATOR_RE.match(line):
            return True
        if PEER_ADMONITION_RE.match(line):
            return True
        if PEER_MARKDOWN_HEADING_RE.match(line):
            return True
        if PEER_BOLD_PSEUDO_SECTION_RE.match(line):
            return True
    return False


def process_file(path: Path, *, dry_run: bool) -> int:
    """Return the number of Example/Examples blocks modified."""
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=False)
    n_changed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        match = HEADING_RE.match(line)
        if not match:
            i += 1
            continue

        heading_indent = len(match.group("indent"))
        name = match.group("name")

        # Apply transformation A: singular -> plural.
        new_heading = " " * heading_indent + "Examples:"
        if name == "Example":
            lines[i] = new_heading

        # Find first non-blank line below the heading.
        first_body_idx = i + 1
        while first_body_idx < len(lines) and lines[first_body_idx].strip() == "":
            first_body_idx += 1

        if first_body_idx >= len(lines):
            # No body before EOF.
            if name == "Example":
                n_changed += 1
            i += 1
            continue

        first_body = lines[first_body_idx]
        first_body_indent = leading_ws_width(first_body)

        if first_body_indent >= heading_indent + 4:
            # Already canonical body indent. Skip B+C. Count only if A applied.
            if name == "Example":
                n_changed += 1
            i = first_body_idx
            continue

        if first_body_indent < heading_indent:
            # Empty section (next line dedents). Skip B+C.
            if name == "Example":
                n_changed += 1
            i = first_body_idx
            continue

        # Body is at exactly heading_indent. Apply B (collapse blank line) + C (indent).
        # B: remove the blank line(s) between heading and first body line.
        # Note: this also handles "more than one blank line" by collapsing to zero.
        if first_body_idx > i + 1:
            del lines[i + 1 : first_body_idx]
            first_body_idx = i + 1
            first_body = lines[first_body_idx]

        # C: indent body lines until end-of-section. Track fence state so
        # that Python comments (`# ...`) inside fenced code blocks are NOT
        # treated as markdown headings by the peer-level terminator check.
        k = first_body_idx
        in_fence = False
        while k < len(lines):
            current = lines[k]
            stripped = current.strip()

            if stripped == "":
                k += 1
                continue

            # Fence marker: indent the marker line AND toggle state.
            if stripped.startswith("```"):
                lines[k] = "    " + current
                in_fence = not in_fence
                k += 1
                continue

            if in_fence:
                # Inside a fence: everything is body, regardless of
                # what the line looks like.
                lines[k] = "    " + current
                k += 1
                continue

            if _is_section_terminator(current, heading_indent):
                break

            lines[k] = "    " + current
            k += 1

        n_changed += 1
        i = k

    if n_changed and not dry_run:
        new_content = "\n".join(lines)
        if original.endswith("\n"):
            new_content += "\n"
        path.write_text(new_content, encoding="utf-8")

    return n_changed


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
        n = process_file(f, dry_run=args.dry_run)
        if n:
            total += n
            file_count += 1
            print(f"  {f.relative_to(REPO_ROOT)}: {n} block(s)")

    verb = "would convert" if args.dry_run else "converted"
    print(f"{verb} {total} Example/Examples block(s) across {file_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
