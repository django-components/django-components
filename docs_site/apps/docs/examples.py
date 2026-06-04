"""
Example autodiscovery and registry.

Walks EXAMPLES_DIR (docs_old/examples/) and imports each example's component.py
and page.py, finding the *Page Component subclass. The registry is cached and
shared by the build command, dev server, and {% example %} template tag.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django_components.component import Component


@dataclass
class ExampleInfo:
    name: str
    page_cls: type[Component]
    example_dir: Path
    has_fragments: bool = False
    # Maps fragment name -> query params dict, e.g. {"alpine": {"type": "alpine"}}
    fragments: dict[str, dict[str, str]] = field(default_factory=dict)


_registry: dict[str, ExampleInfo] | None = None


def get_example_registry() -> dict[str, ExampleInfo]:
    """
    Return the cached example registry, discovering on first call.

    The registry maps example directory names (e.g. "fragments") to ExampleInfo
    objects. It is populated once by walking EXAMPLES_DIR, importing each
    example's component.py and page.py, and finding the *Page Component class.

    Called by:
    - build_docs (at startup, before rendering pages that use {% example %})
    - docs_serve (on each request, but the cache makes it a no-op after first call)
    - {% example %} tag (to look up the ExampleInfo for a given name)
    """
    global _registry  # noqa: PLW0603
    if _registry is not None:
        return _registry
    _registry = _discover_examples(settings.EXAMPLES_DIR)
    return _registry


def _discover_examples(examples_dir: Path) -> dict[str, ExampleInfo]:
    from django_components.component import Component  # noqa: PLC0415

    registry: dict[str, ExampleInfo] = {}

    if not examples_dir.is_dir():
        return registry

    for example_dir in sorted(examples_dir.iterdir()):
        if not example_dir.is_dir():
            continue

        name = example_dir.name
        component_file = example_dir / "component.py"
        page_file = example_dir / "page.py"

        if not component_file.exists() or not page_file.exists():
            continue

        # Import both modules so components get registered with djc
        _import_module_file(component_file, name, "component")
        page_module = _import_module_file(page_file, name, "page")

        if page_module is None:
            continue

        # Find the *Page class (e.g. FragmentsPage, TabsPage)
        page_cls = _find_page_class(page_module, Component)
        if page_cls is None:
            continue

        # Read fragment declarations from DocsExample.fragments if present
        docs_example = getattr(page_cls, "DocsExample", None)
        fragments = getattr(docs_example, "fragments", {}) if docs_example else {}

        registry[name] = ExampleInfo(
            name=name,
            page_cls=page_cls,
            example_dir=example_dir,
            has_fragments=bool(fragments),
            fragments=dict(fragments),
        )

    return registry


def _find_page_class(module: object, component_base: type) -> type[Component] | None:
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, component_base)
            and attr is not component_base
            and attr_name.endswith("Page")
        ):
            return attr
    return None


def _import_module_file(py_file: Path, example_name: str, module_type: str) -> object | None:
    module_name = f"examples.dynamic.{example_name}.{module_type}"

    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, py_file)
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
