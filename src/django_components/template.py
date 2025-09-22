import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Type, Union, cast
from weakref import ReferenceType, ref

from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Origin, Template
from django.template.loader import get_template as django_get_template

from django_components.cache import get_template_cache
from django_components.util.django_monkeypatch import is_cls_patched
from django_components.util.loader import get_component_dirs
from django_components.util.logger import trace_component_msg
from django_components.util.misc import get_import_path, get_module_info

if TYPE_CHECKING:
    from django.template.backends.django import Template as DjangoTemplate

    from django_components.component import Component


# TODO_V1 - Remove, won't be needed once we remove `get_template_string()`, `get_template_name()`, `get_template()`
# Legacy logic for creating Templates from string
def cached_template(
    template_string: str,
    template_cls: Optional[Type[Template]] = None,
    origin: Optional[Origin] = None,
    name: Optional[str] = None,
    engine: Optional[Any] = None,
) -> Template:
    """
    DEPRECATED. Template caching will be removed in v1.

    Create a Template instance that will be cached as per the
    [`COMPONENTS.template_cache_size`](../settings#django_components.app_settings.ComponentsSettings.template_cache_size)
    setting.

    Args:
        template_string (str): Template as a string, same as the first argument to Django's\
            [`Template`](https://docs.djangoproject.com/en/5.2/topics/templates/#template). Required.
        template_cls (Type[Template], optional): Specify the Template class that should be instantiated.\
            Defaults to Django's [`Template`](https://docs.djangoproject.com/en/5.2/topics/templates/#template) class.
        origin (Type[Origin], optional): Sets \
            [`Template.Origin`](https://docs.djangoproject.com/en/5.2/howto/custom-template-backend/#origin-api-and-3rd-party-integration).
        name (Type[str], optional): Sets `Template.name`
        engine (Type[Any], optional): Sets `Template.engine`

    ```python
    from django_components import cached_template

    template = cached_template("Variable: {{ variable }}")

    # You can optionally specify Template class, and other Template inputs:
    class MyTemplate(Template):
        pass

    template = cached_template(
        "Variable: {{ variable }}",
        template_cls=MyTemplate,
        name=...
        origin=...
        engine=...
    )
    ```

    """
    template_cache = get_template_cache()

    template_cls = template_cls or Template
    template_cls_path = get_import_path(template_cls)
    engine_cls_path = get_import_path(engine.__class__) if engine else None
    cache_key = (template_cls_path, template_string, engine_cls_path)

    maybe_cached_template: Optional[Template] = template_cache.get(cache_key)
    if maybe_cached_template is None:
        template = template_cls(template_string, origin=origin, name=name, engine=engine)
        template_cache.set(cache_key, template)
    else:
        template = maybe_cached_template

    return template


########################################################
# PREPARING COMPONENT TEMPLATES FOR RENDERING
########################################################


@contextmanager
def prepare_component_template(
    component: "Component",
    template_data: Any,
) -> Generator[Optional[Template], Any, None]:
    context = component.context
    with context.update(template_data):
        template = _get_component_template(component)

        if template is None:
            # If template is None, then the component is "template-less",
            # and we skip template processing.
            yield template
            return

        if not is_cls_patched(template.__class__):
            raise RuntimeError(
                "Django-components received a Template instance which was not patched."
                "If you are using Django's Template class, check if you added django-components"
                "to INSTALLED_APPS. If you are using a custom template class, then you need to"
                "manually patch the class.",
            )

        with _maybe_bind_template(context, template):
            yield template


