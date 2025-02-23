By the end of this section, we want to be able to use our components in Django templates like so:

```htmldjango
{% load component_tags %}
<!DOCTYPE html>
<html>
  <head>
    <title>My example calendar</title>
  </head>
  <body>
    {% component "calendar" / %}
  </body>
<html>
```

### 1. Register component

First, however, we need to register our component class with [`ComponentRegistry`](../../../reference/api#django_components.ComponentRegistry).

To register a component with a [`ComponentRegistry`](../../../reference/api#django_components.ComponentRegistry),
we will use the [`@register`](../../../reference/api#django_components.register)
decorator, and give it a name under which the component will be accessible from within the template:

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component, register  # <--- new

@register("calendar")  # <--- new
class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"

    def get_context_data(self):
        return {
            "date": "1970-01-01",
        }
```

This will register the component to the default registry. Default registry is loaded into the template
by calling `{% load component_tags %}` inside the template.

!!! info

    **Why do we have to register components?**

    We want to use our component as a template tag (`{% ... %}`) in Django template.

    In Django, template tags are managed by the `Library` instances. Whenever you include `{% load xxx %}`
    in your template, you are loading a `Library` instance into your template.

    [`ComponentRegistry`](../../../reference/api#django_components.ComponentRegistry) acts like a router
    and connects the registered components with the associated `Library`.

    That way, when you include `{% load component_tags %}` in your template, you are able to "call" components
    like `{% component "calendar" / %}`.

    `ComponentRegistries` also make it possible to group and share components as standalone packages.
    [Learn more here](../advanced/authoring_component_libraries.md).

!!! note

    You can create custom [`ComponentRegistry`](../../../reference/api#django_components.ComponentRegistry)
    instances, which will use different `Library` instances.
    In that case you will have to load different libraries depending on which components you want to use:

    Example 1 - Using component defined in the default registry
    ```htmldjango
    {% load component_tags %}
    <div>
      {% component "calendar" / %}
    </div>
    ```

    Example 2 - Using component defined in a custom registry
    ```htmldjango
    {% load my_custom_tags %}
    <div>
      {% my_component "table" / %}
    </div>
    ```

    Note that, because the tag name `component` is use by the default ComponentRegistry,
    the custom registry was configured to use the tag `my_component` instead. [Read more here](../advanced/component_registry.md)

### 2. Load and use the component in template

The component is now registered under the name `calendar`. All that remains to do is to load
and render the component inside a template:

```htmldjango
{% load component_tags %}  {# Load the default registry #}
<!DOCTYPE html>
<html>
  <head>
    <title>My example calendar</title>
  </head>
  <body>
    {% component "calendar" / %}  {# Render the component #}
  </body>
<html>
```

!!! info

    Component tags should end with `/` if they do not contain any [Slot fills](../fundamentals/slots.md).
    But you can also use `{% endcomponent %}` instead:

    ```htmldjango
    {% component "calendar" %}{% endcomponent %}
    ```

We defined the Calendar's template as

```htmldjango
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

and the variable `date` as `"1970-01-01"`.

Thus, the final output will look something like this:

```htmldjango
<!DOCTYPE html>
<html>
  <head>
    <title>My example calendar</title>
    <style>
      .calendar {
        width: 200px;
        background: pink;
      }
      .calendar span {
        font-weight: bold;
      }
    </style>
  </head>
  <body>
    <div class="calendar">
      Today's date is <span>1970-01-01</span>
    </div>
    <script>
      (function () {
        document.querySelector(".calendar").onclick = () => {
          alert("Clicked calendar!");
        };
      })();
    </script>
  </body>
<html>
```

This makes it possible to organize your front-end around reusable components, instead of relying on template tags
and keeping your CSS and Javascript in the static directory.

!!! info

    Remember that you can use
    [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies)
    and [`{% component_css_dependencies %}`](../../reference/template_tags.md#component_css_dependencies)
    to change where the `<script>` and `<style>` tags will be rendered (See [JS and CSS output locations](../../advanced/rendering_js_css/#js-and-css-output-locations)).

!!! info

    **How does django-components pick up registered components?**

    Notice that it was enough to add [`@register`](../../../reference/api#django_components.register) to the component.
    We didn't need to import the component file anywhere to execute it.

    This is because django-components automatically imports all Python files found in the component directories
    during an event called [Autodiscovery](../fundamentals/autodiscovery.md).

    So with Autodiscovery, it's the same as if you manually imported the component files on the `ready()` hook:

    ```python
    class MyApp(AppConfig):
        default_auto_field = "django.db.models.BigAutoField"
        name = "myapp"

        def ready(self):
            import myapp.components.calendar
            import myapp.components.table
            ...
    ```

You can now render the components in templates!

---

Currently our component always renders the same content. [Let's parametrise it, so that our Calendar component
is configurable from within the template ➡️](./parametrising_components.md)
