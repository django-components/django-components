from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Type, Union, cast

from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Origin, Template, TemplateDoesNotExist
from django.template.loader import get_template as django_get_template

from django_components.cache import get_template_cache
from django_components.template_loader import DjcLoader
from django_components.util.django_monkeypatch import is_template_cls_patched
from django_components.util.logger import trace_component_msg
from django_components.util.misc import get_import_path, get_module_info

if TYPE_CHECKING:
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
    """  # noqa: E501
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

        if not is_template_cls_patched(template):
            raise RuntimeError(
                "Django-components received a Template instance which was not patched."
                "If you are using Django's Template class, check if you added django-components"
                "to INSTALLED_APPS. If you are using a custom template class, then you need to"
                "manually patch the class."
            )

        with _maybe_bind_template(context, template):
            yield template


def load_component_template(component_cls: Type["Component"], filepath: str) -> Template:
    if component_cls._template is not None:
        return component_cls._template

    # First try to load the filepath using our `DjcLoader`,
    # so we can pass in the component class to `DjcLoader` and so associate
    # the template with the component class via the `Origin` instance.
    #
    # If the template is NOT found, then we assume that the template
    # is to be loaded with other loaders, and hence we don't consider
    # this template to belong to any component.
    #
    # NOTE: This practically means that for some extension hooks like `on_template_preprocess()`
    #       to work, users MUST either:
    #       - Inline the template within the component class as `Component.template`
    #       - Set `Component.template_file` to filepath that is within our `COMPONENTS.dirs` / `COMPONENTS.app_dirs`
    #         and is thus is loaded by DjcLoader.
    #
    #       If users don't do this, then we don't know if the given template does or does not
    #       belong to a component, and thus we don't pre-process it.
    djc_loader = DjcLoader(None)
    try:
        template = djc_loader.get_template(filepath, component_cls=component_cls)
    except TemplateDoesNotExist:
        template = None

    # Otherwise, use Django's `get_template()` to load the template
    if template is None:
        template = _load_django_template(filepath)

    component_cls._template = template

    return template


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


def _get_component_template(component: "Component") -> Optional[Template]:
    trace_component_msg("COMP_LOAD", component_name=component.name, component_id=component.id, slot_name=None)

    # TODO_V1 - Remove, not needed once we remove `get_template_string()`, `get_template_name()`, `get_template()`
    template_sources: Dict[str, Optional[Union[str, Template]]] = {}

    # TODO_V1 - Remove `get_template_name()` in v1
    template_sources["get_template_name"] = component.get_template_name(component.context)

    # TODO_V1 - Remove `get_template_string()` in v1
    if hasattr(component, "get_template_string"):
        template_string_getter = getattr(component, "get_template_string")
        template_body_from_getter = template_string_getter(component.context)
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
            f"Component template was set multiple times in Component {component.name}."
            f"Sources: {sources_with_values}"
        )

    # Load the template based on the source
    if template_sources["get_template_name"]:
        template_name = template_sources["get_template_name"]
        template: Optional[Template] = _load_django_template(template_name)
        template_string: Optional[str] = None
    elif template_sources["get_template_string"]:
        template_string = template_sources["get_template_string"]
        template = None
    elif template_sources["get_template"]:
        # `Component.get_template()` returns either string or Template instance
        if hasattr(template_sources["get_template"], "render"):
            template = template_sources["get_template"]
            template_string = None
        else:
            template = None
            template_string = template_sources["get_template"]
    elif component.template or component.template_file:
        # If the template was loaded from `Component.template_file`, then the Template
        # instance was already created and cached in `Component._template`.
        #
        # NOTE: This is important to keep in mind, because the implication is that we should
        # treat Templates AND their nodelists as IMMUTABLE.
        if component.__class__._template is not None:
            template = component.__class__._template
            template_string = None
        # Otherwise user have set `Component.template` as string and we still need to
        # create the instance.
        else:
            template = _create_template_from_string(
                component,
                # NOTE: We can't reach this branch if `Component.template` is None
                cast(str, component.template),
                is_component_template=True,
            )
            template_string = None
    # No template
    else:
        template = None
        template_string = None

    # We already have a template instance, so we can return it
    if template is not None:
        return template
    # Create the template from the string
    elif template_string is not None:
        return _create_template_from_string(component, template_string)

    # Otherwise, Component has no template - this is valid, as it may be instead rendered
    # via `Component.on_render()`
    return None


def _create_template_from_string(
    component: "Component",
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
    _, _, module_filepath = get_module_info(component.__class__)
    origin = Origin(
        name=f"{module_filepath}::{component.__class__.__name__}",
        template_name=None,
        loader=None,
    )

    _set_origin_component(origin, component.__class__)

    if is_component_template:
        template = Template(template_string, name=origin.template_name, origin=origin)
        component.__class__._template = template
    else:
        # TODO_V1 - `cached_template()` won't be needed as there will be only 1 template per component
        #           so we will be able to instead use `template_cache` to store the template
        template = cached_template(
            template_string=template_string,
            name=origin.template_name,
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
    return django_get_template(template_name).template


def _set_origin_component(origin: Origin, component_cls: Type["Component"]) -> None:
    origin.component_cls = component_cls


def _get_origin_component(origin: Origin) -> Optional[Type["Component"]]:
    return getattr(origin, "component_cls", None)
