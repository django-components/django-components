_New in version 0.34_

_Note: Since 0.92, `Component` is no longer a subclass of Django's `View`. Instead, the nested
[`Component.View`](../../reference/api.md#django_components.Component.View) class is a subclass of Django's `View`._

---

For web applications, it's common to define endpoints that serve HTML content (AKA views).

django-components has a suite of features that help you write and manage views and their URLs:

- For each component, you can define methods for handling HTTP requests (GET, POST, etc.) - `get()`, `post()`, etc.

- Use [`Component.as_view()`](../../reference/api.md#django_components.Component.as_view) to be able to use your Components with Django's [`urlpatterns`](https://docs.djangoproject.com/en/5.2/topics/http/urls/). This works the same way as [`View.as_view()`](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/#django.views.generic.base.View.as_view).

- Or use [`get_component_url()`](../../reference/api.md#django_components.get_component_url) to retrieve the component URL - an anonymous HTTP endpoint that triggers the component's handlers without having to register the component in `urlpatterns`.

    To expose a component, simply define a handler, or explicitly expose/hide the component with [`Component.View.public = True/False`](../../reference/api.md#django_components.ComponentView.public).

- In addition, [`Component`](../../reference/api.md#django_components.Component) has a [`render_to_response()`](../../reference/api.md#django_components.Component.render_to_response) method that renders the component template based on the provided input and returns an `HttpResponse` object.

## Define handlers

Here's an example of a calendar component defined as a view. Simply define a `View` class with your custom `get()` method to handle GET requests:

```djc_py title="[project root]/components/calendar.py"
from django_components import Component, ComponentView, register

@register("calendar")
class Calendar(Component):
    template = """
        <div class="calendar-component">
            <div class="header">
                {% slot "header" / %}
            </div>
            <div class="body">
                Today's date is <span>{{ date }}</span>
            </div>
        </div>
    """

    class View:
        # Handle GET requests
        def get(self, request, *args, **kwargs):
            # Return HttpResponse with the rendered content
            return Calendar.render_to_response(
                request=request,
                kwargs={
                    "date": request.GET.get("date", "2020-06-06"),
                },
                slots={
                    "header": "Calendar header",
                },
            )
```

!!! info

    The View class supports all the same HTTP methods as Django's [`View`](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/#django.views.generic.base.View) class. These are:

    `get()`, `post()`, `put()`, `patch()`, `delete()`, `head()`, `options()`, `trace()`

    Each of these receive the [`HttpRequest`](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpRequest) object as the first argument.

<!-- TODO_V1 REMOVE -->

!!! warning

    **Deprecation warning:**

    Previously, the handler methods such as `get()` and `post()` could be defined directly on the `Component` class:

    ```py
    class Calendar(Component):
        def get(self, request, *args, **kwargs):
            return self.render_to_response(
                kwargs={
                    "date": request.GET.get("date", "2020-06-06"),
                }
            )
    ```

    This is deprecated from v0.137 onwards, and will be removed in v1.0.

### Acccessing component class

You can access the component class from within the View methods by using the [`View.component_cls`](../../reference/api.md#django_components.ComponentView.component_cls) attribute:

```py
class Calendar(Component):
    ...

    class View:
        def get(self, request):
            return self.component_cls.render_to_response(request=request)
```

## Register URLs manually

To register the component as a route / endpoint in Django, add an entry to your
[`urlpatterns`](https://docs.djangoproject.com/en/5.2/topics/http/urls/).
In place of the view function, create a view object with [`Component.as_view()`](../../reference/api.md#django_components.Component.as_view):

```python title="[project root]/urls.py"
from django.urls import path
from components.calendar.calendar import Calendar

urlpatterns = [
    path("calendar/", Calendar.as_view()),
]
```

[`Component.as_view()`](../../reference/api.md#django_components.Component.as_view)
internally calls [`View.as_view()`](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/#django.views.generic.base.View.as_view), passing the component
class as one of the arguments.

## Register URLs automatically

If you don't care about the exact URL of the component, you can let django-components manage the URLs for you.

Each component class has its own URL that triggers the component's HTTP handlers, without having to register the component in `urlpatterns`.

This way you don't have to mix your app URLs with component URLs.

To obtain the component's URL, use [`get_component_url()`](../../reference/api.md#django_components.get_component_url):

```py
from django_components import get_component_url

url = get_component_url(MyComponent)
```

The component is automatically registered in `urlpatterns` when you define a handler.

You can also explicitly enable/disable the component's URL with [`Component.View.public`](../../reference/api.md#django_components.ComponentView.public):

```py
class MyComponent(Component):
    class View:
        public = False

        def get(self, request):
            return self.component_cls.render_to_response(request=request)
    ...
```

!!! info "Query parameters and fragment"

    If you need to pass query parameters or a fragment to the component URL, you can do so by passing the `query` and `fragment` arguments to [`get_component_url()`](../../reference/api.md#django_components.get_component_url):

    ```py
    url = get_component_url(
        MyComponent,
        query={"foo": "bar", "enabled": True, "debug": False, "unused": None},
        fragment="baz",
    )
    # /components/ext/view/components/c1ab2c3?foo=bar&enabled#baz
    ```

    **Query parameter handling:**

    - `True` values are rendered as flag parameters without values (e.g., `?enabled`)
    - `False` and `None` values are omitted from the URL
    - Other values are rendered normally (e.g., `?foo=bar`)

### Modifying the route path

You can customize the component URL route by overriding [`Component.View.get_route_path()`](../../reference/api.md#django_components.ComponentView.get_route_path). This allows you to add route parameters to your component URLs:

```py
from django_components import Component, get_component_url

class UserProfile(Component):
    class View:
        @classmethod
        def get_route_path(cls):
            return f"users/<str:username>/<int:user_id>/"

        def get(self, request, username: str, user_id: int, **kwargs):
            return UserProfile.render_to_response()

# Get the URL with route parameters filled
url = get_component_url(
    UserProfile,
    kwargs={"username": "john", "user_id": 42},
)
# /components/ext/view/users/john/42/
```

When you define route parameters in `get_route_path()`, you can pass `args` and `kwargs` to [`get_component_url()`](../../reference/api.md#django_components.get_component_url) to fill those parameters. Both `args` and `kwargs` are passed to Django's `reverse()` function.
