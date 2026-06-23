"""
Snippet-path guard.

`pymdownx.snippets` is configured with `check_paths: true`, so a missing
`--8<-- "path"` target already fails the full build (Pass 2). This guard runs
the same check as a fast pre-build static scan, so a broken include is reported
up front with its source line instead of as a mid-build markdown error.

Paths resolve against the same base path as the pipeline: the repo root only
(matching the old mkdocs `base_path: .` config).

Spec: docs_site/design/DESIGN_spike_10.md section 3.7 (feature 3b.11).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import TYPE_CHECKING

from django.conf import settings

from .base import GuardResult

if TYPE_CHECKING:
    from .base import GuardContext

# Single-line form: --8<-- "path"   (optionally followed by :section markers)
_SNIPPET_LINE = re.compile(r'^\s*(?:;?)\s*-{2}8<-{2}\s+"(?P<path>[^"]+)"\s*$')
# Block-form delimiter line: a bare --8<-- on its own line toggles a block of
# quoted paths.
_SNIPPET_BLOCK_DELIM = re.compile(r"^\s*-{2}8<-{2}\s*$")
_QUOTED_PATH = re.compile(r'^\s*"(?P<path>[^"]+)"\s*$')


def _iter_snippet_refs(text: str) -> Iterator[tuple[int, str]]:
    """Yield (line_number, raw_path) for every snippet reference in the source."""
    in_block = False
    for lineno, line in enumerate(text.split("\n"), start=1):
        if in_block:
            if _SNIPPET_BLOCK_DELIM.match(line):
                in_block = False
                continue
            qm = _QUOTED_PATH.match(line)
            if qm:
                yield lineno, qm.group("path")
            continue
        m = _SNIPPET_LINE.match(line)
        if m:
            yield lineno, m.group("path")
        elif _SNIPPET_BLOCK_DELIM.match(line):
            in_block = True


def _resolve(raw_path: str) -> bool:
    """True if the snippet target exists under the repo root."""
    # Strip a trailing ":section" / ":start:end" selector if the bare path
    # alone doesn't exist (pymdownx allows section/line selectors after the path).
    candidates = [raw_path]
    if ":" in raw_path:
        candidates.append(raw_path.split(":", 1)[0])
    return any((settings.REPO_ROOT / cand).is_file() for cand in candidates)


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    for md in sorted(ctx.content_dir.rglob("*.md")):
        label = str(md.relative_to(ctx.content_dir))
        text = md.read_text(encoding="utf-8")
        for lineno, raw_path in _iter_snippet_refs(text):
            if not _resolve(raw_path):
                yield GuardResult.error(
                    guard="snippet_path",
                    message=f"Snippet target not found: {raw_path!r}",
                    source=label,
                    line=lineno,
                )
