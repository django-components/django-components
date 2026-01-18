import sys
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Protocol, Type, Union, cast
from weakref import WeakKeyDictionary

import django.urls
from django.http import HttpRequest, HttpResponse
from django.views.generic import View

from django_components.extension import (
    ComponentExtension,
    ExtensionComponentConfig,
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
    def __call__(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any: ...


def _get_component_route_name(component: Union[Type["Component"], "Component"]) -> str:
    return f"__component_url__{component.class_id}"


def get_component_url(
    component: Union[Type["Component"], "Component"],
    query: Optional[Dict] = None,
    fragment: Optional[str] = None,
    args: Optional[Any] = None,
    kwargs: Optional[Any] = None,
) -> str:
    """
    Get the URL for a [`Component`](../api#django_components.Component).

    Raises `RuntimeError` if the component is not public.

    Component is public when:

    - You set any of the HTTP methods in the [`Component.View`](../api#django_components.ComponentView) class,
    - Or you explicitly set [`Component.View.public = True`](../api#django_components.ComponentView.public).

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    `get_component_url()` optionally accepts `query` and `fragment` arguments.
    `get_component_url()` also accepts optionally `args` and `kwargs` arguments
    that will be transmitted to django.urls.reverse

    **Query parameter handling:**

    - `True` values are rendered as flag parameters without values (e.g., `?enabled`)
    - `False` and `None` values are omitted from the URL
    - Other values are rendered normally (e.g., `?foo=bar`)

    **Example:**

    ```py
    from django_components import Component, get_component_url

    class MyTable(Component):
        class View:
            def get(self, request: HttpRequest, **kwargs: Any):
                return MyTable.render_to_response()

    # Get the URL for the component
    url = get_component_url(
        MyComponent,
        query={"foo": "bar", "enabled": True, "debug": False, "unused": None},
        fragment="baz",
    )
    # /components/ext/view/components/c1ab2c3?foo=bar&enabled#baz
    ```
    """
    view_cls: Optional[Type[ComponentView]] = getattr(component, "View", None)
    if not _is_view_public(view_cls):
        raise RuntimeError("Component URL is not available - Component is not public")

    route_name = _get_component_route_name(component)
    url = django.urls.reverse(route_name, args=args, kwargs=kwargs)
    return format_url(url, query=query, fragment=fragment)


class ComponentView(ExtensionComponentConfig, View):
    """
    The interface for `Component.View`.

    The fields of this class are used to configure the component views and URLs.

    This class is a subclass of
    [`django.views.View`](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/#view).

    Override the methods of this class to define the behavior of the component.

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    The [`Component`](../api#django_components.Component) class is available
    via `self.component_cls`.

    **Example:**

    Define a handler that runs for GET HTTP requests:

    ```python
    class MyComponent(Component):
        class View:
            def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
                return HttpResponse("Hello, world!")
    ```

    **Component URL:**

    Use [`get_component_url()`](../api#django_components.get_component_url) to retrieve
    the component URL - an anonymous HTTP endpoint that triggers the component's handlers without having to register
    the component in `urlpatterns`.

    A component is automatically exposed when you define at least one HTTP handler. To explicitly
    expose/hide the component, use
    [`Component.View.public = True`](../api#django_components.ComponentView.public).

    ```py
    from django_components import Component, get_component_url

    class MyComponent(Component):
        class View:
            def get(self, request, *args, **kwargs):
                return HttpResponse("Hello, world!")

    url = get_component_url(MyComponent)
    ```

    This will create a URL route like `/components/ext/view/components/a1b2c3/`.
    """

    # NOTE: The `component` / `component_cls` attributes are NOT user input, but still must be declared
    # on this class for Django's `View.as_view()` to allow us to pass `component` kwarg.

    # TODO_v1 - Remove. Superseded by `component_cls` attribute because we don't actually have access to an instance.
    component = cast("Component", None)
    """
    DEPRECATED: Will be removed in v1.0.
    Use [`component_cls`](../api#django_components.ComponentView.component_cls) instead.

    This is a dummy instance created solely for the View methods.

    It is the same as if you instantiated the component class directly:

    ```py
    component = Calendar()
    component.render_to_response(request=request)
    ```
    """

    component_cls = cast("Type[Component]", None)
    """
    The parent component class.

    **Example:**

    ```py
    class MyComponent(Component):
        class View:
            def get(self, request):
                return self.component_cls.render_to_response(request=request)
    ```
    """

    def __init__(self, component: "Component", **kwargs: Any) -> None:
        ComponentExtension.ComponentConfig.__init__(self, component)
        View.__init__(self, **kwargs)

        # TODO_v1 - Remove. Superseded by `component_cls`. This was used for backwards compatibility.
        self.component = component

    @classmethod
    def get_route_path(cls) -> str:
        """
        Get the route path for the component.
        By default, this is `components/{component.class_id}/`.
        You can override this method to customize the route path.
        **Example:**
        ```py
        class MyComponent(Component):
            class View:
                @classmethod
                def get_route_path(cls):
                    return f"my/custom/path/{cls.component_cls.class_id}/<int:pk>/"
        ```
        """
        return f"components/{cls.component_cls.class_id}/"

    @property
    def url(self) -> str:
        """
        The URL for the component.

        Raises `RuntimeError` if the component is not public.
        See [`Component.View.public`](../api#django_components.ComponentView.public).

        This is the same as calling [`get_component_url()`](../api#django_components.get_component_url)
        with the current [`Component`](../api#django_components.Component) class:

        ```py
        class MyComponent(Component):
            class View:
                def get(self, request):
                    component_url = get_component_url(self.component_cls)
                    assert self.url == component_url
        ```
        """
        return get_component_url(self.component_cls)

    # #####################################
    # PUBLIC API (Configurable by users)
    # #####################################

    public: ClassVar[Optional[bool]] = None
    """
    Whether the component HTTP handlers should be available via a URL.

    By default (`None`), the component HTTP handlers are available via a URL
    if any of the HTTP methods are defined.

    You can explicitly set `public` to `True` or `False` to override this behaviour.

    **Example:**

    Define the component HTTP handlers and get its URL using
    [`get_component_url()`](../api#django_components.get_component_url):

    ```py
    from django_components import Component, get_component_url

    class MyComponent(Component):
        class View:
            def get(self, request):
                return self.component_cls.render_to_response(request=request)

    url = get_component_url(MyComponent)
    ```

    This will create a URL route like `/components/ext/view/components/a1b2c3/`.

    To explicitly hide the component, set `public = False`:

    ```py
    class MyComponent(Component):
        class View:
            public = False

            def get(self, request):
                return self.component_cls.render_to_response(request=request)
    ```
    """

    # NOTE: The methods below are defined to satisfy the `View` class. All supported methods
    # are defined in `View.http_method_names`.
    #
    # Each method actually delegates to the component's method of the same name.
    # E.g. When `get()` is called, it delegates to `component.get()`.

    # TODO_V1 - For backwards compatibility, the HTTP methods can be defined directly on
    #           the Component class, e.g. `Component.post()`.
    #           This should be no longer supported in v1.
    #           In v1, handlers like `get()` should be defined on the Component.View class.
    #           This is to align Views with the extensions API, where each extension should
    #           keep its methods in the extension class.
    #           And instead, the defaults for these methods should be something like
    #           `return self.component_cls.render_to_response(request, *args, **kwargs)` or similar
    #           or raise NotImplementedError.
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().get(request, *args, **kwargs)  # type: ignore[attr-defined]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().post(request, *args, **kwargs)  # type: ignore[attr-defined]

    def put(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().put(request, *args, **kwargs)  # type: ignore[attr-defined]

    def patch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().patch(request, *args, **kwargs)  # type: ignore[attr-defined]

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().delete(request, *args, **kwargs)  # type: ignore[attr-defined]

    def head(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().head(request, *args, **kwargs)  # type: ignore[attr-defined]

    def options(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().options(request, *args, **kwargs)  # type: ignore[attr-defined]

    def trace(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self.component_cls().trace(request, *args, **kwargs)  # type: ignore[attr-defined]


class ViewExtension(ComponentExtension):
    """
    This extension adds a nested `View` class to each `Component`.

    This nested class is a subclass of `django.views.View`, and allows the component
    to be used as a view by calling `ComponentView.as_view()`.

    This extension also allows the component to be available via a unique URL.

    This extension is automatically added to all components.
    """

    name = "view"

    ComponentConfig = ComponentView

    def __init__(self) -> None:
        # Remember which route belongs to which component
        self.routes_by_component: ComponentRouteCache = WeakKeyDictionary()

    # Create URL route on creation
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        comp_cls = ctx.component_cls
        view_cls: Optional[Type[ComponentView]] = getattr(comp_cls, "View", None)
        if not view_cls or not _is_view_public(view_cls):
            return

        # Create a URL route like `components/MyTable_a1b2c3/`
        # And since this is within the `view` extension, the full URL path will then be:
        # `/components/ext/view/components/MyTable_a1b2c3/`
        route_path = view_cls.get_route_path()
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


def _is_view_public(view_cls: Optional[Type[ComponentView]]) -> bool:
    if view_cls is None:
        return False

    # Allow users to skip setting `View.public = True` if any of the HTTP methods
    # are defined. Users can still opt-out by explicitly setting `View.public` to `True` or `False`.
    public = getattr(view_cls, "public", None)
    if public is not None:
        return public

    # Auto-decide whether the view is public by checking if any of the HTTP methods
    # are overridden in the user's View class.
    # We do this only once, so if user dynamically adds or removes the methods,
    # we will not pick up on that.
    http_methods = ["get", "post", "put", "patch", "delete", "head", "options", "trace"]
    for method in http_methods:
        if not hasattr(view_cls, method):
            continue
        did_change_method = getattr(view_cls, method) != getattr(ComponentView, method)
        if did_change_method:
            view_cls.public = True
            return True

    view_cls.public = False
    return False
