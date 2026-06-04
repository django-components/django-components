"""
Build-time guardrails for examples.

These checks run during `docs_test` (or as part of a future guardrail harness)
to catch broken {% example %} references.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.docs.examples import ExampleInfo

EXAMPLE_RE = re.compile(r'{%\s*example\s+["\'](?P<name>[^"\']+)["\']')


def check_example_contracts(
    content_dir: Path,
    examples_dir: Path,
    registry: dict[str, ExampleInfo],
) -> list[str]:
    """
    Validate every {% example %} reference has a valid example directory.

    Scans all markdown files in content_dir for {% example "name" %} tags,
    then checks each referenced example against the required contract:
    - Directory exists at examples_dir/<name>/ with component.py and page.py
    - page.py defines a *Page Component subclass (verified via the registry)
    - That class has a nested View (needed for as_view() rendering)
    - At least one test_example_*.py exists (examples must be tested)
    - If fragments are declared, DocsExample.fragments is a dict

    Returns a list of error messages (empty = all good).
    """
    # Scan all markdown for {% example "name" %} references
    referenced: dict[str, list[Path]] = {}
    for md in content_dir.rglob("*.md"):
        for m in EXAMPLE_RE.finditer(md.read_text(encoding="utf-8")):
            referenced.setdefault(m.group("name"), []).append(md)

    errors: list[str] = []

    # Validate each referenced example against the contract
    for name, sources in referenced.items():
        source_list = ", ".join(str(s.relative_to(content_dir)) for s in sources)
        example_dir = examples_dir / name

        # Directory must exist
        if not example_dir.is_dir():
            errors.append(f"Example {name!r} (referenced in {source_list}): directory not found at {example_dir}")
            continue

        # Must have both component.py and page.py
        for required in ("component.py", "page.py"):
            if not (example_dir / required).exists():
                errors.append(f"Example {name!r} (referenced in {source_list}): missing {required}")

        # page.py must define a *Page Component (autodiscovery puts it in the registry)
        if name not in registry:
            errors.append(f"Example {name!r} (referenced in {source_list}): no *Page Component found in page.py")
            continue

        info = registry[name]

        # Page class needs a View for as_view() rendering
        if not hasattr(info.page_cls, "View"):
            errors.append(f"Example {name!r} (referenced in {source_list}): {info.page_cls.__name__} has no View class")

        # Every example must have test coverage
        if not any(example_dir.glob("test_example_*.py")):
            errors.append(f"Example {name!r} (referenced in {source_list}): no test_example_*.py file")

        if info.has_fragments and not isinstance(info.fragments, dict):
            errors.append(f"Example {name!r} (referenced in {source_list}): DocsExample.fragments must be a dict")

    return errors
