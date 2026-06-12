"""
Docs-site guardrail harness.

Runs every registered guard against a single GuardContext, collects the
results, and decides the outcome from their severities:

- any ERROR            -> fail
- any WARNING + strict -> fail
- otherwise            -> pass

Each guard is a small module exposing `check(ctx) -> Iterator[GuardResult]`.
The shared SiteIndex (built once by the caller) backs every post-build guard.

Spec: docs_site/design/DESIGN_spike_10.md sections 4 (severity) and 6 (harness).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import (
    alt_text,
    anchor,
    asset,
    code_lang,
    example_contract,
    fence_validator,
    headings,
    html_wellformed,
    internal_link,
    lexer_alias,
    nav,
    single_h1,
    snippet_path,
)
from .base import GuardContext, GuardResult, Severity

if TYPE_CHECKING:
    from .base import Guard

__all__ = [
    "GUARDS",
    "GuardContext",
    "GuardResult",
    "Severity",
    "format_report",
    "run_guards",
]

# Guards in run order: source scans first (cheapest, no build needed), then the
# post-build checks that read the SiteIndex.
GUARDS: list[Guard] = [
    # --- source / pre-build scans ---
    fence_validator.check,
    lexer_alias.check,
    code_lang.check,
    snippet_path.check,
    nav.check,
    example_contract.check,
    # --- post-build (SiteIndex) ---
    internal_link.check,
    anchor.check,
    asset.check,
    html_wellformed.check,
    single_h1.check,
    alt_text.check,
    headings.check,
]


def run_guards(ctx: GuardContext, *, strict: bool = False) -> tuple[list[GuardResult], bool]:
    """
    Run every guard and return (results, ok).

    `ok` is False if any ERROR was produced, or (under strict) any WARNING.
    A guard that raises is itself reported as an ERROR so one broken guard can't
    silently pass the suite.
    """
    results: list[GuardResult] = []
    for guard in GUARDS:
        try:
            results.extend(guard(ctx))
        except Exception as e:
            results.append(
                GuardResult.error(
                    guard=getattr(guard, "__module__", "unknown").rsplit(".", 1)[-1],
                    message=f"Guard crashed: {type(e).__name__}: {e}",
                )
            )

    has_error = any(r.severity is Severity.ERROR for r in results)
    has_warning = any(r.severity is Severity.WARNING for r in results)
    ok = not has_error and not (strict and has_warning)
    return results, ok


def format_report(results: list[GuardResult]) -> str:
    """Render guard results as a human-readable, severity-grouped report."""
    if not results:
        return "All guards passed (no findings)."

    order = [Severity.ERROR, Severity.WARNING, Severity.INFO]
    lines: list[str] = []
    for severity in order:
        group = [r for r in results if r.severity is severity]
        if not group:
            continue
        lines.append(f"{severity.value.upper()}S ({len(group)}):")
        for r in sorted(group, key=lambda x: (x.guard, x.source or "", x.line or 0)):
            loc = r.source or "-"
            if r.line:
                loc = f"{loc}:{r.line}"
            lines.append(f"  [{r.guard}] {loc}")
            lines.append(f"      {r.message}")
    counts = {s: sum(1 for r in results if r.severity is s) for s in order}
    lines.append("")
    lines.append(
        f"Totals: {counts[Severity.ERROR]} errors, {counts[Severity.WARNING]} warnings, {counts[Severity.INFO]} info"
    )
    return "\n".join(lines)