# `_maybe_bind_template()` handles two problems:
#
# 1. Initially, the binding the template was needed for the context processor data
#    to work when using `RequestContext` (See `RequestContext.bind_template()` in e.g. Django v4.2 or v5.1).
#    But as of djc v0.140 (possibly earlier) we generate and apply the context processor data
#    ourselves in `Component._render_impl()`.
#
#    Now, we still want to "bind the template" by setting the `Context.template` attribute.
#    This is for compatibility with Django, because we don't know if there isn't some code that relies
#    on the `Context.template` attribute being set.
#
#    But we don't call `context.bind_template()` explicitly. If we did, then we would
#    be generating and applying the context processor data twice if the context was `RequestContext`.
#    Instead, we only run the same logic as `Context.bind_template()` but inlined.
#
#    The downstream effect of this is that if the user or some third-party library
#    uses custom subclass of `Context` with custom logic for `Context.bind_template()`,
#    then this custom logic will NOT be applied. In such case they should open an issue.
#
#    See https://github.com/django-components/django-components/issues/580
#    and https://github.com/django-components/django-components/issues/634
#
# 2. Not sure if I (Juro) remember right, but I think that with the binding of templates
#    there was also an issue that in *some* cases the template was already bound to the context
#    by the time we got to rendering the component. This is why we need to check if `context.template`
#    is already set.
#
#    The cause of this may have been compatibility with Django's `{% extends %}` tag, or
#    maybe when using the "isolated" context behavior. But not sure.
@contextmanager
def _maybe_bind_template(context: Context, template: Template) -> Generator[None, Any, None]:
    if context.template is not None:
        yield
        return

    # This code is taken from `Context.bind_template()` from Django v5.1
    context.template = template
    try:
        yield
    finally:
        context.template = None


########################################################
# LOADING TEMPLATES FROM FILEPATH
########################################################


# Remember which Component class is currently being loaded
# This is important, because multiple Components may define the same `template_file`.
# So we need this global state to help us decide which Component class of the list of components
# that matched for the given `template_file` should be associated with the template.
#
# NOTE: Implemented as a list (stack) to handle the case when calling Django's `get_template()`
#       could lead to more components being loaded at once.
#       (For this to happen, user would have to define a Django template loader that renders other components
#       while resolving the template file.)
loading_components: List["ComponentRef"] = []


def load_component_template(
    component_cls: Type["Component"],
    filepath: Optional[str] = None,
    content: Optional[str] = None,
) -> Template:
    if filepath is None and content is None:
        raise ValueError("Either `filepath` or `content` must be provided.")

    loading_components.append(ref(component_cls))

    if filepath is not None:
        # Use Django's `get_template()` to load the template file
        template = _load_django_template(filepath)
        template = ensure_unique_template(component_cls, template)

    elif content is not None:
        template = _create_template_from_string(component_cls, content, is_component_template=True)
    else:
        raise ValueError("Received both `filepath` and `content`. These are mutually exclusive.")

    loading_components.pop()

    return template


# When loading a Template instance, it may be cached by Django / template loaders.
# In that case we want to make a copy of the template which would
# be owned by the current Component class.
# Thus each Component has it's own Template instance with their own Origins
# pointing to the correct Component class.
def ensure_unique_template(component_cls: Type["Component"], template: Template) -> Template:
    # Use `template.origin.component_cls` to check if the template was cached by Django / template loaders.
    if get_component_from_origin(template.origin) is None:
        set_component_to_origin(template.origin, component_cls)
    else:
        origin_copy = Origin(template.origin.name, template.origin.template_name, template.origin.loader)
        set_component_to_origin(origin_copy, component_cls)
        template = Template(template.source, origin=origin_copy, name=template.name, engine=template.engine)

    return template


def _get_component_template(component: "Component") -> Optional[Template]:
    trace_component_msg("COMP_LOAD", component_name=component.name, component_id=component.id, slot_name=None)

    # TODO_V1 - Remove, not needed once we remove `get_template_string()`, `get_template_name()`, `get_template()`
    template_sources: Dict[str, Optional[Union[str, Template]]] = {}

    # TODO_V1 - Remove `get_template_name()` in v1
    template_sources["get_template_name"] = component.get_template_name(component.context)

    # TODO_V1 - Remove `get_template_string()` in v1
    if hasattr(component, "get_template_string"):
        template_body_from_getter = component.get_template_string(component.context)  # type: ignore[attr-defined]
    else:
        template_body_from_getter = None
    template_sources["get_template_string"] = template_body_from_getter

    # TODO_V1 - Remove `get_template()` in v1
    template_sources["get_template"] = component.get_template(component.context)

    # NOTE: `component.template` should be populated whether user has set `template` or `template_file`
    #       so we discern between the two cases by checking `component.template_file`
    if component.template_file is not None:
        template_sources["template_file"] = component.template_file
    else:
        template_sources["template"] = component.template

    # TODO_V1 - Remove this check in v1
    # Raise if there are multiple sources for the component template
    sources_with_values = [k for k, v in template_sources.items() if v is not None]
    if len(sources_with_values) > 1:
        raise ImproperlyConfigured(
            f"Component template was set multiple times in Component {component.name}. Sources: {sources_with_values}",
        )

    # Load the template based on the source
    if template_sources["get_template_name"]:
        template_name = cast("str", template_sources["get_template_name"])
        template: Optional[Template] = _load_django_template(template_name)
        template_string: Optional[str] = None
    elif template_sources["get_template_string"]:
        template_string = template_sources["get_template_string"]  # type: ignore[assignment]
        template = None
    elif template_sources["get_template"]:
        # `Component.get_template()` returns either string or Template instance
        if hasattr(template_sources["get_template"], "render"):
            template = template_sources["get_template"]  # type: ignore[assignment]
            template_string = None
        else:
            template = None
            template_string = template_sources["get_template"]  # type: ignore[assignment]
    elif component.template or component.template_file:
        # If the template was loaded from `Component.template` or `Component.template_file`,
        # then the Template instance was already created and cached in `Component._template`.
        #
        # NOTE: This is important to keep in mind, because the implication is that we should
        # treat Templates AND their nodelists as IMMUTABLE.
        template = component.__class__._component_media._template  # type: ignore[attr-defined]
        template_string = None
    # No template
    else:
        template = None
        template_string = None

    # We already have a template instance, so we can return it
    if template is not None:
        return template
    # Create the template from the string
    if template_string is not None:
        return _create_template_from_string(component.__class__, template_string)

    # Otherwise, Component has no template - this is valid, as it may be instead rendered
    # via `Component.on_render()`
    return None


