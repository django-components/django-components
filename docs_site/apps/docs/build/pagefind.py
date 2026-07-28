"""
Pagefind search-index generation (Phase 5a, feature 5a.1).

Pagefind is the retrieval layer behind the docs-site search. It runs *after*
the static build, scanning the written HTML in the output directory and
emitting a chunked index under `<output>/pagefind/` that the custom search UI
(Phase 5a Chunk 2) queries client-side. No server is involved.

Indexing scope is controlled from the page markup, not from here:

- `data-pagefind-body` on the article element whitelists the content region,
  so Pagefind indexes article prose only and ignores the header, sidebar, TOC,
  prev/next nav, and footer (see doc_page.py).
- `data-pagefind-weight` on the same element applies a per-page ranking boost
  derived from the `boost:` front-matter field.

The binary ships with the `pagefind[bin]` dependency; we invoke it via
`python -m pagefind` so it uses the same interpreter/venv as the build.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Pagefind writes its bundle to this subdirectory of the site by default.
PAGEFIND_OUTPUT_SUBDIR = "pagefind"


@dataclass
class PagefindOutcome:
    ok: bool
    message: str
    # Combined stdout+stderr from the pagefind CLI, for surfacing on failure.
    output: str = ""


def run_pagefind(output_dir: Path) -> PagefindOutcome:
    """
    Build the Pagefind search index over an already-built site directory.

    Returns a PagefindOutcome rather than raising so the build command can
    report a search-index failure without discarding a successful page build.
    """
    if not output_dir.is_dir():
        return PagefindOutcome(ok=False, message=f"Site directory not found: {output_dir}")

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pagefind", "--site", str(output_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        # The pagefind binary is missing - the `[bin]` extra wasn't installed.
        return PagefindOutcome(
            ok=False,
            message="pagefind binary not found; install with `uv sync --group docs` (pulls pagefind[bin]).",
        )

    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return PagefindOutcome(
            ok=False,
            message=f"pagefind exited with code {proc.returncode}",
            output=combined.strip(),
        )

    bundle = output_dir / PAGEFIND_OUTPUT_SUBDIR
    if not bundle.is_dir():
        return PagefindOutcome(
            ok=False,
            message=f"pagefind reported success but no index was written to {bundle}",
            output=combined.strip(),
        )

    return PagefindOutcome(ok=True, message=f"Search index written to {bundle}", output=combined.strip())
