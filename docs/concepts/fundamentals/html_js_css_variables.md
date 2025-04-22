When a component recieves input through [`{% component %}`](../../../reference/template_tags/#component) tag,
or the [`Component.render()`](../../../reference/api/#django_components.Component.render) or [`Component.render_to_response()`](../../../reference/api/#django_components.Component.render_to_response) methods, you can define how the input is handled, and what variables will be available to the template, JavaScript and CSS.

## Overview

Django Components offers three key methods for passing variables to different parts of your component:

- [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) - Provides variables to your HTML template
- [`get_js_data()`](../../../reference/api/#django_components.Component.get_js_data) - Provides variables to your JavaScript code
- [`get_css_data()`](../../../reference/api/#django_components.Component.get_css_data) - Provides variables to your CSS styles

These methods let you pre-process inputs before they're used in rendering.

Each method handles the data independently - you can define different data for the template, JS, and CSS.

```python
class ProfileCard(Component):
    class Kwargs(NamedTuple):
        user_id: int
        show_details: bool

    class Defaults:
        show_details = True

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

The [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) method is the primary way to provide variables to your HTML template. It receives the component inputs and returns a dictionary of data that will be available in the template.

If [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) returns `None`, an empty dictionary will be used.

```python
class ProfileCard(Component):
    template_file = "profile_card.html"

    class Kwargs(NamedTuple):
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

The [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data) method is the legacy way to provide variables to your HTML template. It serves the same purpose as [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) - it receives the component inputs and returns a dictionary of data that will be available in the template.

However, [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data) has a few drawbacks:

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

!!! warning

    [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data)
    and [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data)
    are mutually exclusive.

    If both methods return non-empty dictionaries, an error will be raised.

!!! note

    The `get_context_data()` method will be removed in v2.

## Accessing component inputs

The component inputs are available in two ways:

1. **Function arguments (recommended)**

    The data methods receive the inputs as parameters, which you can access directly.

    ```python
    class ProfileCard(Component):
        def get_template_data(self, args, kwargs, slots, context):
            # Access inputs directly as parameters
            return {
                "user_id": user_id,
                "show_details": show_details,
            }
    ```

    !!! info

        By default, the `args` parameter is a list, while `kwargs` and `slots` are dictionaries.

        If you add typing to your component with
        [`Args`](../../../reference/api/#django_components.Component.Args),
        [`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
        or [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
        the respective inputs will be given as instances of these classes.

        Learn more about [Component typing](../../advanced/typing_and_validation).

2. **`self.input` property**

    The data methods receive only the main inputs. There are additional settings that may be passed
    to components. If you need to access these, you can do so via the [`self.input`](../../../reference/api/#django_components.Component.input) property.

    The `input` property contains all the inputs passed to the component (instance of [`ComponentInput`](../../../reference/api/#django_components.ComponentInput)).

    This includes:

    - [`input.args`](../../../reference/api/#django_components.ComponentInput.args) - List of positional arguments
    - [`input.kwargs`](../../../reference/api/#django_components.ComponentInput.kwargs) - Dictionary of keyword arguments
    - [`input.slots`](../../../reference/api/#django_components.ComponentInput.slots) - Dictionary of slots. Values are normalized to [`Slot`](../../../reference/api/#django_components.Slot) instances
    - [`input.context`](../../../reference/api/#django_components.ComponentInput.context) - [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context) object that should be used to render the component
    - [`input.type`](../../../reference/api/#django_components.ComponentInput.type) - The type of the component (document, fragment)
    - [`input.render_dependencies`](../../../reference/api/#django_components.ComponentInput.render_dependencies) - Whether to render dependencies (CSS, JS)

    For more details, see [Component inputs](../render_api/#component-inputs).

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
        regardless of whether you added typing to your component.

## Default values

You can use [`Defaults`](../../../reference/api/#django_components.Component.Defaults) class to provide default values for your inputs.

These defaults will be applied either when:

- The input is not provided at rendering time
- The input is provided as `None`

When you then access the inputs in your data methods, the default values will be already applied.

Read more about [Component Defaults](./component_defaults.md).

```py
from django_components import Component, Default, register

@register("profile_card")
class ProfileCard(Component):
    class Kwargs(NamedTuple):
        show_details: bool

    class Defaults:
        show_details = True

    # show_details will be set to True if `None` or missing
    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "show_details": kwargs.show_details,
        }

    ...
```

!!! warning

    When typing your components with [`Args`](../../../reference/api/#django_components.Component.Args),
    [`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
    or [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
    you may be inclined to define the defaults in the classes.

    ```py
    class ProfileCard(Component):
        class Kwargs(NamedTuple):
            show_details: bool = True
    ```

    This is **NOT recommended**, because:

    - The defaults will NOT be applied to inputs when using [`self.input`](../../../reference/api/#django_components.Component.input) property.
    - The defaults will NOT be applied when a field is given but set to `None`.

    Instead, define the defaults in the [`Defaults`](../../../reference/api/#django_components.Component.Defaults) class.

## Accessing Render API

All three data methods have access to the Component's [Render API](./render_api.md), which includes:

- [`self.id`](./render_api/#component-id) - The unique ID for the current render call
- [`self.input`](./render_api/#component-inputs) - All the component inputs
- [`self.request`](./render_api/#request-object-and-context-processors) - The request object (if available)
- [`self.context_processors_data`](./render_api/#request-object-and-context-processors) - Data from Django's context processors (if request is available)
- [`self.inject()`](./render_api/#provide-inject) - Inject data into the component

## Type hints

### Typing inputs

You can add type hints for the component inputs to ensure that the component logic is correct.

For this, define the [`Args`](../../../reference/api/#django_components.Component.Args),
[`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
and [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
and then add type hints to the data methods.

This will also validate the inputs at runtime, as the type classes will be instantiated with the inputs.

Read more about [Component typing](../../advanced/typing_and_validation).

```python
from typing import NamedTuple, Optional
from django_components import Component, SlotInput

class Button(Component):
    class Args(NamedTuple):
        name: str

    class Kwargs(NamedTuple):
        surname: str
        maybe_var: Optional[int] = None  # May be omitted

    class Slots(NamedTuple):
        my_slot: Optional[SlotInput] = None
        footer: SlotInput

    # Use the above classes to add type hints to the data method
    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        # The parameters are instances of the classes we defined
        assert isinstance(args, Button.Args)
        assert isinstance(kwargs, Button.Kwargs)
        assert isinstance(slots, Button.Slots)
```

!!! note

    The data available via [`self.input`](../../../reference/api/#django_components.Component.input) property is NOT typed.

### Typing data

In the same fashion, you can add types and validation for the data that should be RETURNED from each data method.

For this, set the [`TemplateData`](../../../reference/api/#django_components.Component.TemplateData),
[`JsData`](../../../reference/api/#django_components.Component.JsData),
and [`CssData`](../../../reference/api/#django_components.Component.CssData) classes on the component class.

For each data method, you can either return a plain dictionary with the data, or an instance of the respective data class.

```python
from typing import NamedTuple
from django_components import Component

class Button(Component):
    class TemplateData(NamedTuple):
        data1: str
        data2: int

    class JsData(NamedTuple):
        js_data1: str
        js_data2: int

    class CssData(NamedTuple):
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

To do that, simply return the `kwargs` dictionary itself from [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data):

```py
class MyComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return kwargs
```

You can do the same for [`get_js_data()`](../../../reference/api/#django_components.Component.get_js_data) and [`get_css_data()`](../../../reference/api/#django_components.Component.get_css_data), if needed:

```py
class MyComponent(Component):
    def get_js_data(self, args, kwargs, slots, context):
        return kwargs

    def get_css_data(self, args, kwargs, slots, context):
        return kwargs
```
