"""
Server discovery module for E2E tests.

This module automatically discovers and loads `server()` functions from test files
in the `tests/` directory. Specifically, it looks for test directories listed in
`pyproject.toml` in `tool.pytest.ini_options.testpaths` list.

Each `server()` function should return a dictionary mapping URL paths to view functions,
which will be automatically registered with the testserver.
"""
# ruff: noqa: G004

import ast
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from django.urls import path

try:
    import tomllib  # type: ignore[import-untyped]
except ImportError:
    # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


def discover_server_functions(tests_roots: list[Path] | None = None) -> list:
    """
    Discover all `server()` functions from test files and return URL patterns.

    When tests_root is None (default): finds the project root (directory containing
    pyproject.toml), reads [tool.pytest.ini_options] testpaths from it, and scans
    each listed directory for test_*.py files containing a server() function.

    When tests_roots is provided: scans each directory in the list.

    Returns a list of Django URL patterns (path() objects) that can be added
    to urlpatterns.

    Args:
        tests_roots: If None, use project root + pyproject.toml testpaths.
                    If provided, scan each directory in the list.

    Returns:
        List of Django URL patterns.

    """
    if tests_roots is not None:
        # Legacy: single directory to scan
        test_dirs = tests_roots
        project_root = tests_roots[0].parent
    else:
        # Find project root (directory containing pyproject.toml)
        current_file = Path(__file__).resolve()
        maybe_project_root = _find_project_root(current_file)
        if maybe_project_root is None:
            logger.warning("Could not find project root (directory containing pyproject.toml)")
            return []
        project_root = maybe_project_root

        # Read testpaths from pyproject.toml
        testpath_names = _get_testpaths_from_pyproject(project_root)
        if not testpath_names:
            return []
        test_dirs = [project_root / p for p in testpath_names]
        for d in test_dirs:
            if not d.exists():
                logger.warning(f"Test path from pyproject.toml does not exist: {d}")

    url_patterns = []

    # Collect test_*.py files from each test directory
    test_files: list[Path] = []
    for test_dir in test_dirs:
        if test_dir.exists():
            test_files.extend(test_dir.rglob("test_*.py"))

    logger.info(f"Scanning {len(test_files)} test files for server() functions...")

    for test_file in test_files:
        # Skip files in __pycache__ or other hidden directories
        if "__pycache__" in test_file.parts:
            continue

        # Check if file has server() function using AST
        if not _has_server_function(test_file):
            continue

        # Import and call server() function (project_root used for module resolution)
        server_result = _import_and_call_server(test_file, project_root)

        if server_result is None:
            continue

        # Convert dictionary to URL patterns
        for url_path, view_func in server_result.items():
            if not callable(view_func):
                logger.warning(f"View for path '{url_path}' in {test_file} is not callable")
                continue

            # Create Django URL pattern
            # Remove leading slash if present (path() handles it)
            clean_path = url_path.lstrip("/")
            url_patterns.append(path(clean_path, view_func))
            logger.info(f"Registered URL pattern: {url_path} -> {view_func.__name__}")

    logger.info(f"Discovered {len(url_patterns)} URL patterns from server() functions")
    return url_patterns


def _has_server_function(file_path: Path) -> bool:
    """
    Check if a Python file defines a module-level `server` function.

    Uses AST and only inspects top-level nodes.
    """
    try:
        with Path(file_path).open(encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        return any(isinstance(node, ast.FunctionDef) and node.name == "server" for node in tree.body)
    except (SyntaxError, UnicodeDecodeError, OSError) as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return False


def _import_and_call_server(module_path: Path, project_root: Path) -> dict[str, Any] | None:
    """
    Import a module and call its `server()` function.

    project_root is the directory containing pyproject.toml (used for sys.path and module names).

    Returns the dictionary returned by `server()`, or None if there's an error.
    """
    try:
        # Ensure project root is in sys.path for imports
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Convert file path to module name relative to project root
        # e.g., tests/test_component_js_e2e.py -> tests.test_component_js_e2e
        try:
            relative_path = module_path.relative_to(project_root)
        except ValueError:
            logger.warning(f"Could not compute relative path for {module_path} from {project_root}")
            return None

        module_name_parts = relative_path.with_suffix("").parts
        module_name = ".".join(module_name_parts)

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Could not create spec for {module_path}")
            return None

        module = importlib.util.module_from_spec(spec)

        # Execute the module (this will run setup_test_config() but it's safe
        # since Django is already configured by testserver settings)
        spec.loader.exec_module(module)

        # Check if server function exists
        if not hasattr(module, "server"):
            logger.warning(f"Module {module_name} does not have a server() function")
            return None

        # Call the server function
        server_func = module.server
        if not callable(server_func):
            logger.warning(f"server in {module_name} is not callable")
            return None

        result = server_func()

        # Validate that result is a dictionary
        if not isinstance(result, dict):
            logger.warning(f"server() in {module_name} returned {type(result)}, expected dict")
            return None

        logger.info(f"Successfully loaded server() from {module_name}")
        return result

    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to import or call server() from {module_path}: {e}")
        return None


def _find_project_root(start: Path) -> Path | None:
    """Walk up from start until we find a directory containing pyproject.toml."""
    current = start.resolve()
    while True:
        if (current / "pyproject.toml").is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _get_testpaths_from_pyproject(project_root: Path) -> list[str]:
    """Read [tool.pytest.ini_options] testpaths from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError) as e:
        logger.warning(f"Failed to read {pyproject_path}: {e}")
        return []
    try:
        testpaths = data["tool"]["pytest"]["ini_options"]["testpaths"]
    except KeyError:
        logger.warning(f"No [tool.pytest.ini_options] testpaths in {pyproject_path}")
        return []
    if not isinstance(testpaths, list) or not all(isinstance(p, str) for p in testpaths):
        logger.warning(f"testpaths in pyproject.toml must be a list of strings, got {testpaths!r}")
        return []
    return testpaths
