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

    def get_context_data(self):
        return {
            "date": "1970-01-01",
        }
```

### 1. Render the template that contains the `{% component %}` tag

If you have embedded the component in a Django template using the
[`{% component %}`](../../reference/template_tags#component) tag:

```django title="[project root]/templates/my_template.html"
{% load component_tags %}
<div>
  {% component "calendar" date="2024-12-13" / %}
</div>
```

You can simply render the template with the Django tooling:

#### With [`django.shortcuts.render()`](https://docs.djangoproject.com/en/5.1/topics/http/shortcuts/#render)

```python
from django.shortcuts import render

context = {"date": "2024-12-13"}
rendered_template = render(request, "my_template.html", context)
```

#### With [`Template.render()`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Template.render)

Either loading the template with [`get_template()`](https://docs.djangoproject.com/en/5.1/topics/templates/#django.template.loader.get_template):

```python
from django.template.loader import get_template

template = get_template("my_template.html")
context = {"date": "2024-12-13"}
rendered_template = template.render(context)
```

Or creating a new [`Template`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Template) instance:

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

### 2. Render the component directly with [`Component.render()`](../../reference/api#django_components.Component.render)

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

    The `request` object is required for some of the component's features, like using [Django's context processors](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.RequestContext).

### 3. Render the component directly with [`Component.render_to_response()`](../../reference/api#django_components.Component.render_to_response)

A common pattern in Django is to render the component and then return the resulting HTML as a response to an HTTP request.

For this, you can use the [`Component.render_to_response()`](../../reference/api#django_components.Component.render_to_response) convenience method.

`render_to_response()` accepts the same args, kwargs, slots, and more, as [`Component.render()`](../../reference/api#django_components.Component.render), but wraps the result in an [`HttpResponse`](https://docs.djangoproject.com/en/5.1/ref/request-response/#django.http.HttpResponse).

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

!!! info

    **Response class of `render_to_response`**

    While `render` method returns a plain string, `render_to_response` wraps the rendered content in a "Response" class. By default, this is [`django.http.HttpResponse`](https://docs.djangoproject.com/en/5.1/ref/request-response/#django.http.HttpResponse).

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
