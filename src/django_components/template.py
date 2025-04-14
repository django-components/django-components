from typing import Any, Optional, Type

from django.template import Origin, Template

from django_components.cache import get_template_cache
from django_components.util.misc import get_import_path


# Central logic for creating Templates from string, so we can cache the results
def cached_template(
    template_string: str,
    template_cls: Optional[Type[Template]] = None,
    origin: Optional[Origin] = None,
    name: Optional[str] = None,
    engine: Optional[Any] = None,
) -> Template:
    """
    Create a Template instance that will be cached as per the
    [`COMPONENTS.template_cache_size`](../settings#django_components.app_settings.ComponentsSettings.template_cache_size)
    setting.

    Args:
        template_string (str): Template as a string, same as the first argument to Django's\
            [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template). Required.
        template_cls (Type[Template], optional): Specify the Template class that should be instantiated.\
            Defaults to Django's [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template) class.
        origin (Type[Origin], optional): Sets \
            [`Template.Origin`](https://docs.djangoproject.com/en/5.1/howto/custom-template-backend/#origin-api-and-3rd-party-integration).
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
