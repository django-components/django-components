import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NamedTuple

from django.apps import apps
from django.conf import settings

from django_components.app_settings import ComponentsSettings, app_settings
from django_components.util.logger import logger


def get_component_dirs(include_apps: bool = True) -> list[Path]:
    """
    Get directories that may contain component files.

    This is the heart of all features that deal with filesystem and file lookup.
    Autodiscovery, Django template resolution, static file resolution - They all use this.

    Args:
        include_apps (bool, optional): Include directories from installed Django apps.\
            Defaults to `True`.

    Returns:
        list[Path]: A list of directories that may contain component files.

    `get_component_dirs()` searches for dirs set in
    [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
    settings. If none set, defaults to searching for a `"components"` app.

    In addition to that, also all installed Django apps are checked whether they contain
    directories as set in
    [`COMPONENTS.app_dirs`](../settings#django_components.app_settings.ComponentsSettings.app_dirs)
    (e.g. `[app]/components`).

    **Notes:**

    - Paths that do not point to directories are ignored.

    - `BASE_DIR` setting is required.

    - The paths in [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
        must be absolute paths.

    """
    # Allow to configure from settings which dirs should be checked for components
    component_dirs = app_settings.DIRS

    # TODO_REMOVE_IN_V1
    raw_component_settings = getattr(settings, "COMPONENTS", {})
    if isinstance(raw_component_settings, dict):
        raw_dirs_value = raw_component_settings.get("dirs", None)
    elif isinstance(raw_component_settings, ComponentsSettings):
        raw_dirs_value = raw_component_settings.dirs
    else:
        raw_dirs_value = None
    is_component_dirs_set = raw_dirs_value is not None
    is_legacy_paths = (
        # Use value of `STATICFILES_DIRS` ONLY if `COMPONENT.dirs` not set
        not is_component_dirs_set and getattr(settings, "STATICFILES_DIRS", None)
    )
    if is_legacy_paths:
        # NOTE: For STATICFILES_DIRS, we use the defaults even for empty list.
        # We don't do this for COMPONENTS.dirs, so user can explicitly specify "NO dirs".
        component_dirs = settings.STATICFILES_DIRS or [settings.BASE_DIR / "components"]
    # END TODO_REMOVE_IN_V1

    source = "STATICFILES_DIRS" if is_legacy_paths else "COMPONENTS.dirs"

    logger.debug(
        "get_component_dirs will search for valid dirs from following options:\n"
        + "\n".join([f" - {d!s}" for d in component_dirs]),
    )

    # Add `[app]/[APP_DIR]` to the directories. This is, by default `[app]/components`
    app_paths: list[Path] = []
    if include_apps:
        for conf in apps.get_app_configs():
            for app_dir in app_settings.APP_DIRS:
                comps_path = Path(conf.path).joinpath(app_dir)
                if comps_path.exists():
                    app_paths.append(comps_path)

    directories: set[Path] = set(app_paths)

    # Validate and add other values from the config
    for component_dir in component_dirs:
        # Consider tuples for STATICFILES_DIRS (See #489)
        # See https://docs.djangoproject.com/en/5.2/ref/settings/#prefixes-optional
        if isinstance(component_dir, (tuple, list)):
            component_dir = component_dir[1]  # noqa: PLW2901
        try:
            Path(component_dir)
        except TypeError:
            logger.warning(
                f"{source} expected str, bytes or os.PathLike object, or tuple/list of length 2. "
                f"See Django documentation for STATICFILES_DIRS. Got {type(component_dir)} : {component_dir}",
            )
            continue

        if not Path(component_dir).is_absolute():
            raise ValueError(f"{source} must contain absolute paths, got '{component_dir}'")
        directories.add(Path(component_dir).resolve())

    logger.debug(
        "get_component_dirs matched following template dirs:\n" + "\n".join([f" - {d!s}" for d in directories]),
    )
    return list(directories)


class ComponentFileEntry(NamedTuple):
    """Result returned by [`get_component_files()`](../api#django_components.get_component_files)."""

    dot_path: str
    """The python import path for the module. E.g. `app.components.mycomp`"""
    filepath: Path
    """The filesystem path to the module. E.g. `/path/to/project/app/components/mycomp.py`"""


