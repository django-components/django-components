"""
Post-build HTML minification (Phase 5c, feature 5c.14).

A final pass over every built `*.html`, replacing the old mkdocs-minify-plugin
(abandoned htmlmin2 backend) with minify-html (Rust-backed, MIT). GitHub Pages
already gzips responses, so the win is modest (~8%), but it's cheap and reduces
the *parsed* HTML size (which affects time-to-render).

Conservative config: keep closing tags and the html/head opening tags (safer for
HTML5), keep spaces between attributes. minify-html handles `<pre>` natively and
leaves whitespace-sensitive regions alone; the snapshot tests + a focused unit
test guard against `<pre>` / SVG whitespace regressions.

The import is lazy + guarded so a build without minify-html installed simply
skips minification rather than failing.

Spec: docs_site/design/DESIGN_spike_9.md section 2.6.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# minify-html option flags (minify_html.minify kwargs, v0.18+). The conservative
# behaviours we want are the library defaults: doctype kept, attribute values
# stay spec-compliant, spaces between attributes preserved, `<pre>` whitespace
# untouched. We only opt INTO keeping the HTML5-safer closing / html+head tags
# and minifying inline CSS. Inline JS minification is left OFF so the JSON-LD
# `<script type="application/ld+json">` blocks are never touched.
_MINIFY_CONFIG = {
    "minify_css": True,
    "keep_closing_tags": True,
    "keep_html_and_head_opening_tags": True,
}


@dataclass
class MinifyOutcome:
    files: int = 0  # html files minified
    before: int = 0  # total bytes before
    after: int = 0  # total bytes after
    skipped_reason: str = ""  # set when minify-html isn't available


def minify_site(output_dir: Path, *, log: Callable[[str], None] = lambda _msg: None) -> MinifyOutcome:
    """Minify every `*.html` under `output_dir` in place. No-op if minify-html is missing."""
    try:
        import minify_html  # noqa: PLC0415
    except ImportError:
        log("minify-html not installed; skipping HTML minification")
        return MinifyOutcome(skipped_reason="minify-html-missing")

    outcome = MinifyOutcome()
    for html_path in output_dir.rglob("*.html"):
        src = html_path.read_text(encoding="utf-8")
        out = minify_html.minify(src, **_MINIFY_CONFIG)
        html_path.write_text(out, encoding="utf-8")
        outcome.files += 1
        outcome.before += len(src)
        outcome.after += len(out)
    return outcome
