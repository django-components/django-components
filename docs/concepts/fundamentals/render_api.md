When a component is being rendered, whether with [`Component.render()`](../../../reference/api#django_components.Component.render)
or [`{% component %}`](../../../reference/template_tags#component), a component instance is populated with the current inputs and context. This allows you to access things like component inputs.

We refer to these render-time-only methods and attributes as the "Render API".

Render API is available inside these [`Component`](../../../reference/api#django_components.Component) methods:

- [`get_template_data()`](../../../reference/api#django_components.Component.get_template_data)
- [`get_js_data()`](../../../reference/api#django_components.Component.get_js_data)
- [`get_css_data()`](../../../reference/api#django_components.Component.get_css_data)
- [`get_context_data()`](../../../reference/api#django_components.Component.get_context_data)
- [`on_render_before()`](../../../reference/api#django_components.Component.on_render_before)
- [`on_render_after()`](../../../reference/api#django_components.Component.on_render_after)

!!! note

    If you try to access the Render API outside of these methods, you will get a `RuntimeError`.

Example:

```python
class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # Access component's ID
        assert self.id == "c1A2b3c"

        # Access component's inputs, slots and context
        assert self.input.args == (123, "str")
        assert self.input.kwargs == {"variable": "test", "another": 1}
        footer_slot = self.input.slots["footer"]
        some_var = self.input.context["some_var"]

        # Access the request object and Django's context processors, if available
        assert self.request.GET == {"query": "something"}
        assert self.context_processors_data['user'].username == "admin"

        return {
            "variable": variable,
        }

rendered = Table.render(
    kwargs={"variable": "test", "another": 1},
    args=(123, "str"),
    slots={"footer": "MY_SLOT"},
)
```

## Overview

The Render API includes:

- [`self.id`](../render_api/#component-id) - The unique ID for the current render call
- [`self.input`](../render_api/#component-inputs) - All the component inputs
- [`self.request`](../render_api/#request-object-and-context-processors) - The request object (if available)
- [`self.context_processors_data`](../render_api/#request-object-and-context-processors) - Data from Django's context processors (if request is available)
- [`self.inject()`](../render_api/#provide-inject) - Inject data into the component

## Component ID

Component ID (or render ID) is a unique identifier for the current render call.

That means that if you call [`Component.render()`](../../../reference/api#django_components.Component.render)
multiple times, the ID will be different for each call.

It is available as [`self.id`](../../../reference/api#django_components.Component.id).

The ID is a 7-letter alphanumeric string in the format `cXXXXXX`,
where `XXXXXX` is a random string of 6 alphanumeric characters (case-sensitive).

E.g. `c1a2b3c`.

A single render ID has a chance of collision 1 in 57 billion. However, due to birthday paradox, the chance of collision increases to 1% when approaching ~33K render IDs.

Thus, there is currently a soft-cap of ~30K components rendered on a single page.

If you need to expand this limit, please open an issue on GitHub.

```python
class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # Access component's ID
        assert self.id == "c1A2b3c"

        return {}
```

## Component inputs

All the component inputs are captured and available as [`self.input`](../../../reference/api/#django_components.Component.input).

[`self.input`](../../../reference/api/#django_components.Component.input) ([`ComponentInput`](../../../reference/api/#django_components.ComponentInput)) has the mostly the same fields as the input to [`Component.render()`](../../../reference/api/#django_components.Component.render). This includes:

- `args` - List of positional arguments
- `kwargs` - Dictionary of keyword arguments
- `slots` - Dictionary of slots. Values are normalized to [`Slot`](../../../reference/api/#django_components.Slot) instances
- `context` - [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context) object that should be used to render the component
- And other kwargs passed to [`Component.render()`](../../../reference/api/#django_components.Component.render) like `type` and `render_dependencies`

Thus, use can use [`self.input.args`](../../../reference/api/#django_components.ComponentInput.args)
and [`self.input.kwargs`](../../../reference/api/#django_components.ComponentInput.kwargs)
to access the positional and keyword arguments passed to [`Component.render()`](../../../reference/api/#django_components.Component.render).

```python
class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # Access component's inputs, slots and context
        assert self.input.args == [123, "str"]
        assert self.input.kwargs == {"variable": "test", "another": 1}
        footer_slot = self.input.slots["footer"]
        some_var = self.input.context["some_var"]

        return {}

rendered = TestComponent.render(
    kwargs={"variable": "test", "another": 1},
    args=(123, "str"),
    slots={"footer": "MY_SLOT"},
)
```

## Request object and context processors

If the component was either:

- Given a [`request`](../../../reference/api/#django_components.Component.render) kwarg
- Rendered with [`RenderContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
- Nested in another component for which any of these conditions is true

Then the request object will be available in [`self.request`](../../../reference/api/#django_components.Component.request).

If the request object is available, you will also be able to access the [`context processors`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#configuring-an-engine) data in [`self.context_processors_data`](../../../reference/api/#django_components.Component.context_processors_data).

This is a dictionary with the context processors data.

If the request object is not available, then [`self.context_processors_data`](../../../reference/api/#django_components.Component.context_processors_data) will be an empty dictionary.

Read more about the request object and context processors in the [HTTP Request](./http_request.md) section.

```python
from django.http import HttpRequest

class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # Access the request object and Django's context processors
        assert self.request.GET == {"query": "something"}
        assert self.context_processors_data['user'].username == "admin"

        return {}

rendered = Table.render(
    request=HttpRequest(),
)
```

## Provide / Inject

Components support a provide / inject system as known from Vue or React.

When rendering the component, you can call [`self.inject()`](../../../reference/api/#django_components.Component.inject) with the key of the data you want to inject.

The object returned by [`self.inject()`](../../../reference/api/#django_components.Component.inject)

To provide data to components, use the [`{% provide %}`](../../../reference/template_tags#provide) template tag.

Read more about [Provide / Inject](../advanced/provide_inject.md).

```python
class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # Access provided data
        data = self.inject("some_data")
        assert data.some_data == "some_data"
```
