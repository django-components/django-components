_New in version 0.34_

_Note: Since 0.92, `Component` is no longer a subclass of Django's `View`. Instead, the nested
[`Component.View`](../../../reference/api#django_components.Component.View) class is a subclass of Django's `View`._

---

For web applications, it's common to define endpoints that serve HTML content (AKA views).

django-components has a suite of features that help you write and manage views and their URLs:

- For each component, you can define methods for handling HTTP requests (GET, POST, etc.) - `get()`, `post()`, etc.
  
- Use [`Component.as_view()`](../../../reference/api#django_components.Component.as_view) to be able to use your Components  with Django's [`urlpatterns`](https://docs.djangoproject.com/en/5.1/topics/http/urls/). This works the same way as [`View.as_view()`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View.as_view).

- To avoid having to manually define the endpoints for each component, you can set the component to be "public" with [`Component.Url.public = True`](../../../reference/api#django_components.ComponentUrl.public). This will automatically create a URL for the component. To retrieve the component URL, use [`get_component_url()`](../../../reference/api#django_components.get_component_url).

- In addition, [`Component`](../../../reference/api#django_components.Component) has a [`render_to_response()`](../../../reference/api#django_components.Component.render_to_response) method that renders the component template based on the provided input and returns an `HttpResponse` object.

## Component as view example

### Define handlers

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

    The View class supports all the same HTTP methods as Django's [`View`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View) class. These are:

    `get()`, `post()`, `put()`, `patch()`, `delete()`, `head()`, `options()`, `trace()`

    Each of these receive the [`HttpRequest`](https://docs.djangoproject.com/en/5.1/ref/request-response/#django.http.HttpRequest) object as the first argument.


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

    This is deprecated from v0.135 onwards, and will be removed in v1.0.

### Register the URLs manually

To register the component as a route / endpoint in Django, add an entry to your
[`urlpatterns`](https://docs.djangoproject.com/en/5.1/topics/http/urls/).
In place of the view function, create a view object with [`Component.as_view()`](../../../reference/api#django_components.Component.as_view):

```python title="[project root]/urls.py"
from django.urls import path
from components.calendar.calendar import Calendar

urlpatterns = [
    path("calendar/", Calendar.as_view()),
]
```

[`Component.as_view()`](../../../reference/api#django_components.Component.as_view)
internally calls [`View.as_view()`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View.as_view), passing the component
instance as one of the arguments.

### Register the URLs automatically

If you don't care about the exact URL of the component, you can let django-components manage the URLs for you by setting the [`Component.Url.public`](../../../reference/api#django_components.ComponentUrl.public) attribute to `True`:

```py
class MyComponent(Component):
    class Url:
        public = True

    class View:
        def get(self, request):
            return self.component.render_to_response(request=request)
    ...
```

Then, to get the URL for the component, use [`get_component_url()`](../../../reference/api#django_components.get_component_url):

```py
from django_components import get_component_url

url = get_component_url(MyComponent)
```

This way you don't have to mix your app URLs with component URLs.
