import importlib
import os
from typing import Callable, List, Optional

from django_components.util.loader import get_component_files
from django_components.util.logger import logger

# In tests, we want to capture which modules have been loaded, so we can
# clean them up between tests. But there's no need to track this in
# production.
LOADED_MODULES: List[str] = []


def autodiscover(
    map_module: Optional[Callable[[str], str]] = None,
) -> List[str]:
    """
    Search for all python files in
    [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
    and
    [`COMPONENTS.app_dirs`](../settings#django_components.app_settings.ComponentsSettings.app_dirs)
    and import them.

    See [Autodiscovery](../../concepts/fundamentals/autodiscovery).

    NOTE: Subdirectories and files starting with an underscore `_` (except for `__init__.py` are ignored.

    Args:
        map_module (Callable[[str], str], optional): Map the module paths with `map_module` function.\
        This serves as an escape hatch for when you need to use this function in tests.

    Returns:
        List[str]: A list of module paths of imported files.

    To get the same list of modules that `autodiscover()` would return, but without importing them, use
    [`get_component_files()`](../api#django_components.get_component_files):

    ```python
    from django_components import get_component_files

    modules = get_component_files(".py")
    ```
    """
    modules = get_component_files(".py")
    logger.debug(f"Autodiscover found {len(modules)} files in component directories.")
    return _import_modules([entry.dot_path for entry in modules], map_module)


def import_libraries(
    map_module: Optional[Callable[[str], str]] = None,
) -> List[str]:
    """
    Import modules set in
    [`COMPONENTS.libraries`](../settings#django_components.app_settings.ComponentsSettings.libraries)
    setting.

    See [Autodiscovery](../../concepts/fundamentals/autodiscovery).

    Args:
        map_module (Callable[[str], str], optional): Map the module paths with `map_module` function.\
        This serves as an escape hatch for when you need to use this function in tests.

    Returns:
        List[str]: A list of module paths of imported files.

    **Examples:**

    Normal usage - load libraries after Django has loaded
    ```python
    from django_components import import_libraries

    class MyAppConfig(AppConfig):
        def ready(self):
            import_libraries()
    ```

    Potential usage in tests
    ```python
    from django_components import import_libraries

    import_libraries(lambda path: path.replace("tests.", "myapp."))
    ```
    """
    from django_components.app_settings import app_settings

    return _import_modules(app_settings.LIBRARIES, map_module)


def _import_modules(
    modules: List[str],
    map_module: Optional[Callable[[str], str]] = None,
) -> List[str]:
    imported_modules: List[str] = []
    for module_name in modules:
        if map_module:
            module_name = map_module(module_name)

        # This imports the file and runs it's code. So if the file defines any
        # django components, they will be registered.
        logger.debug(f'Importing module "{module_name}"')
        importlib.import_module(module_name)
        imported_modules.append(module_name)

        # In tests tagged with `@djc_test`, we want to capture the modules that
        # are imported so we can clean them up between tests.
        if os.environ.get("DJC_TESTING"):
            LOADED_MODULES.append(module_name)

    return imported_modules