def _create_template_from_string(
    component: Type["Component"],
    template_string: str,
    is_component_template: bool = False,
) -> Template:
    # Generate a valid Origin instance.
    # When an Origin instance is created by Django when using Django's loaders, it looks like this:
    # ```
    # {
    #   'name': '/path/to/project/django-components/sampleproject/calendarapp/templates/calendarapp/calendar.html',
    #   'template_name': 'calendarapp/calendar.html',
    #   'loader': <django.template.loaders.app_directories.Loader object at 0x10b441d90>
    # }
    # ```
    #
    # Since our template is inlined, we will format as `filepath::ComponentName`
    #
    # ```
    # /path/to/project/django-components/src/calendarapp/calendar.html::Calendar
    # ```
    #
    # See https://docs.djangoproject.com/en/5.2/howto/custom-template-backend/#template-origin-api
    _, _, module_filepath = get_module_info(component)
    origin = Origin(
        name=f"{module_filepath}::{component.__name__}",
        template_name=None,
        loader=None,
    )

    set_component_to_origin(origin, component)

    template_name = cast("Optional[str]", origin.template_name)
    if is_component_template:
        template = Template(template_string, name=template_name, origin=origin)
    else:
        # TODO_V1 - `cached_template()` won't be needed as there will be only 1 template per component
        #           so we will be able to instead use `template_cache` to store the template
        template = cached_template(
            template_string=template_string,
            name=template_name,
            origin=origin,
        )

    return template


# When loading a template, use Django's `get_template()` to ensure it triggers Django template loaders
# See https://github.com/django-components/django-components/issues/901
#
# This may raise `TemplateDoesNotExist` if the template doesn't exist.
# See https://docs.djangoproject.com/en/5.2/ref/templates/api/#template-loaders
# And https://docs.djangoproject.com/en/5.2/ref/templates/api/#custom-template-loaders
#
# TODO_v3 - Instead of loading templates with Django's `get_template()`,
#       we should simply read the files directly (same as we do for JS and CSS).
#       This has the implications that:
#       - We would no longer support Django's template loaders
#       - Instead if users are using template loaders, they should re-create them as djc extensions
#       - We would no longer need to set `TEMPLATES.OPTIONS.loaders` to include
#         `django_components.template_loader.Loader`
def _load_django_template(template_name: str) -> Template:
    engine_tmpl = cast("DjangoTemplate", django_get_template(template_name))
    return engine_tmpl.template


########################################################
# ASSOCIATING COMPONENT CLASSES WITH TEMPLATES
#
# See https://github.com/django-components/django-components/pull/1222
########################################################

# NOTE: `ReferenceType` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    ComponentRef = ReferenceType[Type["Component"]]
else:
    ComponentRef = ReferenceType


# Remember which Component classes defined `template_file`. Since multiple Components may
# define the same `template_file`, we store a list of weak references to the Component classes.
component_template_file_cache: Dict[str, List[ComponentRef]] = {}
component_template_file_cache_initialized = False


