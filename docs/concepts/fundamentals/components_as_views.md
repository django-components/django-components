_New in version 0.34_

_Note: Since 0.92, Component no longer subclasses View. To configure the View class, set the nested `Component.View` class_

Components can now be used as views:

- Components define the `Component.as_view()` class method that can be used the same as [`View.as_view()`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View.as_view).

- By default, you can define GET, POST or other HTTP handlers directly on the Component, same as you do with [View](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#view). For example, you can override `get` and `post` to handle GET and POST requests, respectively.

- In addition, `Component` now has a [`render_to_response`](#inputs-of-render-and-render_to_response) method that renders the component template based on the provided context and slots' data and returns an `HttpResponse` object.

## Component as view example

Here's an example of a calendar component defined as a view:

```djc_py
# In a file called [project root]/components/calendar.py
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

    # Handle GET requests
    def get(self, request, *args, **kwargs):
        context = {
            "date": request.GET.get("date", "2020-06-06"),
        }
        slots = {
            "header": "Calendar header",
        }
        # Return HttpResponse with the rendered content
        return self.render_to_response(
            context=context,
            slots=slots,
        )
```

Then, to use this component as a view, you should create a `urls.py` file in your components directory, and add a path to the component's view:

```python
# In a file called [project root]/components/urls.py
from django.urls import path
from components.calendar.calendar import Calendar

urlpatterns = [
    path("calendar/", Calendar.as_view()),
]
```

`Component.as_view()` is a shorthand for calling [`View.as_view()`](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.View.as_view) and passing the component
instance as one of the arguments.

Remember to add `__init__.py` to your components directory, so that Django can find the `urls.py` file.

Finally, include the component's urls in your project's `urls.py` file:

```python
# In a file called [project root]/urls.py
from django.urls import include, path

urlpatterns = [
    path("components/", include("components.urls")),
]
```

Note: Slots content are automatically escaped by default to prevent XSS attacks. To disable escaping, set `escape_slots_content=False` in the `render_to_response` method. If you do so, you should make sure that any content you pass to the slots is safe, especially if it comes from user input.

If you're planning on passing an HTML string, check Django's use of [`format_html`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.html.format_html) and [`mark_safe`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.safestring.mark_safe).

## Modifying the View class

The View class that handles the requests is defined on `Component.View`.

When you define a GET or POST handlers on the `Component` class, like so:

```py
class MyComponent(Component):
    def get(self, request, *args, **kwargs):
        return self.render_to_response(
            context={
                "date": request.GET.get("date", "2020-06-06"),
            },
        )

    def post(self, request, *args, **kwargs) -> HttpResponse:
        variable = request.POST.get("variable")
        return self.render_to_response(
            kwargs={"variable": variable}
        )
```

Then the request is still handled by `Component.View.get()` or `Component.View.post()`
methods. However, by default, `Component.View.get()` points to `Component.get()`, and so on.

```py
class ComponentView(View):
    component: Component = None
    ...

    def get(self, request, *args, **kwargs):
        return self.component.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.component.post(request, *args, **kwargs)

    ...
```

If you want to define your own `View` class, you need to:

1. Set the class as `Component.View`
2. Subclass from `ComponentView`, so the View instance has access to the component instance.

In the example below, we added extra logic into `View.setup()`.

Note that the POST handler is still defined at the top. This is because `View` subclasses `ComponentView`, which defines the `post()` method that calls `Component.post()`.

If you were to overwrite the `View.post()` method, then `Component.post()` would be ignored.

```py
from django_components import Component, ComponentView

class MyComponent(Component):

    def post(self, request, *args, **kwargs) -> HttpResponse:
        variable = request.POST.get("variable")
        return self.component.render_to_response(
            kwargs={"variable": variable}
        )

    class View(ComponentView):
        def setup(self, request, *args, **kwargs):
            super(request, *args, **kwargs)

            do_something_extra(request, *args, **kwargs)
```
