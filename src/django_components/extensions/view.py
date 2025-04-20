from typing import TYPE_CHECKING, Any, Protocol, cast

from django.http import HttpRequest, HttpResponse
from django.views.generic import View

from django_components.extension import ComponentExtension

if TYPE_CHECKING:
    from django_components.component import Component


class ViewFn(Protocol):
    def __call__(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any: ...  # noqa: E704


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
    """

    # NOTE: This attribute must be declared on the class for `View.as_view()` to allow
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

    def __init__(self, component: "Component", **kwargs: Any) -> None:
        ComponentExtension.ExtensionClass.__init__(self, component)
        View.__init__(self, **kwargs)

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

    This extension is automatically added to all components.
    """

    name = "view"

    ExtensionClass = ComponentView
