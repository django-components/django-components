Our calendar component can accept and pre-process data, defines its own CSS and JS, and can be used in templates.

...But how do we actually render the components into HTML?

There's 3 ways to render a component:

- Render the template that contains the [`{% component %}`](../../reference/template_tags#component) tag
- Render the component directly with [`Component.render()`](../../reference/api#django_components.Component.render)
- Render the component directly with [`Component.render_to_response()`](../../reference/api#django_components.Component.render_to_response)

As a reminder, this is what the calendar component looks like:

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": "1970-01-01",
        }
```

### 1. Render the template

If you have embedded the component in a Django template using the
[`{% component %}`](../../reference/template_tags#component) tag:

```django title="[project root]/templates/my_template.html"
{% load component_tags %}
<div>
  {% component "calendar" date="2024-12-13" / %}
</div>
```

You can simply render the template with the Django tooling:

#### With [`django.shortcuts.render()`](https://docs.djangoproject.com/en/5.2/topics/http/shortcuts/#render)

```python
from django.shortcuts import render

context = {"date": "2024-12-13"}
rendered_template = render(request, "my_template.html", context)
```

#### With [`Template.render()`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template.render)

Either loading the template with [`get_template()`](https://docs.djangoproject.com/en/5.2/topics/templates/#django.template.loader.get_template):

```python
from django.template.loader import get_template

template = get_template("my_template.html")
context = {"date": "2024-12-13"}
rendered_template = template.render(context)
```

Or creating a new [`Template`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template) instance:

```python
from django.template import Template

template = Template("""
{% load component_tags %}
<div>
  {% component "calendar" date="2024-12-13" / %}
</div>
""")
rendered_template = template.render()
```

### 2. Render the component

You can also render the component directly with [`Component.render()`](../../reference/api#django_components.Component.render), without wrapping the component in a template.

```python
from components.calendar import Calendar

calendar = Calendar
rendered_component = calendar.render()
```

You can pass args, kwargs, slots, and more, to the component:

```python
from components.calendar import Calendar

calendar = Calendar
rendered_component = calendar.render(
    args=["2024-12-13"],
    kwargs={
        "extra_class": "my-class"
    },
    slots={
        "date": "<b>2024-12-13</b>"
    },
)
```

!!! info

    Among other, you can pass also the `request` object to the `render` method:

    ```python
    from components.calendar import Calendar

    calendar = Calendar
    rendered_component = calendar.render(request=request)
    ```

    The `request` object is required for some of the component's features, like using [Django's context processors](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext).

### 3. Render the component to HttpResponse

A common pattern in Django is to render the component and then return the resulting HTML as a response to an HTTP request.

For this, you can use the [`Component.render_to_response()`](../../reference/api#django_components.Component.render_to_response) convenience method.

`render_to_response()` accepts the same args, kwargs, slots, and more, as [`Component.render()`](../../reference/api#django_components.Component.render), but wraps the result in an [`HttpResponse`](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpResponse).

```python
from components.calendar import Calendar

def my_view(request):
    response = Calendar.render_to_response(
        args=["2024-12-13"],
        kwargs={
            "extra_class": "my-class"
        },
        slots={
            "date": "<b>2024-12-13</b>"
        },
        request=request,
    )
    return response
```

!!! info "Response class of `render_to_response`"

    While `render` method returns a plain string, `render_to_response` wraps the rendered content in a "Response" class. By default, this is [`django.http.HttpResponse`](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpResponse).

    If you want to use a different Response class in `render_to_response`, set the [`Component.response_class`](../../reference/api#django_components.Component.response_class) attribute:

    ```py
    class MyCustomResponse(HttpResponse):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            # Configure response
            self.headers = ...
            self.status = ...

    class SimpleComponent(Component):
        response_class = MyCustomResponse
    ```

### 4. Rendering slots

Slots content are automatically escaped by default to prevent XSS attacks.

In other words, it's as if you would be using Django's [`escape()`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#std-templatefilter-escape) on the slot contents / result:

```python
from django.utils.html import escape

class Calendar(Component):
    template = """
        <div>
            {% slot "date" default date=date / %}
        </div>
    """

Calendar.render(
    slots={
        "date": escape("<b>Hello</b>"),
    }
)
```

To disable escaping, you can wrap the slot string or slot result in Django's [`mark_safe()`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.mark_safe):

```py
Calendar.render(
    slots={
        # string
        "date": mark_safe("<b>Hello</b>"),

        # function
        "date": lambda ctx: mark_safe("<b>Hello</b>"),
    }
)
```

!!! info

    Read more about Django's
    [`format_html`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.html.format_html)
    and [`mark_safe`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.mark_safe).

### 5. Component views and URLs

For web applications, it's common to define endpoints that serve HTML content (AKA views).

You can define the view endpoints directly on your component class by using the nested [`Component.View`](../../reference/api#django_components.Component.View) class.

This is a great place for:

- Web pages - Page components can use [`Component.View.get()`](../../reference/api#django_components.ComponentView.get) to return the entire web page upon GET request.

- Fragments - Fragment components (partials) can use [`Component.View.get()`](../../reference/api#django_components.ComponentView.get) to return HTML fragments upon GET request (to be used with HTMX or similar libraries).

- Form submission - Define [`Component.View.post()`](../../reference/api#django_components.ComponentView.post) to handle a POST requests.

Read more on [Component views and URLs](../../concepts/fundamentals/component_views_urls).

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

Next, define the URL route which will trigger these handlers.

You can either:

1. Use automatically generated component URL using [`get_component_url()`](../../reference/api#django_components.get_component_url):

    ```py
    from django_components import get_component_url

    url = get_component_url(Calendar)
    ```

    This HTTP endpoint is automatically registered in Django's `urlpatterns` when you define a handler.

    To explicitly enable/disable the component's URL, use [`Component.View.public`](../../../reference/api#django_components.ComponentView.public):

    ```djc_py
    from django_components import Component

    class Calendar(Component):
        class View:
            public = False
    ```

2. Manually assign the URL by setting [`Component.as_view()`](../../reference/api#django_components.Component.as_view) to your `urlpatterns`:

    ```djc_py
    from django.urls import path
    from components.calendar import Calendar

    urlpatterns = [
        path("calendar/", Calendar.as_view()),
    ]
    ```

And with that, you're all set! When you visit the URL, the component will be rendered and the content will be returned.

The `get()`, `post()`, etc methods will receive the [`HttpRequest`](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpRequest) object as the first argument. So you can parametrize how the component is rendered for example by passing extra query parameters to the URL:

```
http://localhost:8000/calendar/?date=2024-12-13
```

!!! info "Customizing component URLs"

    By default, the component URL is `components/{component.class_id}/`.

    You can customize the auto-generated component URL path by overriding [`Component.View.get_route_path()`](../../reference/api#django_components.ComponentView.get_route_path).
    
    This allows you to use route parameters in your component URLs, e.g.:
    
    ```
    my/custom/path/<int:my_id>/
    ```

    Read more about [modifying component URLs](../../concepts/fundamentals/component_views_urls#modifying-the-route-path).
