"""
Example-page contract guard.

Validates that every `{% example "name" %}` reference resolves to a directory
that follows the example contract: component.py + page.py, a `*Page` Component
(found via the autodiscovery registry), a nested `View`, a test file, and a
well-formed `fragments` dict when fragments are declared.

Migrated from the Phase-2 `build/guards.py` into the unified harness.

Spec: docs_site/design/DESIGN_spike_10.md section 3.6 (feature 2.7).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import TYPE_CHECKING

from .base import GuardResult

if TYPE_CHECKING:
    from pathlib import Path

    from apps.docs.examples import ExampleInfo

    from .base import GuardContext

_EXAMPLE_RE = re.compile(r'{%\s*example\s+["\'](?P<name>[^"\']+)["\']')


def _referenced_examples(content_dir: Path) -> dict[str, list[str]]:
    """Map each referenced example name -> the source files that reference it."""
    referenced: dict[str, list[str]] = {}
    for md in sorted(content_dir.rglob("*.md")):
        label = str(md.relative_to(content_dir))
        for m in _EXAMPLE_RE.finditer(md.read_text(encoding="utf-8")):
            referenced.setdefault(m.group("name"), []).append(label)
    return referenced


def check(ctx: GuardContext) -> Iterator[GuardResult]:
    registry: dict[str, ExampleInfo] = ctx.example_registry or {}

    for name, sources in _referenced_examples(ctx.content_dir).items():
        source = ", ".join(sources)
        example_dir = ctx.examples_dir / name

        if not example_dir.is_dir():
            yield GuardResult.error(
                guard="example_contract",
                message=f"Example {name!r} directory not found at {example_dir}",
                source=source,
            )
            continue

        missing_file = False
        for required in ("component.py", "page.py"):
            if not (example_dir / required).exists():
                yield GuardResult.error(
                    guard="example_contract",
                    message=f"Example {name!r} is missing required file: {required}",
                    source=source,
                )
                missing_file = True
        if missing_file:
            continue

        # page.py must define a *Page Component (autodiscovery registers it).
        if name not in registry:
            yield GuardResult.error(
                guard="example_contract",
                message=f"Example {name!r} has no *Page Component in page.py",
                source=source,
            )
            continue

        info = registry[name]
        if not hasattr(info.page_cls, "View"):
            yield GuardResult.error(
                guard="example_contract",
                message=f"Example {name!r}: {info.page_cls.__name__} has no nested View class",
                source=source,
            )

        if not any(example_dir.glob("test_example_*.py")):
            yield GuardResult.error(
                guard="example_contract",
                message=f"Example {name!r} has no test_example_*.py file",
                source=source,
            )

        if info.has_fragments and not isinstance(info.fragments, dict):
            yield GuardResult.error(
                guard="example_contract",
                message=f"Example {name!r}: DocsExample.fragments must be a dict",
                source=source,
            )
