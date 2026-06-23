"""
Core types for the docs-site guardrail harness.

A guard is a plain function `(GuardContext) -> Iterator[GuardResult]`. The
harness (see __init__.py) runs every registered guard, collects the results,
and decides the exit code from their severities.

Spec: docs_site/design/DESIGN_spike_10.md section 6.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from apps.docs.build.site_index import SiteIndex
    from apps.docs.examples import ExampleInfo


class Severity(Enum):
    """How a guard result affects the build outcome."""

    ERROR = "error"  # fails every build
    WARNING = "warning"  # fails only under --strict
    INFO = "info"  # never fails; informational only


@dataclass(frozen=True)
class GuardResult:
    guard: str  # the guard name, e.g. "internal_link"
    severity: Severity
    message: str
    source: str | None = None  # file / page the issue is on (for the report)
    line: int | None = None

    @classmethod
    def error(cls, guard: str, message: str, source: str | None = None, line: int | None = None) -> GuardResult:
        return cls(guard=guard, severity=Severity.ERROR, message=message, source=source, line=line)

    @classmethod
    def warning(cls, guard: str, message: str, source: str | None = None, line: int | None = None) -> GuardResult:
        return cls(guard=guard, severity=Severity.WARNING, message=message, source=source, line=line)

    @classmethod
    def info(cls, guard: str, message: str, source: str | None = None, line: int | None = None) -> GuardResult:
        return cls(guard=guard, severity=Severity.INFO, message=message, source=source, line=line)


@dataclass
class GuardContext:
    """Everything the guards need, assembled once before the suite runs."""

    content_dir: Path  # docs_site/content (markdown source)
    examples_dir: Path  # docs_site/examples (runnable examples)
    nav_path: Path  # content/_nav.yml
    static_dir: Path  # docs_site/static (source of /static/* assets)
    # Post-build index of the rendered site. None during pre-build-only runs.
    site_index: SiteIndex | None = None
    # name -> ExampleInfo, from the example autodiscovery registry.
    example_registry: dict[str, ExampleInfo] | None = None
    # docs_site/versions/ (the committed version tree). Only set when running the
    # version guards (docs_versions_check); None for the per-build content suite.
    versions_root: Path | None = None


# A guard is a function that yields zero or more results for a given context.
Guard = Callable[["GuardContext"], Iterator[GuardResult]]
