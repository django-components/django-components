"""
Template loader that loads templates from each Django app's "components" directory.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Generator, List, Optional, Type

from django.core.exceptions import SuspiciousFileOperation
from django.template import Origin, Template, TemplateDoesNotExist
from django.template.loaders.filesystem import Loader as FilesystemLoader
from django.utils._os import safe_join

from django_components.util.loader import get_component_dirs

if TYPE_CHECKING:
    from django_components.component import Component


class DjcLoader(FilesystemLoader):
    def get_dirs(self, include_apps: bool = True) -> List[Path]:
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

    # Same as `FilesystemLoader.get_template()` from Django v5.1, except optionally
    # accepts a Component class that the template belongs to.
    # This is used by `load_component_template()` to associate the template with the component class.
    def get_template(
        self,
        template_name: str,
        skip: Optional[List[Origin]] = None,
        component_cls: Optional[Type["Component"]] = None,
    ) -> Template:
        tried = []

        for origin in self.get_template_sources(template_name, component_cls=component_cls):
            if skip is not None and origin in skip:
                tried.append((origin, "Skipped to avoid recursion"))
                continue

            try:
                contents = self.get_contents(origin)
            except TemplateDoesNotExist:
                tried.append((origin, "Source does not exist"))
                continue
            else:
                return Template(
                    contents,
                    origin,
                    origin.template_name,
                    self.engine,
                )

        raise TemplateDoesNotExist(template_name, tried=tried)

    # Same as `FilesystemLoader.get_template_sources()` from Django v5.1, except optionally
    # accepts a Component class that the template belongs to.
    # This is used by `load_component_template()` to associate the template with the component class.
    def get_template_sources(
        self,
        template_name: str,
        component_cls: Optional[Type["Component"]] = None,
    ) -> Generator[Origin, None, None]:
        for template_dir in self.get_dirs():
            try:
                name = safe_join(template_dir, template_name)
            except SuspiciousFileOperation:
                # The joined path was located outside of this template_dir
                # (it might be inside another one, so this isn't fatal).
                continue

            origin = Origin(
                name=name,
                template_name=template_name,
                loader=self,
            )

            if component_cls:
                from django_components.template import _set_origin_component

                _set_origin_component(origin, component_cls)

            yield origin

    # Same as `FilesystemLoader.get_contents()` from Django v5.1, except that it defaults
    # to `file_charset` UTF-8 if engine is not set.
    # This is used by `load_component_template()` so we don't need an instance of Django's `Engine`
    # to call `DjcLoader.get_template()`.
    def get_contents(self, origin: Origin) -> str:
        encoding = self.engine.file_charset if self.engine else "utf-8"
        try:
            with open(origin.name, encoding=encoding) as fp:
                return fp.read()
        except FileNotFoundError:
            raise TemplateDoesNotExist(origin)


# NOTE: Django's template loaders have the pattern of using the `Loader` class name.
#       However, this then makes it harder to track and distinguish between different loaders.
#       So internally we use the name `DjcLoader` instead.
#       But for public API we use the name `Loader` to match Django.
Loader = DjcLoader
