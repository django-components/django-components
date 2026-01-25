When a component recieves input through [`{% component %}`](../../reference/template_tags.md#component) tag,
or the [`Component.render()`](../../reference/api.md#django_components.Component.render) or [`Component.render_to_response()`](../../reference/api.md#django_components.Component.render_to_response) methods, you can define how the input is handled, and what variables will be available to the template, JavaScript and CSS.

## Overview

Django Components offers three key methods for passing variables to different parts of your component:

- [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data) - Provides variables to your HTML template
- [`get_js_data()`](../../reference/api.md#django_components.Component.get_js_data) - Provides variables to your JavaScript code
- [`get_css_data()`](../../reference/api.md#django_components.Component.get_css_data) - Provides variables to your CSS styles

These methods let you pre-process inputs before they're used in rendering.

Each method handles the data independently - you can define different data for the template, JS, and CSS.

```python
class ProfileCard(Component):
    class Kwargs:
        user_id: int
        show_details: bool = True

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        user = User.objects.get(id=kwargs.user_id)
        return {
            "user": user,
            "show_details": kwargs.show_details,
        }

    def get_js_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "user_id": kwargs.user_id,
        }

    def get_css_data(self, args, kwargs: Kwargs, slots, context):
        text_color = "red" if kwargs.show_details else "blue"
        return {
            "text_color": text_color,
        }
```

## Template variables

The [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data) method is the primary way to provide variables to your HTML template. It receives the component inputs and returns a dictionary of data that will be available in the template.

If [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data) returns `None`, an empty dictionary will be used.

```python
class ProfileCard(Component):
    template_file = "profile_card.html"

    class Kwargs:
        user_id: int
        show_details: bool

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        user = User.objects.get(id=kwargs.user_id)

        # Process and transform inputs
        return {
            "user": user,
            "show_details": kwargs.show_details,
            "user_joined_days": (timezone.now() - user.date_joined).days,
        }
```

In your template, you can then use these variables:

```django
<div class="profile-card">
    <h2>{{ user.username }}</h2>

    {% if show_details %}
        <p>Member for {{ user_joined_days }} days</p>
        <p>Email: {{ user.email }}</p>
    {% endif %}
</div>
```

### Legacy `get_context_data()`

The [`get_context_data()`](../../reference/api.md#django_components.Component.get_context_data) method is the legacy way to provide variables to your HTML template. It serves the same purpose as [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data) - it receives the component inputs and returns a dictionary of data that will be available in the template.

However, [`get_context_data()`](../../reference/api.md#django_components.Component.get_context_data) has a few drawbacks:

- It does NOT receive the `slots` and `context` parameters.
- The `args` and `kwargs` parameters are given as variadic `*args` and `**kwargs` parameters. As such, they cannot be typed.

```python
class ProfileCard(Component):
    template_file = "profile_card.html"

    def get_context_data(self, user_id, show_details=False, *args, **kwargs):
        user = User.objects.get(id=user_id)
        return {
            "user": user,
            "show_details": show_details,
        }
```

There is a slight difference between [`get_context_data()`](../../reference/api.md#django_components.Component.get_context_data) and [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data)
when rendering a component with the [`{% component %}`](../../reference/template_tags.md#component) tag.

For example if you have component that accepts kwarg `date`:

```py
class MyComponent(Component):
    def get_context_data(self, date, *args, **kwargs):
        return {
            "date": date,
        }

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs["date"],
        }
```

The difference is that:

- With [`get_context_data()`](../../reference/api.md#django_components.Component.get_context_data), you can pass `date` either as arg or kwarg:

    ```django
    ✅
    {% component "my_component" date=some_date %}
    {% component "my_component" some_date %}
    ```

- But with [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data), `date` MUST be passed as kwarg:

    ```django
    ✅
    {% component "my_component" date=some_date %}

    ❌
    {% component "my_component" some_date %}
    ```

!!! warning

    [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data)
    and [`get_context_data()`](../../reference/api.md#django_components.Component.get_context_data)
    are mutually exclusive.

    If both methods return non-empty dictionaries, an error will be raised.

!!! note

    The `get_context_data()` method will be removed in v2.

## Accessing component inputs

The component inputs are available in 3 ways:

### Function arguments

The data methods receive the inputs as parameters directly.

```python
class ProfileCard(Component):
    # Access inputs directly as parameters
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "user_id": args[0],
            "show_details": kwargs["show_details"],
        }
```

!!! info

    By default, the `args` parameter is a list, while `kwargs` and `slots` are dictionaries.

    If you add typing to your component with
    [`Args`](../../reference/api.md#django_components.Component.Args),
    [`Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
    or [`Slots`](../../reference/api.md#django_components.Component.Slots) classes,
    the respective inputs will be given as instances of these classes.

    Learn more about [Component typing](typing_and_validation.md).

    ```py
    class ProfileCard(Component):
        class Args:
            user_id: int

        class Kwargs:
            show_details: bool

        # Access inputs directly as parameters
        def get_template_data(self, args: Args, kwargs: Kwargs, slots, context):
            return {
                "user_id": args.user_id,
                "show_details": kwargs.show_details,
            }
    ```

### `args`, `kwargs`, `slots` properties

In other methods, you can access the inputs via
[`self.args`](../../reference/api.md#django_components.Component.args),
[`self.kwargs`](../../reference/api.md#django_components.Component.kwargs),
and [`self.slots`](../../reference/api.md#django_components.Component.slots) properties:

```py
class ProfileCard(Component):
    def on_render_before(self, context: Context, template: Template | None):
        # Access inputs via self.args, self.kwargs, self.slots
        self.args[0]
        self.kwargs.get("show_details", False)
        self.slots["footer"]
```

!!! info

    These properties work the same way as `args`, `kwargs`, and `slots` parameters in the data methods:

    By default, the `args` property is a list, while `kwargs` and `slots` are dictionaries.

    If you add typing to your component with
    [`Args`](../../reference/api.md#django_components.Component.Args),
    [`Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
    or [`Slots`](../../reference/api.md#django_components.Component.Slots) classes,
    the respective inputs will be given as instances of these classes.

    Learn more about [Component typing](typing_and_validation.md).

    ```py
    class ProfileCard(Component):
        class Args:
            user_id: int

        class Kwargs:
            show_details: bool

        def get_template_data(self, args: Args, kwargs: Kwargs, slots, context):
            return {
                "user_id": self.args.user_id,
                "show_details": self.kwargs.show_details,
            }
    ```

<!-- TODO_v1 - Remove -->

### `input` property (low-level)

!!! warning

    The `input` property is deprecated and will be removed in v1.

    Instead, use properties defined on the
    [`Component`](../../reference/api.md#django_components.Component) class
    directly like
    [`self.context`](../../reference/api.md#django_components.Component.context).

    To access the unmodified inputs, use
    [`self.raw_args`](../../reference/api.md#django_components.Component.raw_args),
    [`self.raw_kwargs`](../../reference/api.md#django_components.Component.raw_kwargs),
    and [`self.raw_slots`](../../reference/api.md#django_components.Component.raw_slots) properties.

The previous two approaches allow you to access only the most important inputs.

There are additional settings that may be passed to components.
If you need to access these, you can use [`self.input`](../../reference/api.md#django_components.Component.input) property
for a low-level access to all the inputs.

The `input` property contains all the inputs passed to the component (instance of [`ComponentInput`](../../reference/api.md#django_components.ComponentInput)).

This includes:

- [`input.args`](../../reference/api.md#django_components.ComponentInput.args) - List of positional arguments
- [`input.kwargs`](../../reference/api.md#django_components.ComponentInput.kwargs) - Dictionary of keyword arguments
- [`input.slots`](../../reference/api.md#django_components.ComponentInput.slots) - Dictionary of slots. Values are normalized to [`Slot`](../../reference/api.md#django_components.Slot) instances
- [`input.context`](../../reference/api.md#django_components.ComponentInput.context) - [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context) object that should be used to render the component
- [`input.type`](../../reference/api.md#django_components.ComponentInput.type) - The type of the component (document, fragment)
- [`input.render_dependencies`](../../reference/api.md#django_components.ComponentInput.render_dependencies) - Whether to render dependencies (CSS, JS)

```python
class ProfileCard(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # Access positional arguments
        user_id = self.input.args[0] if self.input.args else None

        # Access keyword arguments
        show_details = self.input.kwargs.get("show_details", False)

        # Render component differently depending on the type
        if self.input.type == "fragment":
            ...

        return {
            "user_id": user_id,
            "show_details": show_details,
        }
```

!!! info

    Unlike the parameters passed to the data methods, the `args`, `kwargs`, and `slots` in `self.input` property are always lists and dictionaries,
    regardless of whether you added typing classes to your component (like [`Args`](../../reference/api.md#django_components.Component.Args),
    [`Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
    or [`Slots`](../../reference/api.md#django_components.Component.Slots)).

## Default values

You can use the [`Defaults`](../../reference/api.md#django_components.Component.Defaults) and [`Kwargs`](../../reference/api.md#django_components.Component.Kwargs) classes to provide default values for your inputs.

These defaults will be applied either when:

- The input is not provided at rendering time
- The input is provided as `None`

When you then access the inputs in your data methods, the default values will be already applied.

Read more about [Component Defaults](./component_defaults.md).

```py
from django_components import Component, Default, register

@register("profile_card")
class ProfileCard(Component):
    class Kwargs:
        # Will be set to True if `None` or missing
        show_details: bool = True

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "show_details": kwargs.show_details,
        }

    ...
```

## Accessing Render API

All three data methods have access to the Component's [Render API](render_api.md), which includes:

- [`self.args`](render_api.md#args) - The positional arguments for the current render call
- [`self.kwargs`](render_api.md#kwargs) - The keyword arguments for the current render call
- [`self.slots`](render_api.md#slots) - The slots for the current render call
- [`self.raw_args`](render_api.md#args) - Unmodified positional arguments for the current render call
- [`self.raw_kwargs`](render_api.md#kwargs) - Unmodified keyword arguments for the current render call
- [`self.raw_slots`](render_api.md#slots) - Unmodified slots for the current render call
- [`self.context`](render_api.md#context) - The context for the current render call
- [`self.id`](render_api.md#component-id) - The unique ID for the current render call
- [`self.request`](render_api.md#request-and-context-processors) - The request object
- [`self.context_processors_data`](render_api.md#request-and-context-processors) - Data from Django's context processors
- [`self.inject()`](render_api.md#provide-inject) - Inject data into the component
- [`self.registry`](render_api.md#template-tag-metadata) - The [`ComponentRegistry`](../../reference/api.md#django_components.ComponentRegistry) instance
- [`self.registered_name`](render_api.md#template-tag-metadata) - The name under which the component was registered
- [`self.outer_context`](render_api.md#template-tag-metadata) - The context outside of the [`{% component %}`](../../reference/template_tags.md#component) tag
- [`self.parent`](render_api.md#parent) - The parent component instance (or `None` if root)
- [`self.root`](render_api.md#root) - The root component instance (or `self` if root)
- [`self.ancestors`](render_api.md#ancestors) - An iterator of all ancestor component instances
- `self.deps_strategy` - The strategy for rendering dependencies

## Type hints

### Typing inputs

You can add type hints for the component inputs to ensure that the component logic is correct.

For this, define the [`Args`](../../reference/api.md#django_components.Component.Args),
[`Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
and [`Slots`](../../reference/api.md#django_components.Component.Slots) classes,
and then add type hints to the data methods.

This will also validate the inputs at runtime, as the type classes will be instantiated with the inputs.

Read more about [Component typing](typing_and_validation.md).

```python
from django_components import Component, SlotInput

class Button(Component):
    class Args:
        name: str

    class Kwargs:
        surname: str
        maybe_var: int | None = None  # May be omitted

    class Slots:
        my_slot: SlotInput | None = None
        footer: SlotInput

    # Use the above classes to add type hints to the data method
    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        # The parameters are instances of the classes we defined
        assert isinstance(args, Button.Args)
        assert isinstance(kwargs, Button.Kwargs)
        assert isinstance(slots, Button.Slots)
```

!!! note

    To access "untyped" inputs, use [`self.raw_args`](../../reference/api.md#django_components.Component.raw_args),
    [`self.raw_kwargs`](../../reference/api.md#django_components.Component.raw_kwargs),
    and [`self.raw_slots`](../../reference/api.md#django_components.Component.raw_slots) properties.

    These are plain lists and dictionaries, even when you added typing to your component.

### Typing data

In the same fashion, you can add types and validation for the data that should be RETURNED from each data method.

For this, set the [`TemplateData`](../../reference/api.md#django_components.Component.TemplateData),
[`JsData`](../../reference/api.md#django_components.Component.JsData),
and [`CssData`](../../reference/api.md#django_components.Component.CssData) classes on the component class.

For each data method, you can either return a plain dictionary with the data, or an instance of the respective data class.

```python
from django_components import Component

class Button(Component):
    class TemplateData(
        data1: str
        data2: int

    class JsData:
        js_data1: str
        js_data2: int

    class CssData:
        css_data1: str
        css_data2: int

    def get_template_data(self, args, kwargs, slots, context):
        return Button.TemplateData(
            data1="...",
            data2=123,
        )

    def get_js_data(self, args, kwargs, slots, context):
        return Button.JsData(
            js_data1="...",
            js_data2=123,
        )

    def get_css_data(self, args, kwargs, slots, context):
        return Button.CssData(
            css_data1="...",
            css_data2=123,
        )
```

## Pass-through kwargs

It's best practice to explicitly define what args and kwargs a component accepts.

However, if you want a looser setup, you can easily write components that accept any number
of kwargs, and pass them all to the template
(similar to [django-cotton](https://github.com/wrabit/django-cotton)).

To do that, simply return the `kwargs` dictionary itself from [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data):

```py
class MyComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return kwargs
```

You can do the same for [`get_js_data()`](../../reference/api.md#django_components.Component.get_js_data) and [`get_css_data()`](../../reference/api.md#django_components.Component.get_css_data), if needed:

```py
class MyComponent(Component):
    def get_js_data(self, args, kwargs, slots, context):
        return kwargs

    def get_css_data(self, args, kwargs, slots, context):
        return kwargs
```
