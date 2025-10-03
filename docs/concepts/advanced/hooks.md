_New in version 0.96_

Intercept the rendering lifecycle with Component hooks.

Unlike the [extension hooks](../../../reference/extension_hooks/), these are defined directly
on the [`Component`](../../../reference/api#django_components.Component) class.

## Available hooks

### `on_render_before`

```py
def on_render_before(
    self: Component,
    context: Context,
    template: Optional[Template],
) -> None:
```

[`Component.on_render_before`](../../../reference/api#django_components.Component.on_render_before) runs just before the component's template is rendered.

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
    def on_render_before(self, context: Context, template: Optional[Template]) -> None:
        # Insert value into the Context
        context["from_on_before"] = ":)"

        assert isinstance(template, Template)
```

!!! warning

    If you want to pass data to the template, prefer using
    [`get_template_data()`](../../../reference/api#django_components.Component.get_template_data)
    instead of this hook.

!!! warning

    Do NOT modify the template in this hook. The template is reused across renders.

    Since this hook is called for every component, this means that the template would be modified
    every time a component is rendered.

### `on_render`

_New in version 0.140_

```py
def on_render(
    self: Component,
    context: Context,
    template: Optional[Template],
) -> Union[str, SafeString, OnRenderGenerator, None]:
```

[`Component.on_render`](../../../reference/api#django_components.Component.on_render) does the actual rendering.

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
        if template is None:
            return None
        else:
            return template.render(context)
```

The `template` argument is `None` if the component has no template.

#### Modifying rendered template

To change what gets rendered, you can:

- Render a different template
- Render a component
- Return a different string or SafeString

```py
class MyTable(Component):
    def on_render(self, context, template):
        return "Hello"
```

You can also use [`on_render()`](../../../reference/api#django_components.Component.on_render) as a router,
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

When you render the original template in [`on_render()`](../../../reference/api#django_components.Component.on_render) as:

```py
class MyTable(Component):
    def on_render(self, context, template):
        result = template.render(context)
```

The result is NOT the final output, but an intermediate result. Nested components
are not rendered yet.

Instead, django-components needs to take this result and process it
to actually render the child components.

To access the final output, you can `yield` the result instead of returning it.

This will return a tuple of (rendered HTML, error). The error is `None` if the rendering succeeded.

```py
class MyTable(Component):
    def on_render(self, context, template):
        html, error = yield template.render(context)

        if error is None:
            # The rendering succeeded
            return html
        else:
            # The rendering failed
            print(f"Error: {error}")
```

At this point you can do 3 things:

1. Return a new HTML

    The new HTML will be used as the final output.

    If the original template raised an error, it will be ignored.

    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            html, error = yield template.render(context)

            return "NEW HTML"
    ```

2. Raise a new exception

    The new exception is what will bubble up from the component.
    
    The original HTML and original error will be ignored.

    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            html, error = yield template.render(context)

            raise Exception("Error message")
    ```

3. Return nothing (or `None`) to handle the result as usual

    If you don't raise an exception, and neither return a new HTML,
    then original HTML / error will be used:

    - If rendering succeeded, the original HTML will be used as the final output.
    - If rendering failed, the original error will be propagated.

    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            html, error = yield template.render(context)

            if error is not None:
                # The rendering failed
                print(f"Error: {error}")
    ```

#### Multiple yields

You can yield multiple times within the same `on_render` method. This is useful for complex rendering scenarios where you need to render different templates or handle multiple rendering operations:

```py
class MyTable(Component):
    def on_render(self, context, template):
        # First yield - render with one context
        with context.push({"mode": "header"}):
            header_html, header_error = yield template.render(context)
        
        # Second yield - render with different context
        with context.push({"mode": "body"}):
            body_html, body_error = yield template.render(context)
        
        # Third yield - render a string directly
        footer_html, footer_error = yield "Footer content"
        
        # Process all results and return final output
        if header_error or body_error or footer_error:
            return "Error occurred during rendering"
        
        return f"{header_html}\n{body_html}\n{footer_html}"
```

Each yield operation is independent and returns its own `(html, error)` tuple, allowing you to handle each rendering result separately.

#### Example: ErrorBoundary

[`on_render()`](../../../reference/api#django_components.Component.on_render) can be used to
implement React's [ErrorBoundary](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary).

That is, a component that catches errors in nested components and displays a fallback UI instead:

```django
{% component "error_boundary" %}
  {% fill "content" %}
    {% component "nested_component" %}
  {% endfill %}
  {% fill "fallback" %}
    Sorry, something went wrong.
  {% endfill %}
{% endcomponent %}
```

To implement this, we render the fallback slot in [`on_render()`](../../../reference/api#django_components.Component.on_render)
and return it if an error occured:

```djc_py
class ErrorFallback(Component):
    class Kwargs(NamedTuple):
        fallback: Optional[str] = None

    class Slots(NamedTuple):
        default: Optional[SlotInput] = None
        fallback: Optional[SlotInput] = None

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
        fallback_kwarg = cast(ErrorFallback.Kwargs, self.kwargs).fallback
        fallback_slot = cast(ErrorFallback.Slots, self.slots).default

        if fallback_kwarg is not None and fallback_slot is not None:
            raise TemplateSyntaxError(
                "The 'fallback' argument and slot cannot both be provided. Please provide only one.",
            )

        result, error = yield template.render(context)

        # No error, return the result
        if error is None:
            return result

        # Error, return the fallback
        if fallback_kwarg is not None:
            return fallback_kwarg
        elif fallback_slot is not None:
            # Render the template second time, this time with the error
            # So that we render the fallback slot with proper access to the outer context and whatnot.
            with context.push({"error": error}):
                return template.render(context)
        else:
            return ""
```

### `on_render_after`

```py
def on_render_after(
    self: Component,
    context: Context,
    template: Optional[Template],
    result: Optional[str | SafeString],
    error: Optional[Exception],
) -> Union[str, SafeString, None]:
```

[`on_render_after()`](../../../reference/api#django_components.Component.on_render_after) runs when the component was fully rendered,
including all its children.

It receives the same arguments as [`on_render_before()`](#on_render_before),
plus the outcome of the rendering:

- `result`: The rendered output of the component. `None` if the rendering failed.
- `error`: The error that occurred during the rendering, or `None` if the rendering succeeded.

[`on_render_after()`](../../../reference/api#django_components.Component.on_render_after) behaves the same way
as the second part of [`on_render()`](#on_render) (after the `yield`).

```py
class MyTable(Component):
    def on_render_after(self, context, template, result, error):
        if error is None:
            # The rendering succeeded
            return result
        else:
            # The rendering failed
            print(f"Error: {error}")
```

Same as [`on_render()`](#on_render),
you can return a new HTML, raise a new exception, or return nothing:

1. Return a new HTML

    The new HTML will be used as the final output.

    If the original template raised an error, it will be ignored.

    ```py
    class MyTable(Component):
        def on_render_after(self, context, template, result, error):
            return "NEW HTML"
    ```

2. Raise a new exception

    The new exception is what will bubble up from the component.
    
    The original HTML and original error will be ignored.

    ```py
    class MyTable(Component):
        def on_render_after(self, context, template, result, error):
            raise Exception("Error message")
    ```

3. Return nothing (or `None`) to handle the result as usual

    If you don't raise an exception, and neither return a new HTML,
    then original HTML / error will be used:

    - If rendering succeeded, the original HTML will be used as the final output.
    - If rendering failed, the original error will be propagated.

    ```py
    class MyTable(Component):
        def on_render_after(self, context, template, result, error):
            if error is not None:
                # The rendering failed
                print(f"Error: {error}")
    ```

## Example

You can use hooks together with [provide / inject](#how-to-use-provide--inject) to create components
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
