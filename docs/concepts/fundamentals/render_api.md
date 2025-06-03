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

Example:

```python
class Table(Component):
    def on_render_before(self, context, template):
        # Access component's ID
        assert self.id == "c1A2b3c"

        # Access component's inputs, slots and context
        assert self.args == [123, "str"]
        assert self.kwargs == {"variable": "test", "another": 1}
        footer_slot = self.slots["footer"]
        some_var = self.context["some_var"]

    def get_template_data(self, args, kwargs, slots, context):
        # Access the request object and Django's context processors, if available
        assert self.request.GET == {"query": "something"}
        assert self.context_processors_data['user'].username == "admin"

rendered = Table.render(
    kwargs={"variable": "test", "another": 1},
    args=(123, "str"),
    slots={"footer": "MY_SLOT"},
)
```

## Overview

The Render API includes:

- Component inputs:
    - [`self.args`](../render_api/#args) - The positional arguments for the current render call
    - [`self.kwargs`](../render_api/#kwargs) - The keyword arguments for the current render call
    - [`self.slots`](../render_api/#slots) - The slots for the current render call
    - [`self.raw_args`](../render_api/#args) - Unmodified positional arguments for the current render call
    - [`self.raw_kwargs`](../render_api/#kwargs) - Unmodified keyword arguments for the current render call
    - [`self.raw_slots`](../render_api/#slots) - Unmodified slots for the current render call
    - [`self.context`](../render_api/#context) - The context for the current render call
    - [`self.deps_strategy`](../../advanced/rendering_js_css#dependencies-strategies) - The strategy for rendering dependencies

- Request-related:
    - [`self.request`](../render_api/#request-and-context-processors) - The request object (if available)
    - [`self.context_processors_data`](../render_api/#request-and-context-processors) - Data from Django's context processors

- Provide / inject:
    - [`self.inject()`](../render_api/#provide-inject) - Inject data into the component

- Template tag metadata:
    - [`self.node`](../render_api/#template-tag-metadata) - The [`ComponentNode`](../../../reference/api/#django_components.ComponentNode) instance
    - [`self.registry`](../render_api/#template-tag-metadata) - The [`ComponentRegistry`](../../../reference/api/#django_components.ComponentRegistry) instance
    - [`self.registered_name`](../render_api/#template-tag-metadata) - The name under which the component was registered
    - [`self.outer_context`](../render_api/#template-tag-metadata) - The context outside of the [`{% component %}`](../../../reference/template_tags#component) tag

- Other metadata:
    - [`self.id`](../render_api/#component-id) - The unique ID for the current render call

## Component inputs

### Args

The `args` argument as passed to
[`Component.get_template_data()`](../../../reference/api/#django_components.Component.get_template_data).

If you defined the [`Component.Args`](../../../reference/api/#django_components.Component.Args) class,
then the [`Component.args`](../../../reference/api/#django_components.Component.args) property will return an instance of that class.

Otherwise, `args` will be a plain list.

Use [`self.raw_args`](../../../reference/api/#django_components.Component.raw_args)
to access the positional arguments as a plain list irrespective of [`Component.Args`](../../../reference/api/#django_components.Component.Args).

**Example:**

With `Args` class:

```python
from django_components import Component

class Table(Component):
    class Args(NamedTuple):
        page: int
        per_page: int

    def on_render_before(self, context: Context, template: Template) -> None:
        assert self.args.page == 123
        assert self.args.per_page == 10

rendered = Table.render(
    args=[123, 10],
)
```

Without `Args` class:

```python
from django_components import Component

class Table(Component):
    def on_render_before(self, context: Context, template: Template) -> None:
        assert self.args[0] == 123
        assert self.args[1] == 10
```

### Kwargs

The `kwargs` argument as passed to
[`Component.get_template_data()`](../../../reference/api/#django_components.Component.get_template_data).

If you defined the [`Component.Kwargs`](../../../reference/api/#django_components.Component.Kwargs) class,
then the [`Component.kwargs`](../../../reference/api/#django_components.Component.kwargs) property will return an instance of that class.

Otherwise, `kwargs` will be a plain dictionary.

Use [`self.raw_kwargs`](../../../reference/api/#django_components.Component.raw_kwargs)
to access the keyword arguments as a plain dictionary irrespective of [`Component.Kwargs`](../../../reference/api/#django_components.Component.Kwargs).

**Example:**

With `Kwargs` class:

```python
from django_components import Component

class Table(Component):
    class Kwargs(NamedTuple):
        page: int
        per_page: int

    def on_render_before(self, context: Context, template: Template) -> None:
        assert self.kwargs.page == 123
        assert self.kwargs.per_page == 10

rendered = Table.render(
    kwargs={"page": 123, "per_page": 10},
)
```

Without `Kwargs` class:

```python
from django_components import Component

class Table(Component):
    def on_render_before(self, context: Context, template: Template) -> None:
        assert self.kwargs["page"] == 123
        assert self.kwargs["per_page"] == 10
```

### Slots

The `slots` argument as passed to
[`Component.get_template_data()`](../../../reference/api/#django_components.Component.get_template_data).

If you defined the [`Component.Slots`](../../../reference/api/#django_components.Component.Slots) class,
then the [`Component.slots`](../../../reference/api/#django_components.Component.slots) property will return an instance of that class.

Otherwise, `slots` will be a plain dictionary.

Use [`self.raw_slots`](../../../reference/api/#django_components.Component.raw_slots)
to access the slots as a plain dictionary irrespective of [`Component.Slots`](../../../reference/api/#django_components.Component.Slots).

**Example:**

With `Slots` class:

```python
from django_components import Component, Slot, SlotInput

class Table(Component):
    class Slots(NamedTuple):
        header: SlotInput
        footer: SlotInput

    def on_render_before(self, context: Context, template: Template) -> None:
        assert isinstance(self.slots.header, Slot)
        assert isinstance(self.slots.footer, Slot)

rendered = Table.render(
    slots={
        "header": "MY_HEADER",
        "footer": lambda ctx: "FOOTER: " + ctx.data["user_id"],
    },
)
```

Without `Slots` class:

```python
from django_components import Component, Slot, SlotInput

class Table(Component):
    def on_render_before(self, context: Context, template: Template) -> None:
        assert isinstance(self.slots["header"], Slot)
        assert isinstance(self.slots["footer"], Slot)
```

### Context

The `context` argument as passed to
[`Component.get_template_data()`](../../../reference/api/#django_components.Component.get_template_data).

This is Django's [Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
with which the component template is rendered.

If the root component or template was rendered with
[`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
then this will be an instance of `RequestContext`.

Whether the context variables defined in `context` are available to the template depends on the
[context behavior mode](../../../reference/settings#django_components.app_settings.ComponentsSettings.context_behavior):

- In `"django"` context behavior mode, the template will have access to the keys of this context.

- In `"isolated"` context behavior mode, the template will NOT have access to this context,
    and data MUST be passed via component's args and kwargs.

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
```

## Request and context processors

Components have access to the request object and context processors data if the component was:

- Given a [`request`](../../../reference/api/#django_components.Component.render) kwarg directly
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

## Template tag metadata

If the component is rendered with [`{% component %}`](../../../reference/template_tags#component) template tag,
the following metadata is available:

- [`self.node`](../../../reference/api/#django_components.Component.node) - The [`ComponentNode`](../../../reference/api/#django_components.ComponentNode) instance
- [`self.registry`](../../../reference/api/#django_components.Component.registry) - The [`ComponentRegistry`](../../../reference/api/#django_components.ComponentRegistry) instance
  that was used to render the component
- [`self.registered_name`](../../../reference/api/#django_components.Component.registered_name) - The name under which the component was registered
- [`self.outer_context`](../../../reference/api/#django_components.Component.outer_context) - The context outside of the [`{% component %}`](../../../reference/template_tags#component) tag

    ```django
    {% with abc=123 %}
        {{ abc }} {# <--- This is in outer context #}
        {% component "my_component" / %}
    {% endwith %}
    ```

You can use these to check whether the component was rendered inside a template with [`{% component %}`](../../../reference/template_tags#component) tag
or in Python with [`Component.render()`](../../../reference/api/#django_components.Component.render).

```python
class MyComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        if self.registered_name is None:
            # Do something for the render() function
        else:
            # Do something for the {% component %} template tag
```

You can access the [`ComponentNode`](../../../reference/api/#django_components.ComponentNode) under [`Component.node`](../../../reference/api/#django_components.Component.node):

```py
class MyComponent(Component):
    def get_template_data(self, context, template):
        if self.node is not None:
            assert self.node.name == "my_component"
```

Accessing the [`ComponentNode`](../../../reference/api/#django_components.ComponentNode) is mostly useful for extensions, which can modify their behaviour based on the source of the Component.

For example, if `MyComponent` was used in another component - that is,
with a `{% component "my_component" %}` tag
in a template that belongs to another component - then you can use
[`self.node.template_component`](../../../reference/api/#django_components.ComponentNode.template_component)
to access the owner [`Component`](../../../reference/api/#django_components.Component) class.

```djc_py
class Parent(Component):
    template: types.django_html = """
        <div>
            {% component "my_component" / %}
        </div>
    """

@register("my_component")
class MyComponent(Component):
    def get_template_data(self, context, template):
        if self.node is not None:
            assert self.node.template_component == Parent
```

!!! info

    `Component.node` is `None` if the component is created by [`Component.render()`](../../../reference/api/#django_components.Component.render)
    (but you can pass in the `node` kwarg yourself).
