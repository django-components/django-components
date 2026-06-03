# ruff: noqa: PLC0415
import re
from pathlib import Path
from typing import Any

from django.apps import AppConfig
from django.template import Template
from django.template.library import InclusionNode
from django.template.loader_tags import IncludeNode
from django.utils.autoreload import file_changed

from django_components.app_settings import ReloadModeType


class ComponentsConfig(AppConfig):
    name = "django_components"

    # This is the code that gets run when user adds django_components
    # to Django's INSTALLED_APPS
    # NOTE: Except for `extensions._init_app()`, the rest of the code is Django-specific.
    def ready(self) -> None:
        from django_components.app_settings import app_settings
        from django_components.component_registry import registry
        from django_components.components.dynamic import DynamicComponent
        from django_components.components.error_fallback import ErrorFallback
        from django_components.extension import extensions
        from django_components.util.django_monkeypatch import (
            monkeypatch_include_node,
            monkeypatch_inclusion_node,
            monkeypatch_template_cls,
            monkeypatch_template_proxy_cls,
        )

        # Monkeypatch Django template classes to make django-components
        # work with django-debug-toolbar-template-profiler.
        # NOTE: This monkeypatch is applied here, before Django processes any requests.
        #       See https://github.com/django-components/django-components/discussions/819
        monkeypatch_template_cls(Template)
        monkeypatch_include_node(IncludeNode)
        # Fixes https://github.com/django-components/django-components/pull/1390
        monkeypatch_inclusion_node(InclusionNode)

        # This makes django-components work with django-template-partials
        # NOTE: Delete when Django 5.2 reaches end of life
        monkeypatch_template_proxy_cls()

        # Set up file-change handling for component files (templates, JS, CSS).
        # See https://github.com/django-components/django-components/discussions/567#discussioncomment-10273632
        reload_mode = app_settings.RELOAD_ON_FILE_CHANGE
        if reload_mode != "off":
            _setup_component_file_reload(reload_mode=reload_mode)

        # Allow tags to span multiple lines. This makes it easier to work with
        # components inside Django templates, allowing us syntax like:
        # ```html
        #   {% component "icon"
        #     icon='outline_chevron_down'
        #     size=16
        #     color="text-gray-400"
        #     attrs:class="ml-2"
        #   %}{% endcomponent %}
        # ```
        #
        # See https://stackoverflow.com/a/54206609/9788634
        if app_settings.MULTILINE_TAGS:
            from django.template import base

            base.tag_re = re.compile(base.tag_re.pattern, re.DOTALL)

        # Register the dynamic component under the name as given in settings
        registry.register(app_settings.DYNAMIC_COMPONENT_NAME, DynamicComponent)
        registry.register("error_fallback", ErrorFallback)

        # Let extensions process any components which may have been created before the app was ready
        extensions._init_app(app_settings.EXTENSIONS)


def _setup_component_file_reload(*, reload_mode: ReloadModeType) -> None:
    """
    Listen for file changes in component directories and clear the cached
    component media (template, JS, CSS) so the next render reads fresh content
    from disk.

    When `reload_mode` is "hot", the handler returns True to
    tell Django's autoreloader that the change was handled, suppressing a full
    server restart.

    When `reload_mode` is "restart", the handler returns None.
    Django's `notify_file_changed()` treats that as "no handler claimed it" and
    calls `trigger_reload()` itself. See `django/utils/autoreload.py`.
    """
    from django_components.component_media import _get_components_for_file

    def on_component_file_changed(
        sender: Any,  # noqa: ARG001
        file_path: Path,
        **kwargs: Any,  # noqa: ARG001
    ) -> bool | None:
        abs_path = str(Path(file_path).resolve())
        components = _get_components_for_file(abs_path)
        if not components:
            return None

        for comp_cls in components:
            comp_media = comp_cls._component_media  # type: ignore[attr-defined]
            # Reset both template and non-template caches. A given file can only
            # be one type, but reset_template/reset_files are cheap no-ops when
            # the corresponding attribute isn't set, so we just clear both.
            comp_media.reset_template()
            comp_media.reset_files()

        if reload_mode == "hot":
            return True

        # Return None so Django's notify_file_changed() calls trigger_reload()
        # for us. See django/utils/autoreload.py:371.
        return None

    # weak=False because the handler is a closure local to this function.
    # Django's default weak=True would let it get garbage-collected immediately.
    file_changed.connect(on_component_file_changed, weak=False)
