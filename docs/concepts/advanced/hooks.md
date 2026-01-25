_New in version 0.96_

Intercept the rendering lifecycle with Component hooks.

Unlike the [extension hooks](../../reference/extension_hooks.md), these are defined directly
on the [`Component`](../../reference/api.md#django_components.Component) class.

## Available hooks

### `on_render_before`

```py
def on_render_before(
    self: Component,
    context: Context,
    template: Template | None,
) -> None:
```

[`Component.on_render_before`](../../reference/api.md#django_components.Component.on_render_before) runs just before the component's template is rendered.

It is called for every component, including nested ones, as part of
the component render lifecycle.

It receives the [Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
and the [Template](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template)
as arguments.

The `template` argument is `None` if the component has no template.

**Example:**

You can use this hook to access the context or the template:

```py
from django.template import Context, Template
from django_components import Component

class MyTable(Component):
    def on_render_before(self, context: Context, template: Template | None) -> None:
        # Insert value into the Context
        context["from_on_before"] = ":)"

        assert isinstance(template, Template)
```

!!! warning

    If you want to pass data to the template, prefer using
    [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data)
    instead of this hook.

!!! warning

    Do NOT modify the template in this hook. The template is reused across renders.

### `on_render`

_New in version 0.140_

```py
def on_render(
    self: Component,
    context: Context,
    template: Template | None,
) -> str | SafeString | OnRenderGenerator | None:
```

[`Component.on_render`](../../reference/api.md#django_components.Component.on_render) does the actual rendering.

You can override this method to:

- Change what template gets rendered
- Modify the context
- Modify the rendered output after it has been rendered
- Handle errors

The default implementation renders the component's
[Template](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template)
with the given
[Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context).

```py
class MyTable(Component):
    def on_render(self, context, template):
        if template:
            return template.render(context)
```

The `template` argument is `None` if the component has no template.

#### Modifying rendered template

To change what gets rendered, you can:

- Render a component
- Render a template
- Return a string or SafeString

```py
class MyTable(Component):
    def on_render(self, context, template):
        # Return a string
        return "<p>Hello</p>"

        # Render a component
        return MyOtherTable.render(
            args=self.args,
            kwargs=self.kwargs,
            slots=self.slots,
            context=context,
        )

        # Render a template
        return get_template("my_other_table.html").render(context)
```

You can also use [`on_render()`](../../reference/api.md#django_components.Component.on_render) as a router,
rendering other components based on the parent component's arguments:

```py
class MyTable(Component):
    def on_render(self, context, template):
        # Select different component based on `feature_new_table` kwarg
        if self.kwargs.get("feature_new_table"):
            comp_cls = NewTable
        else:
            comp_cls = OldTable

        # Render the selected component
        return comp_cls.render(
            args=self.args,
            kwargs=self.kwargs,
            slots=self.slots,
            context=context,
        )
```

#### Post-processing rendered template

When you render the original template in [`on_render()`](../../reference/api.md#django_components.Component.on_render) as:

```py
class MyTable(Component):
    def on_render(self, context, template):
        result = template.render(context)
```

The result is NOT the final output, but an intermediate result. Nested components
are not rendered yet.

Instead, django-components needs to take this result and process it
to actually render the child components.

This is not a problem when you return the result directly as above. Django-components will take care of rendering the child components.

But if you want to access the final output, you must `yield` the result instead of returning it.

Yielding the result will return a tuple of `(rendered_html, error)`:

- On success, the error is `None` - `(string, None)`
- On failure, the rendered HTML is `None` - `(None, Exception)`

```py
class MyTable(Component):
    def on_render(self, context, template):
        html, error = yield lambda: template.render(context)

        if error is None:
            # The rendering succeeded
            return html
        else:
            # The rendering failed
            print(f"Error: {error}")
```

!!! warning

    Notice that we actually yield a **lambda function** instead of the result itself.
    This is because calling `template.render(context)` may raise an exception.
    
    When you wrap the result in a lambda function, and the rendering fails,
    the error will be yielded back in the `(None, Exception)` tuple.

At this point you can do 3 things:

1. Return new HTML

    The new HTML will be used as the final output.

    If the original template raised an error, the original error will be ignored.

    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            html, error = yield lambda: template.render(context)

            # Fallback if rendering failed
            # Otherwise, we keep the original HTML
            if error is not None:
                return "FALLBACK HTML"
    ```

2. Raise new exception

    The new exception is what will bubble up from the component.
    
    The original HTML and original error will be ignored.

    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            html, error = yield lambda: template.render(context)

            # Override the original error
            # Otherwise, we keep the original HTML
            if error is not None:
                raise Exception("My new error") from error
    ```

3. No change - Return nothing or `None`

    If you neither raise an exception, nor return a new HTML,
    then the original HTML / error will be used:

    - If rendering succeeded, the original HTML will be used as the final output.
    - If rendering failed, the original error will be propagated.

    This can be useful for side effects like tracking the errors that occurred during the rendering:

    ```py
    from myapp.metrics import track_rendering_error

    class MyTable(Component):
        def on_render(self, context, template):
            html, error = yield lambda: template.render(context)

            # Track how many times the rendering failed
            if error is not None:
                track_rendering_error(error)
    ```

#### Multiple yields

You can yield multiple times within the same [`on_render()`](../../reference/api.md#django_components.Component.on_render) method. This is useful for complex rendering scenarios:

```py
class MyTable(Component):
    def on_render(self, context, template):
        # First yield
        with context.push({"mode": "header"}):
            header_html, header_error = yield lambda: template.render(context)
        
        # Second yield
        with context.push({"mode": "body"}):
            body_html, body_error = yield lambda: template.render(context)
        
        # Third yield
        footer_html, footer_error = yield "Footer content"
        
        # Process all
        if header_error or body_error or footer_error:
            return "Error occurred during rendering"
        
        return f"{header_html}\n{body_html}\n{footer_html}"
```

Each yield operation is independent and returns its own `(html, error)` tuple, allowing you to handle each rendering result separately.

#### Example: ErrorBoundary

[`on_render()`](../../reference/api.md#django_components.Component.on_render) can be used to
implement React's [ErrorBoundary](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary).

That is, a component that catches errors in nested components and displays a fallback UI instead:

```django
{% component "error_boundary" %}
  {% fill "default" %}
    {% component "nested_component" %}
  {% endfill %}
  {% fill "fallback" %}
    Sorry, something went wrong.
  {% endfill %}
{% endcomponent %}
```

To implement this, we render the fallback slot in [`on_render()`](../../reference/api.md#django_components.Component.on_render)
and return it if an error occured:

```djc_py
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django_components import Component, OnRenderGenerator, SlotInput, types

class ErrorFallback(Component):
    class Slots:
        default: SlotInput | None = None
        fallback: SlotInput | None = None

    template: types.django_html = """
        {% if not error %}
            {% slot "default" default / %}
        {% else %}
            {% slot "fallback" error=error / %}
        {% endif %}
    """

    def on_render(
        self,
        context: Context,
        template: Template,
    ) -> OnRenderGenerator:
        fallback_slot = self.slots.default

        result, error = yield lambda: template.render(context)

        # No error, return the original result
        if error is None:
            return None

        # Error, return the fallback
        if fallback_slot is not None:
            # Render the template second time, this time rendering
            # the fallback branch
            with context.push({"error": error}):
                return template.render(context)
        else:
            return mark_safe("<pre>An error occurred</pre>")
```

### `on_render_after`

```py
def on_render_after(
    self: Component,
    context: Context,
    template: Template | None,
    result: str | SafeString | None,
    error: Exception | None,
) -> str | SafeString | None:
```

[`on_render_after()`](../../reference/api.md#django_components.Component.on_render_after) runs when the component was fully rendered,
including all its children.

It receives the same arguments as [`on_render_before()`](#on_render_before),
plus the outcome of the rendering:

- `result`: The rendered output of the component. `None` if the rendering failed.
- `error`: The error that occurred during the rendering, or `None` if the rendering succeeded.

[`on_render_after()`](../../reference/api.md#django_components.Component.on_render_after) behaves the same way
as the second part of [`on_render()`](#on_render) (after the `yield`).

```py
class MyTable(Component):
    def on_render_after(self, context, template, result, error):
        # If rendering succeeded, keep the original result
        # Otherwise, print the error
        if error is not None:
            print(f"Error: {error}")
```

Same as [`on_render()`](#on_render),
you can return a new HTML, raise a new exception, or return nothing:

1. Return new HTML

    The new HTML will be used as the final output.

    If the original template raised an error, the original error will be ignored.

    ```py
    class MyTable(Component):
        def on_render_after(self, context, template, result, error):
            # Fallback if rendering failed
            # Otherwise, we keep the original HTML
            if error is not None:
                return "FALLBACK HTML"
    ```

2. Raise new exception

    The new exception is what will bubble up from the component.
    
    The original HTML and original error will be ignored.

    ```py
    class MyTable(Component):
        def on_render_after(self, context, template, result, error):
            # Override the original error
            # Otherwise, we keep the original HTML
            if error is not None:
                raise Exception("My new error") from error
    ```

3. No change - Return nothing or `None`

    If you neither raise an exception, nor return a new HTML,
    then the original HTML / error will be used:

    - If rendering succeeded, the original HTML will be used as the final output.
    - If rendering failed, the original error will be propagated.

    This can be useful for side effects like tracking the errors that occurred during the rendering:

    ```py
    from myapp.metrics import track_rendering_error

    class MyTable(Component):
        def on_render_after(self, context, template, result, error):
            # Track how many times the rendering failed
            if error is not None:
                track_rendering_error(error)
    ```

## Example: Tabs

You can use hooks together with [provide / inject](provide_inject.md) to create components
that accept a list of items via a slot.

In the example below, each `tab_item` component will be rendered on a separate tab page, but they are all defined in the default slot of the `tabs` component.

[See here for how it was done](https://github.com/django-components/django-components/discussions/540)

```django
{% component "tabs" %}
  {% component "tab_item" header="Tab 1" %}
    <p>
      hello from tab 1
    </p>
    {% component "button" %}
      Click me!
    {% endcomponent %}
  {% endcomponent %}

  {% component "tab_item" header="Tab 2" %}
    Hello this is tab 2
  {% endcomponent %}
{% endcomponent %}
```
