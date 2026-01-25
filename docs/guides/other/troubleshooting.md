As larger projects get more complex, it can be hard to debug issues. Django Components provides a number of tools and approaches that can help you with that.

## Component and slot highlighting

Django Components provides a visual debugging feature that helps you understand the structure and boundaries of your components and slots. When enabled, it adds a colored border and a label around each component and slot on your rendered page.

To enable component and slot highlighting for all components and slots, set `highlight_components` and `highlight_slots` to `True` in [extensions defaults](../../reference/settings.md#django_components.app_settings.ComponentsSettings.extensions_defaults) in your `settings.py` file:

```python
from django_components import ComponentsSettings

COMPONENTS = ComponentsSettings(
    extensions_defaults={
        "debug_highlight": {
            "highlight_slots": True,
            "highlight_components": True,
        },
    },
)
```

Alternatively, you can enable highlighting for specific components by setting `Component.DebugHighlight.highlight_components` to `True`:

```python
class MyComponent(Component):
    class DebugHighlight:
        highlight_components = True
        highlight_slots = True
```

Components will be highlighted with a **blue** border and label:

![Component highlighting example](../../images/debug-highlight-components.png)

While the slots will be highlighted with a **red** border and label:

![Slot highlighting example](../../images/debug-highlight-slots.png)

!!! warning

    Use this feature ONLY in during development. Do NOT use it in production.

## Template position in errors

When a component or template tag raises an error, django-components automatically includes the exact tag
that caused the error, as found in the template. This makes it easy to locate the problematic code in your template files.

For example, this is the error message when a component receives incorrect arguments:

![Template position in error message](../../images/debug-error-component-underline.png)

## Component path in errors

When an error occurs, the error message will show the path to the component that
caused the error. E.g.

```
KeyError: "An error occured while rendering components MyPage > MyLayout > MyComponent > Childomponent(slot:content)
```

The error message contains also the slot paths, so if you have a template like this:

```django
{% component "my_page" %}
    {% slot "content" %}
        {% component "table" %}
            {% slot "header" %}
                {% component "table_header" %}
                    ...  {# ERROR HERE #}
                {% endcomponent %}
            {% endslot %}
        {% endcomponent %}
    {% endslot %}
{% endcomponent %}
```

Then the error message will show the path to the component that caused the error:

```
KeyError: "An error occured while rendering components my_page > layout > layout(slot:content) > my_page(slot:content) > table > table(slot:header) > table_header > table_header(slot:content)
```

## Debug and trace logging

Django components supports [logging with Django](https://docs.djangoproject.com/en/5.2/howto/logging/#logging-how-to).

To configure logging for Django components, set the `django_components` logger in
[`LOGGING`](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-LOGGING)
in `settings.py` (below).

Also see the [`settings.py` file in sampleproject](https://github.com/django-components/django-components/blob/master/sampleproject/sampleproject/settings.py) for a real-life example.

```py
import logging
import sys

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    "handlers": {
        "console": {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    "loggers": {
        "django_components": {
            "level": logging.DEBUG,
            "handlers": ["console"],
        },
    },
}
```

!!! info

    To set TRACE level, set `"level"` to `5`:

    ```py
    LOGGING = {
        "loggers": {
            "django_components": {
                "level": 5,
                "handlers": ["console"],
            },
        },
    }
    ```

### Logger levels

As of v0.126, django-components primarily uses these logger levels:

- `DEBUG`: Report on loading associated HTML / JS / CSS files, autodiscovery, etc.
- `TRACE`: Detailed interaction of components and slots. Logs when template tags,
  components, and slots are started / ended rendering, and when a slot is filled.

## Slot origin

When you pass a slot fill to a Component, the component and slot names is remebered
on the slot object.

Thus, you can check where a slot was filled from by printing it out:

```python
class MyComponent(Component):
    def on_render_before(self, context: Context, template: Template | None):
        print(self.slots)
```

might print:

```python
{
    'content': <Slot component_name='layout' slot_name='content'>,
    'header': <Slot component_name='my_page' slot_name='header'>,
    'left_panel': <Slot component_name='layout' slot_name='left_panel'>,
}
```

## Agentic debugging

All the features above make django-components to work really well with coding AI agents
like Github Copilot or CursorAI.

To debug component rendering with LLMs, you want to provide the LLM with:

1. The components source code
2. The rendered output
3. As much additional context as possible

Your codebase already contains the components source code, but not the latter two.

### Providing rendered output

To provide the LLM with the rendered output, you can simply export the rendered output to a file.

```python
rendered = ProjectPage.render(...)
with open("result.html", "w") as f:
    f.write(rendered)
```

If you're using `render_to_response`, access the output from the `HttpResponse` object:

```python
response = ProjectPage.render_to_response(...)
with open("result.html", "wb") as f:
    f.write(response.content)
```

### Providing contextual logs

Next, we provide the agent with info on HOW we got the result that we have. We do so
by providing the agent with the trace-level logs.

In your `settings.py`, configure the trace-level logs to be written to the `django_components.log` file:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "django_components.log",
            "mode": "w",  # Overwrite the file each time
        },
    },
    "loggers": {
        "django_components": {
            "level": 5,
            "handlers": ["file"],
        },
    },
}
```

### Prompting the agent

Now, you can prompt the agent and include the trace log and the rendered output to guide the agent with debugging.

> I have a django-components (DJC) project. DJC is like if Vue or React component-based web development but made for Django ecosystem.
> 
> In the view `project_view`, I am rendering the `ProjectPage` component. However, the output is not as expected.
> The output is missing the tabs.
>
> You have access to the full log trace in `django_components.log`.
>
> You can also see the rendered output in `result.html`.
>
> With this information, help me debug the issue.
>
> First, tell me what kind of info you would be looking for in the logs, and why (how it relates to understanding the cause of the bug).
>
> Then tell me if that info was there, and what the implications are.
>
> Finally, tell me what you would do to fix the issue.
