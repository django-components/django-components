import importlib.util
import sys
from pathlib import Path

from django.conf import settings

# Keep track of what we've already discovered to make subsequent calls a noop
_discovered_examples: set[str] = set()


def discover_example_modules() -> list[str]:
    """
    Find and import `component.py` and `page.py` files from example directories
    `docs/examples/*/` (e.g. `docs/examples/form/component.py`).

    These files will be importable from other modules like:

    ```python
    from examples.dynamic.form.component import Form
    # or
    from examples.dynamic.form.page import FormPage
    ```

    Components will be also registered with the ComponentRegistry, so they can be used
    in the templates via the `{% component %}` tag like:

    ```django
    {% component "form" / %}
    ```

    This function is idempotent - calling it multiple times will not re-import modules.
    """
    # Skip if we've already discovered examples
    if _discovered_examples:
        return list(_discovered_examples)

    docs_examples_dir: Path = settings.EXAMPLES_DIR
    if not docs_examples_dir.exists():
        raise FileNotFoundError(f"Docs examples directory not found: {docs_examples_dir}")

    for example_dir in docs_examples_dir.iterdir():
        if not example_dir.is_dir():
            continue

        example_name = example_dir.name

        component_file = example_dir / "component.py"
        if component_file.exists():
            _import_module_file(component_file, example_name, "component")

        page_file = example_dir / "page.py"
        if page_file.exists():
            _import_module_file(page_file, example_name, "page")

        # Mark this example as discovered
        _discovered_examples.add(example_name)

    return list(_discovered_examples)


def _import_module_file(py_file: Path, example_name: str, module_type: str):
    """
    Dynamically import a python file as a module.

    This file will then be importable from other modules like:

    ```python
    from examples.dynamic.form.component import Form
    # or
    from examples.dynamic.form.page import FormPage
    ```
    """
    module_name = f"examples.dynamic.{example_name}.{module_type}"

    # Skip if module is already imported
    if module_name in sys.modules:
        return

    try:
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec or not spec.loader:
            raise ValueError(f"Failed to load {module_type} {example_name}/{py_file.name}")

        module = importlib.util.module_from_spec(spec)
        # Add to sys.modules so the contents can be imported from other modules
        # via Python import system.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        print(f"Loaded example {module_type}: {example_name}/{py_file.name}")
    except Exception as e:  # noqa: BLE001
        print(f"Failed to load {module_type} {example_name}/{py_file.name}: {e}")
