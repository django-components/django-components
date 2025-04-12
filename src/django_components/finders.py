import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from django import VERSION as DJANGO_VERSION
from django.contrib.staticfiles.finders import BaseFinder
from django.contrib.staticfiles.utils import get_files
from django.core.checks import CheckMessage, Error, Warning
from django.core.files.storage import FileSystemStorage
from django.utils._os import safe_join

from django_components.app_settings import app_settings
from django_components.util.loader import get_component_dirs
from django_components.util.misc import any_regex_match, no_regex_match

# To keep track on which directories the finder has searched the static files.
searched_locations = []


# Custom Finder for staticfiles that searches for all files within the directories
# defined by `COMPONENTS.dirs`.
#
# This is what makes it possible to define JS and CSS files in the directories as
# defined by `COMPONENTS.dirs`, but still use the JS / CSS files with `static()` or
# `collectstatic` command.
class ComponentsFileSystemFinder(BaseFinder):
    """
    A static files finder based on `FileSystemFinder`.

    Differences:
    - This finder uses `COMPONENTS.dirs` setting to locate files instead of `STATICFILES_DIRS`.
    - Whether a file within `COMPONENTS.dirs` is considered a STATIC file is configured
      by `COMPONENTS.static_files_allowed` and `COMPONENTS.static_files_forbidden`.
    - If `COMPONENTS.dirs` is not set, defaults to `settings.BASE_DIR / "components"`
    """

    def __init__(self, app_names: Any = None, *args: Any, **kwargs: Any) -> None:
        component_dirs = [str(p) for p in get_component_dirs()]

        # NOTE: The rest of the __init__ is the same as `django.contrib.staticfiles.finders.FileSystemFinder`,
        # but using our locations instead of STATICFILES_DIRS.

        # List of locations with static files
        self.locations: List[Tuple[str, str]] = []

        # Maps dir paths to an appropriate storage instance
        self.storages: Dict[str, FileSystemStorage] = {}
        for root in component_dirs:
            if isinstance(root, (list, tuple)):
                prefix, root = root
            else:
                prefix = ""
            if (prefix, root) not in self.locations:
                self.locations.append((prefix, root))
        for prefix, root in self.locations:
            filesystem_storage = FileSystemStorage(location=root)
            filesystem_storage.prefix = prefix
            self.storages[root] = filesystem_storage

        super().__init__(*args, **kwargs)

    # NOTE: Based on `FileSystemFinder.check`
    def check(self, **kwargs: Any) -> List[CheckMessage]:
        errors: List[CheckMessage] = []
        if not isinstance(app_settings.DIRS, (list, tuple)):
            errors.append(
                Error(
                    "The COMPONENTS.dirs setting is not a tuple or list.",
                    hint="Perhaps you forgot a trailing comma?",
                    id="components.E001",
                )
            )
            return errors
        for root in app_settings.DIRS:
            if isinstance(root, (list, tuple)):
                prefix, root = root
                if prefix.endswith("/"):
                    errors.append(
                        Error(
                            "The prefix %r in the COMPONENTS.dirs setting must not end with a slash." % prefix,
                            id="staticfiles.E003",
                        )
                    )
            elif not os.path.isdir(root):
                errors.append(
                    Warning(
                        f"The directory '{root}' in the COMPONENTS.dirs setting does not exist.",
                        id="components.W004",
                    )
                )
        return errors

    # NOTE: Same as `FileSystemFinder.find`
    def find(self, path: str, **kwargs: Any) -> Union[List[str], str]:
        """
        Look for files in the extra locations as defined in COMPONENTS.dirs.
        """
        # Handle deprecated `all` parameter:
        # - In Django 5.2, the `all` parameter was deprecated in favour of `find_all`.
        # - Between Django 5.2 (inclusive) and 6.1 (exclusive), the `all` parameter was still
        #   supported, but an error was raised if both were provided.
        # - In Django 6.1, the `all` parameter was removed.
        #
        # See https://github.com/django/django/blob/5.2/django/contrib/staticfiles/finders.py#L58C9-L58C37
        # And https://github.com/django-components/django-components/issues/1119
        if DJANGO_VERSION >= (5, 2) and DJANGO_VERSION < (6, 1):
            find_all = self._check_deprecated_find_param(**kwargs)  # type: ignore
        elif DJANGO_VERSION >= (6, 1):
            find_all = kwargs.get("find_all", False)
        else:
            find_all = kwargs.get("all", False)

        matches: List[str] = []
        for prefix, root in self.locations:
            if root not in searched_locations:
                searched_locations.append(root)
            matched_path = self.find_location(root, path, prefix)
            if matched_path:
                if not find_all:
                    return matched_path
                matches.append(matched_path)
        return matches

    # NOTE: Same as `FileSystemFinder.find_local`, but we exclude Python/HTML files
    def find_location(self, root: str, path: str, prefix: Optional[str] = None) -> Optional[str]:
        """
        Find a requested static file in a location and return the found
        absolute path (or ``None`` if no match).
        """
        if prefix:
            prefix = "%s%s" % (prefix, os.sep)
            if not path.startswith(prefix):
                return None
            path = path.removeprefix(prefix)
        path = safe_join(root, path)

        if os.path.exists(path) and self._is_path_valid(path):
            return path
        return None

    # `Finder.list` is called from `collectstatic` command,
    # see https://github.com/django/django/blob/bc9b6251e0b54c3b5520e3c66578041cc17e4a28/django/contrib/staticfiles/management/commands/collectstatic.py#L126C23-L126C30  # noqa E501
    #
    # NOTE: This is same as `FileSystemFinder.list`, but we exclude Python/HTML files
    # NOTE 2: Yield can be annotated as Iterable, see https://stackoverflow.com/questions/38419654
    def list(self, ignore_patterns: List[str]) -> Iterable[Tuple[str, FileSystemStorage]]:
        """
        List all files in all locations.
        """
        for prefix, root in self.locations:
            # Skip nonexistent directories.
            if os.path.isdir(root):
                storage = self.storages[root]
                for path in get_files(storage, ignore_patterns):
                    if self._is_path_valid(path):
                        yield path, storage

    def _is_path_valid(self, path: str) -> bool:
        # Normalize patterns to regexes
        allowed_patterns = [
            # Convert suffixes like `.html` to regex `\.html$`
            re.compile(rf"\{p}$") if isinstance(p, str) else p
            for p in app_settings.STATIC_FILES_ALLOWED
        ]
        forbidden_patterns = [
            # Convert suffixes like `.html` to regex `\.html$`
            re.compile(rf"\{p}$") if isinstance(p, str) else p
            for p in app_settings.STATIC_FILES_FORBIDDEN
        ]
        return any_regex_match(path, allowed_patterns) and no_regex_match(path, forbidden_patterns)
