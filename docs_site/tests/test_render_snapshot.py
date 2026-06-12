"""
Snapshot regression scaffold for the render pipeline (feature 3b.17).

Snapshots the *content* HTML (`wrap_in_layout=False`) of a few representative
markdown fixtures, so a change in the markdown extension stack (admonitions,
Pygments highlighting, TOC anchors, link rewriting) shows up as a reviewable
diff. We snapshot content only - not the full page - so version bumps and
chrome tweaks don't churn these baselines.

Per spike 10, this starts small (3 fixtures) and stays a standalone pytest;
it is intentionally NOT wired into docs_build_check until the renderer settles
(Phase 5). Update baselines with: uv run pytest tests/test_render_snapshot.py
--snapshot-update
"""

from __future__ import annotations

import pygments_djc  # noqa: F401 -- register djc_py for highlighting
from apps.docs.build.pipeline import render_page

FIXTURES = {
    "headings_and_prose": (
        "# Title\n\n"
        "Intro paragraph with `inline code` and a [link](https://example.com).\n\n"
        "## Section\n\n"
        "Some **bold** and _italic_ text.\n\n"
        "### Subsection\n\n"
        "- one\n- two\n- three\n"
    ),
    "code_blocks": (
        "# Code\n\n"
        "```python\n"
        "def f(x):\n"
        "    return x + 1\n"
        "```\n\n"
        "```djc_py\n"
        "class Button(Component):\n"
        '    template = "<button>{{ label }}</button>"\n'
        "```\n"
    ),
    "admonition_and_table": (
        "# Rich\n\n!!! note\n    A note admonition body.\n\n| Col A | Col B |\n| ----- | ----- |\n| 1     | 2     |\n"
    ),
}


def test_render_snapshots(snapshot) -> None:  # type: ignore[no-untyped-def]
    rendered = {name: render_page(src, wrap_in_layout=False).html for name, src in FIXTURES.items()}
    assert rendered == snapshot
