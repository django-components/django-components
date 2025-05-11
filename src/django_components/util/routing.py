from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Protocol, Type, TypeVar

TClass = TypeVar("TClass", bound=Type[Any])


# Mark object as related to extension URLs so we can place these in
# a separate documentation section
def mark_extension_url_api(obj: TClass) -> TClass:
    obj._extension_url_api = True
    return obj


@mark_extension_url_api
class URLRouteHandler(Protocol):
    """Framework-agnostic 'view' function for routes"""

    def __call__(self, request: Any, *args: Any, **kwargs: Any) -> Any: ...  # noqa: E704


@mark_extension_url_api
@dataclass
class URLRoute:
    """
    Framework-agnostic route definition.

    This is similar to Django's `URLPattern` object created with
    [`django.urls.path()`](https://docs.djangoproject.com/en/5.2/ref/urls/#path).

    The `URLRoute` must either define a `handler` function or have a list of child routes `children`.
    If both are defined, an error will be raised.

    **Example:**

    ```python
    URLRoute("/my/path", handler=my_handler, name="my_name", extra={"kwargs": {"my_extra": "my_value"}})
    ```

    Is equivalent to:

    ```python
    django.urls.path("/my/path", my_handler, name="my_name", kwargs={"my_extra": "my_value"})
    ```

    With children:

    ```python
    URLRoute(
        "/my/path",
        name="my_name",
        extra={"kwargs": {"my_extra": "my_value"}},
        children=[
            URLRoute(
                "/child/<str:name>/",
                handler=my_handler,
                name="my_name",
                extra={"kwargs": {"my_extra": "my_value"}},
            ),
            URLRoute("/other/<int:id>/", handler=other_handler),
        ],
    )
    ```
    """

    path: str
    handler: Optional[URLRouteHandler] = None
    children: Iterable["URLRoute"] = field(default_factory=list)
    name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.handler is not None and self.children:
            raise ValueError("Cannot have both handler and children")

    # Allow to use `URLRoute` objects in sets and dictionaries
    def __hash__(self) -> int:
        return hash(self.path)
