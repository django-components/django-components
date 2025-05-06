import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol, Type, Union, cast
from weakref import WeakKeyDictionary

import django.urls
from django.http import HttpRequest, HttpResponse
from django.views.generic import View

from django_components.extension import (
    ComponentExtension,
    OnComponentClassCreatedContext,
    OnComponentClassDeletedContext,
    URLRoute,
    extensions,
)
from django_components.util.misc import format_url

if TYPE_CHECKING:
    from django_components.component import Component

# NOTE: `WeakKeyDictionary` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    ComponentRouteCache = WeakKeyDictionary[Type["Component"], URLRoute]
else:
    ComponentRouteCache = WeakKeyDictionary


class ViewFn(Protocol):
    def __call__(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any: ...  # noqa: E704


def _get_component_route_name(component: Union[Type["Component"], "Component"]) -> str:
    return f"__component_url__{component.class_id}"


def get_component_url(
    component: Union[Type["Component"], "Component"],
    query: Optional[Dict] = None,
    fragment: Optional[str] = None,
) -> str:
    """
    Get the URL for a [`Component`](../api#django_components.Component).

    Raises `RuntimeError` if the component is not public.

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    `get_component_url()` optionally accepts `query` and `fragment` arguments.

    **Example:**

    ```py
    from django_components import Component, get_component_url

    class MyComponent(Component):
        class View:
            public = True

    # Get the URL for the component
    url = get_component_url(
        MyComponent,
        query={"foo": "bar"},
        fragment="baz",
    )
    # /components/ext/view/components/c1ab2c3?foo=bar#baz
    ```
    """
    view_cls: Optional[Type[ComponentView]] = getattr(component, "View", None)
    if view_cls is None or not view_cls.public:
        raise RuntimeError("Component URL is not available - Component is not public")

    route_name = _get_component_route_name(component)
    url = django.urls.reverse(route_name)
    return format_url(url, query=query, fragment=fragment)


class ComponentView(ComponentExtension.ExtensionClass, View):  # type: ignore
    """
    The interface for `Component.View`.

    The fields of this class are used to configure the component views and URLs.

    This class is a subclass of
    [`django.views.View`](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/#view).
    The [`Component`](../api#django_components.Component) instance is available
    via `self.component`.

    Override the methods of this class to define the behavior of the component.

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    **Example:**

    ```python
    class MyComponent(Component):
        class View:
            def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
                return HttpResponse("Hello, world!")
    ```

    **Component URL:**

    If the `public` attribute is set to `True`, the component will have its own URL
    that will point to the Component's View.

    ```py
    from django_components import Component

    class MyComponent(Component):
        class View:
            public = True

            def get(self, request, *args, **kwargs):
                return HttpResponse("Hello, world!")
    ```

    Will create a URL route like `/components/ext/view/components/a1b2c3/`.

    To get the URL for the component, use `get_component_url`:

    ```py
    url = get_component_url(MyComponent)
    ```
    """

    # NOTE: This class attribute must be declared on the class for `View.as_view()` to allow
    # us to pass `component` kwarg.
    component = cast("Component", None)
    """
    The component instance.

    This is a dummy instance created solely for the View methods.

    It is the same as if you instantiated the component class directly:

    ```py
    component = Calendar()
    component.render_to_response(request=request)
    ```
    """

    public = False
    """
    Whether the component should be available via a URL.

    **Example:**

    ```py
    from django_components import Component

    class MyComponent(Component):
        class View:
            public = True
    ```

    Will create a URL route like `/components/ext/view/components/a1b2c3/`.

    To get the URL for the component, use `get_component_url`:

    ```py
    url = get_component_url(MyComponent)
    ```
    """

    def __init__(self, component: "Component", **kwargs: Any) -> None:
        ComponentExtension.ExtensionClass.__init__(self, component)
        View.__init__(self, **kwargs)

    @property
    def url(self) -> str:
        """
        The URL for the component.

        Raises `RuntimeError` if the component is not public.
        """
        return get_component_url(self.component.__class__)

    # NOTE: The methods below are defined to satisfy the `View` class. All supported methods
    # are defined in `View.http_method_names`.
    #
    # Each method actually delegates to the component's method of the same name.
    # E.g. When `get()` is called, it delegates to `component.get()`.

    # TODO_V1 - In v1 handlers like `get()` should be defined on the Component.View class,
    #           not the Component class directly. This is to align Views with the extensions API
    #           where each extension should keep its methods in the extension class.
    #           Instead, the defaults for these methods should be something like
    #           `return self.component.render_to_response()` or similar.
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "get")(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "post")(request, *args, **kwargs)

    def put(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "put")(request, *args, **kwargs)

    def patch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "patch")(request, *args, **kwargs)

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "delete")(request, *args, **kwargs)

    def head(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "head")(request, *args, **kwargs)

    def options(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "options")(request, *args, **kwargs)

    def trace(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return getattr(self.component, "trace")(request, *args, **kwargs)


class ViewExtension(ComponentExtension):
    """
    This extension adds a nested `View` class to each `Component`.

    This nested class is a subclass of `django.views.View`, and allows the component
    to be used as a view by calling `ComponentView.as_view()`.

    This extension also allows the component to be available via a unique URL.

    This extension is automatically added to all components.
    """

    name = "view"

    ExtensionClass = ComponentView

    def __init__(self) -> None:
        # Remember which route belongs to which component
        self.routes_by_component: ComponentRouteCache = WeakKeyDictionary()

    # Create URL route on creation
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        comp_cls = ctx.component_cls
        view_cls: Optional[Type[ComponentView]] = getattr(comp_cls, "View", None)
        if view_cls is None or not view_cls.public:
            return

        # Create a URL route like `components/MyTable_a1b2c3/`
        # And since this is within the `view` extension, the full URL path will then be:
        # `/components/ext/view/components/MyTable_a1b2c3/`
        route_path = f"components/{comp_cls.class_id}/"
        route_name = _get_component_route_name(comp_cls)
        route = URLRoute(
            path=route_path,
            handler=comp_cls.as_view(),
            name=route_name,
        )

        self.routes_by_component[comp_cls] = route
        extensions.add_extension_urls(self.name, [route])

    # Remove URL route on deletion
    def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
        comp_cls = ctx.component_cls
        route = self.routes_by_component.pop(comp_cls, None)
        if route is None:
            return
        extensions.remove_extension_urls(self.name, [route])
