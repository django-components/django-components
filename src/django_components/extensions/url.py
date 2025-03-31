import sys
from typing import TYPE_CHECKING, Optional, Type, Union
from weakref import WeakKeyDictionary

import django.urls

from django_components.extension import (
    ComponentExtension,
    OnComponentClassCreatedContext,
    OnComponentClassDeletedContext,
    URLRoute,
    extensions,
)
from django_components.util.misc import hash_comp_cls

if TYPE_CHECKING:
    from django_components.component import Component


# NOTE: `WeakKeyDictionary` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    ComponentRouteCache = WeakKeyDictionary[Type["Component"], URLRoute]
else:
    ComponentRouteCache = WeakKeyDictionary


def _get_component_route_name(component: Union[Type["Component"], "Component"]) -> str:
    return f"__component_url__{component._class_hash}"


def get_component_url(component: Union[Type["Component"], "Component"]) -> str:
    """
    Get the URL for a [`Component`](../api#django_components.Component).

    Raises `RuntimeError` if the component is not public.

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    **Example:**

    ```py
    from django_components import Component, get_component_url

    class MyComponent(Component):
        class Url:
            public = True

    # Get the URL for the component
    url = get_component_url(MyComponent)
    ```
    """
    url_cls: Optional[Type[ComponentUrl]] = getattr(component, "Url", None)
    if url_cls is None or not url_cls.public:
        raise RuntimeError("Component URL is not available - Component is not public")

    route_name = _get_component_route_name(component)
    return django.urls.reverse(route_name)


class ComponentUrl(ComponentExtension.ExtensionClass):  # type: ignore
    """
    The interface for `Component.Url`.

    This class is used to configure whether the component should be available via a URL.

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    **Example:**
    ```python
    from django_components import Component

    class MyComponent(Component):
        class Url:
            public = True

    # Get the URL for the component
    url = get_component_url(MyComponent)
    ```
    """

    public: bool = False
    """
    Whether this [`Component`](../api#django_components.Component) should be available
    via a URL. Defaults to `False`.

    If `True`, the Component will have its own unique URL path.

    You can use this to write components that will correspond to HTML fragments
    for HTMX or similar libraries.

    To obtain the component URL, either access the url from
    [`Component.Url.url`](../api#django_components.ComponentUrl.url) or
    use the [`get_component_url()`](../api#django_components.get_component_url) function.

    **Example:**

    ```py
    from django_components import Component, get_component_url

    class MyComponent(Component):
        class Url:
            public = True

    # Get the URL for the component
    url = get_component_url(MyComponent)
    ```
    """

    @property
    def url(self) -> str:
        """
        The URL for the component.

        Raises `RuntimeError` if the component is not public.
        """
        return get_component_url(self.component.__class__)


class UrlExtension(ComponentExtension):
    """
    This extension adds a nested `Url` class to each [`Component`](../api#django_components.Component).

    This nested `Url` class configures whether the component should be available via a URL.

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    **Example:**

    ```py
    from django_components import Component

    class MyComponent(Component):
        class Url:
            public = True
    ```

    Will create a URL route like `/components/ext/url/components/a1b2c3/`.

    To get the URL for the component, use `get_component_url`:

    ```py
    url = get_component_url(MyComponent)
    ```

    This extension is automatically added to all [`Component`](../api#django_components.Component)
    classes.
    """

    name = "url"

    ExtensionClass = ComponentUrl

    def __init__(self) -> None:
        # Remember which route belongs to which component
        self.routes_by_component: ComponentRouteCache = WeakKeyDictionary()

    # Create URL route on creation
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        url_cls: Optional[Type[ComponentUrl]] = getattr(ctx.component_cls, "Url", None)
        if url_cls is None or not url_cls.public:
            return

        # Create a URL route like `components/a1b2c3/`
        # The full URL path will then be `/components/ext/url/components/a1b2c3/`
        cls_hash = hash_comp_cls(ctx.component_cls, include_name=False)
        route_path = f"components/{cls_hash}/"
        route_name = _get_component_route_name(ctx.component_cls)
        route = URLRoute(
            path=route_path,
            handler=ctx.component_cls.as_view(),
            name=route_name,
        )

        self.routes_by_component[ctx.component_cls] = route
        extensions.add_extension_urls(self.name, [route])

    # Remove URL route on deletion
    def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
        route = self.routes_by_component.pop(ctx.component_cls, None)
        if route is None:
            return
        extensions.remove_extension_urls(self.name, [route])
