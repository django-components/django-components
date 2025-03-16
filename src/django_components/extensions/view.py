from typing import TYPE_CHECKING, Any, Protocol, cast

from django.http import HttpRequest, HttpResponse
from django.views.generic import View

from django_components.extension import ComponentExtension

if TYPE_CHECKING:
    from django_components.component import Component


class ViewFn(Protocol):
    def __call__(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any: ...  # noqa: E704


class ComponentView(ComponentExtension.ExtensionClass, View):
    """
    Subclass of `django.views.View` where the `Component` instance is available
    via `self.component`.
    """

    # NOTE: This attribute must be declared on the class for `View.as_view()` to allow
    # us to pass `component` kwarg.
    component = cast("Component", None)

    def __init__(self, component: "Component", **kwargs: Any) -> None:
        ComponentExtension.ExtensionClass.__init__(self, component)
        View.__init__(self, **kwargs)

    # NOTE: The methods below are defined to satisfy the `View` class. All supported methods
    # are defined in `View.http_method_names`.
    #
    # Each method actually delegates to the component's method of the same name.
    # E.g. When `get()` is called, it delegates to `component.get()`.

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "get")(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "post")(request, *args, **kwargs)

    def put(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "put")(request, *args, **kwargs)

    def patch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "patch")(request, *args, **kwargs)

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "delete")(request, *args, **kwargs)

    def head(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "head")(request, *args, **kwargs)

    def options(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "options")(request, *args, **kwargs)

    def trace(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        component: "Component" = self.component
        return getattr(component, "trace")(request, *args, **kwargs)


class ViewExtension(ComponentExtension):
    """
    This extension adds a nested `View` class to each `Component`.
    This nested class is a subclass of `django.views.View`, and allows the component
    to be used as a view by calling `ComponentView.as_view()`.

    This extension is automatically added to all components.
    """

    name = "view"

    ExtensionClass = ComponentView