# Remember the mapping of `Component.template_file` -> `Component` class, so that we can associate
# the `Template` instances with the correct Component class in our monkepatched `Template.__init__()`.
def cache_component_template_file(component_cls: Type["Component"]) -> None:
    # When a Component class is created before Django is set up,
    # then `component_template_file_cache_initialized` is False and we leave it for later.
    # This is necessary because:
    # 1. We might need to resolve the template_file as relative to the file where the Component class is defined.
    # 2. To be able to resolve the template_file, Django needs to be set up, because we need to access Django settings.
    # 3. Django settings may not be available at the time of Component class creation.
    if not component_template_file_cache_initialized:
        return

    # NOTE: Avoids circular import
    from django_components.component_media import (  # noqa: PLC0415
        ComponentMedia,
        Unset,
        _resolve_component_relative_files,
        is_set,
    )

    # If we access the `Component.template_file` attribute, then this triggers media resolution if it was not done yet.
    # The problem is that this also causes the loading of the Template, if Component has defined `template_file`.
    # This triggers `Template.__init__()`, which then triggers another call to `cache_component_template_file()`.
    #
    # At the same time, at this point we don't need the media files to be loaded. But we DO need for the relative
    # file path to be resolved.
    #
    # So for this reason, `ComponentMedia.resolved_relative_files` was added to track if the media files were resolved.
    # Once relative files were resolved, we can safely access the template file from `ComponentMedia` instance
    # directly, thus avoiding the triggering of the Template loading.
    comp_media: ComponentMedia = component_cls._component_media  # type: ignore[attr-defined]
    if comp_media.resolved and comp_media.resolved_relative_files:
        template_file: Union[str, Unset, None] = component_cls.template_file
    else:
        # NOTE: This block of code is based on `_resolve_media()` in `component_media.py`
        if not comp_media.resolved_relative_files:
            comp_dirs = get_component_dirs()
            _resolve_component_relative_files(component_cls, comp_media, comp_dirs=comp_dirs)

        template_file = comp_media.template_file

    if not is_set(template_file):
        return

    if template_file not in component_template_file_cache:
        component_template_file_cache[template_file] = []

    component_template_file_cache[template_file].append(ref(component_cls))


def get_component_by_template_file(template_file: str) -> Optional[Type["Component"]]:
    # This function is called from within `Template.__init__()`. At that point, Django MUST be already set up,
    # because Django's `Template.__init__()` accesses the templating engines.
    #
    # So at this point we want to call `cache_component_template_file()` for all Components for which
    # we skipped it earlier.
    global component_template_file_cache_initialized  # noqa: PLW0603
    if not component_template_file_cache_initialized:
        component_template_file_cache_initialized = True

        # NOTE: Avoids circular import
        from django_components.component import all_components  # noqa: PLC0415

        components = all_components()
        for component in components:
            cache_component_template_file(component)

    if template_file not in component_template_file_cache or not len(component_template_file_cache[template_file]):
        return None

    # There is at least one Component class that has this `template_file`.
    matched_component_refs = component_template_file_cache[template_file]

    # There may be multiple components that define the same `template_file`.
    # So to find the correct one, we need to check if the currently loading component
    # is one of the ones that define the `template_file`.
    #
    # If there are NO currently loading components, then `Template.__init__()` was NOT triggered by us,
    # in which case we don't associate any Component class with this Template.
    if not len(loading_components):
        return None

    loading_component = loading_components[-1]()
    if loading_component is None:
        return None

    for component_ref in matched_component_refs:
        comp_cls = component_ref()
        if comp_cls is loading_component:
            return comp_cls

    return None


# NOTE: Used by `@djc_test` to reset the component template file cache
def _reset_component_template_file_cache() -> None:
    global component_template_file_cache  # noqa: PLW0603
    component_template_file_cache = {}

    global component_template_file_cache_initialized  # noqa: PLW0603
    component_template_file_cache_initialized = False


# Helpers so we know where in the codebase we set / access the `Origin.component_cls` attribute
def set_component_to_origin(origin: Origin, component_cls: Type["Component"]) -> None:
    origin.component_cls = component_cls  # type: ignore[attr-defined]


def get_component_from_origin(origin: Origin) -> Optional[Type["Component"]]:
    return getattr(origin, "component_cls", None)
