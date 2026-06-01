# ruff: noqa: T201
"""
Codemod: rewrite hand-typed `[X](path.md#django_components.Y)` markdown links
to short-form bracket cross-refs `[X][ShortKey]` per spike 5 §11.4.

Run with `--dry-run` to preview; without it to apply in place.

Scope:
    - src/django_components/**/*.py (docstrings)
    - docs/**/*.md (user-facing docs)

The output key always strips the `django_components.` prefix AND any leading
lowercase (module) path segments, matching the SYMBOL_INDEX shape the new
docs resolver will use (spike 5 §11.3). The current mkdocs-autorefs index
won't resolve these short keys; that's intentional - we don't publish until
the new resolver lands in Phase 4.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Match `[link text](path/with/anything.md#django_components.X.Y.Z)`
# The path part can have anything except `)`; the fragment must start with
# `#django_components.` and consume the rest up to `)`.
LINK_RE = re.compile(
    r"""
    \[                              # opening bracket
    (?P<text>                       # link text:
        (?:                         # repeated (non-greedy):
            \[[^\]]*\]              #   - balanced single-nested brackets [..]
            |                       #   - or
            [^\]]                   #   - any character that isn't `]`
        )*?
    )
    \]
    \(
    [^)#\s]*                        # any path (or empty), no spaces
    \#django_components\.
    (?P<key>[A-Za-z_][\w.]*)        # dotted-path key starting with letter/underscore
    \)
    """,
    re.VERBOSE,
)

# File globs in scope.
SCOPE = [
    ("src/django_components", "**/*.py"),
    ("docs", "**/*.md"),
]


def short_key(raw_key: str) -> str:
    """
    Reduce a `django_components.app_settings.ComponentsSettings.dirs`-style
    dotted path to its short form `ComponentsSettings.dirs`.

    Rule: strip leading lowercase (module-name) segments until we hit a
    capitalized segment, OR until only one segment is left. This matches the
    SYMBOL_INDEX shape the new resolver uses (spike 11.5 §11.3): short
    class.attr leaf paths, never internal module prefixes.

    Examples:
        Component                                    -> Component
        Component.inject                             -> Component.inject
        app_settings.ComponentsSettings.dirs         -> ComponentsSettings.dirs
        components.dynamic.DynamicComponent          -> DynamicComponent
        context.ContextBehavior.DJANGO               -> ContextBehavior.DJANGO
        import_libraries                             -> import_libraries
        testing.djc_test                             -> djc_test

    """
    segments = raw_key.split(".")
    # Strip leading lowercase segments while there's more than one left.
    while len(segments) > 1 and segments[0][:1].islower():
        segments.pop(0)
    return ".".join(segments)


def rewrite_match(m: re.Match[str]) -> str:
    """
    Emit autorefs bracket cross-ref in the FINAL short form the new
    docs resolver will use (spike 11.5 §7.2, §11.3): `[text][ShortKey]`,
    always with an explicit key, never the `[X][]` empty-key form.

    Why always-explicit:

    - `[X][]` resolves to `[X][X]` per CommonMark, which then competes with
      whatever mkdocstrings stripped/normalised the text to. When `X` has
      backticks or parens (very common in our docstrings) the lookup key
      becomes ambiguous depending on the parser. Explicit keys avoid this.

    Why short keys now (instead of `django_components.X`):

    - The current mkdocs-autorefs index expects fully-qualified identifiers,
      so this codemod produces forms the OLD build can't resolve. That's
      fine: we don't publish until Phase 6 cutover. Phase 4 ships the new
      resolver and these short forms become the contract.
    """
    text = m.group("text")
    raw_key = m.group("key")
    return f"[{text}][{short_key(raw_key)}]"


def rewrite_file(path: Path, *, dry_run: bool) -> int:
    """Return the number of transformations made (or that would be made)."""
    content = path.read_text(encoding="utf-8")
    new_content, n_subs = LINK_RE.subn(rewrite_match, content)
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
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="In --dry-run, print N before/after samples (default 0).",
    )
    args = parser.parse_args()

    files = gather_files()
    total = 0
    file_count = 0
    samples_left = args.sample

    for f in files:
        n = rewrite_file(f, dry_run=args.dry_run)
        if n:
            total += n
            file_count += 1
            if args.dry_run and samples_left > 0:
                content = f.read_text(encoding="utf-8")
                for m in LINK_RE.finditer(content):
                    if samples_left <= 0:
                        break
                    samples_left -= 1
                    before = m.group(0)
                    after = rewrite_match(m)
                    rel = f.relative_to(REPO_ROOT)
                    print(f"  {rel}: {before!r} -> {after!r}")

    verb = "would change" if args.dry_run else "changed"
    print(f"{verb} {total} link(s) across {file_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