def get_component_files(suffix: str | None = None) -> list[ComponentFileEntry]:
    """
    Search for files within the component directories (as defined in
    [`get_component_dirs()`](../api#django_components.get_component_dirs)).

    Requires `BASE_DIR` setting to be set.

    Subdirectories and files starting with an underscore `_` (except `__init__.py`) are ignored.

    Args:
        suffix (str | None, optional): The suffix to search for. E.g. `.py`, `.js`, `.css`.\
            Defaults to `None`, which will search for all files.

    Returns:
        list[ComponentFileEntry] A list of entries that contain both the filesystem path and \
            the python import path (dot path).

    **Example:**

    ```python
    from django_components import get_component_files

    modules = get_component_files(".py")
    ```

    """
    search_glob = f"**/*{suffix}" if suffix else "**/*"

    dirs = get_component_dirs(include_apps=False)
    component_filepaths = _search_dirs(dirs, search_glob)

    if hasattr(settings, "BASE_DIR") and settings.BASE_DIR:
        project_root = settings.BASE_DIR
    else:
        # Fallback for getting the root dir, see https://stackoverflow.com/a/16413955/9788634
        project_root = Path.cwd()

    # NOTE: We handle dirs from `COMPONENTS.dirs` and from individual apps separately.
    modules: list[ComponentFileEntry] = []

    # First let's handle the dirs from `COMPONENTS.dirs`
    #
    # Because for dirs in `COMPONENTS.dirs`, we assume they will be nested under `BASE_DIR`,
    # and that `BASE_DIR` is the current working dir (CWD). So the path relatively to `BASE_DIR`
    # is ALSO the python import path.
    for filepath in component_filepaths:
        module_path = _filepath_to_python_module(filepath, project_root, None)
        # Ignore files starting with dot `.` or files in dirs that start with dot.
        #
        # If any of the parts of the path start with a dot, e.g. the filesystem path
        # is `./abc/.def`, then this gets converted to python module as `abc..def`
        #
        # NOTE: This approach also ignores files:
        #   - with two dots in the middle (ab..cd.py)
        #   - an extra dot at the end (abcd..py)
        #   - files outside of the parent component (../abcd.py).
        # But all these are NOT valid python modules so that's fine.
        if ".." in module_path:
            continue

        entry = ComponentFileEntry(dot_path=module_path, filepath=filepath)
        modules.append(entry)

    # For for apps, the directories may be outside of the project, e.g. in case of third party
    # apps. So we have to resolve the python import path relative to the package name / the root
    # import path for the app.
    # See https://github.com/django-components/django-components/issues/669
    for conf in apps.get_app_configs():
        for app_dir in app_settings.APP_DIRS:
            comps_path = Path(conf.path).joinpath(app_dir)
            if not comps_path.exists():
                continue
            app_component_filepaths = _search_dirs([comps_path], search_glob)
            for filepath in app_component_filepaths:
                app_component_module = _filepath_to_python_module(filepath, conf.path, conf.name)
                entry = ComponentFileEntry(dot_path=app_component_module, filepath=filepath)
                modules.append(entry)

    return modules


def _filepath_to_python_module(
    file_path: Path | str,
    root_fs_path: str | Path,
    root_module_path: str | None,
) -> str:
    """
    Derive python import path from the filesystem path.

    Example:
    - If project root is `/path/to/project`
    - And file_path is `/path/to/project/app/components/mycomp.py`
    - Then the path relative to project root is `app/components/mycomp.py`
    - Which we then turn into python import path `app.components.mycomp`

    """
    path_cls = PureWindowsPath if os.name == "nt" else PurePosixPath

    rel_path = path_cls(file_path).relative_to(path_cls(root_fs_path))
    rel_path_parts = rel_path.with_suffix("").parts
    module_name = ".".join(rel_path_parts)

    # Combine with the base module path
    full_module_name = f"{root_module_path}.{module_name}" if root_module_path else module_name
    full_module_name = full_module_name.removesuffix(".__init__")  # Remove the trailing `.__init__`

    return full_module_name


def _search_dirs(dirs: list[Path], search_glob: str) -> list[Path]:
    """
    Search the directories for the given glob pattern. Glob search results are returned
    as a flattened list.
    """
    matched_files: list[Path] = []
    for directory in dirs:
        for path in Path(directory).rglob(search_glob):
            # Skip any subdirectory or file (under the top-level directory) that starts with an underscore
            rel_dir_parts = list(path.relative_to(directory).parts)
            name_part = rel_dir_parts.pop()
            if any(part.startswith("_") for part in rel_dir_parts):
                continue
            if name_part.startswith("_") and name_part != "__init__.py":
                continue

            matched_files.append(path)

    return matched_files


def resolve_file(filepath: str, dirs: list[Path] | None = None) -> Path | None:
    dirs = dirs if dirs is not None else get_component_dirs()
    for directory in dirs:
        full_path = Path(directory) / filepath
        if full_path.exists():
            return full_path
    return None
