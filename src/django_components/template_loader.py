"""Template loader that loads templates from each Django app's "components" directory."""

from pathlib import Path

from django.template.loaders.filesystem import Loader as FilesystemLoader

from django_components.util.loader import get_component_dirs


class DjcLoader(FilesystemLoader):
    def get_dirs(self, include_apps: bool = True) -> list[Path]:
        """
        Prepare directories that may contain component files:

        Searches for dirs set in `COMPONENTS.dirs` settings. If none set, defaults to searching
        for a "components" app. The dirs in `COMPONENTS.dirs` must be absolute paths.

        In addition to that, also all apps are checked for `[app]/components` dirs.

        Paths are accepted only if they resolve to a directory.
        E.g. `/path/to/django_project/my_app/components/`.

        `BASE_DIR` setting is required.
        """
        return get_component_dirs(include_apps)


# NOTE: Django's template loaders have the pattern of using the `Loader` class name.
#       However, this then makes it harder to track and distinguish between different loaders.
#       So internally we use the name `DjcLoader` instead.
#       But for public API we use the name `Loader` to match Django.
Loader = DjcLoader
