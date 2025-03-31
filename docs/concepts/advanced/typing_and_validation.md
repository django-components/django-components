## Adding type hints with Generics

_New in version 0.92_

The [`Component`](../../../reference/api#django_components.Component) class optionally accepts type parameters
that allow you to specify the types of args, kwargs, slots, and data.

Use this to add type hints to your components, or to validate component inputs and outputs.

```py
from django_components import Component

ButtonType = Component[Args, Kwargs, Slots, Data, JsData, CssData]

class Button(ButtonType):
    template_file = "button.html"

    def get_context_data(self, *args, **kwargs):
        ...
```

The generic parameters are:

- `Args` - Positional arguments, must be a `Tuple` or `Any`
- `Kwargs` - Keyword arguments, must be a `TypedDict` or `Any`
- `Slots` - Slots, must be a `TypedDict` or `Any`
- `Data` - Data returned from [`get_context_data()`](../../../reference/api#django_components.Component.get_context_data), must be a `TypedDict` or `Any`
- `JsData` - Data returned from [`get_js_data()`](../../../reference/api#django_components.Component.get_js_data), must be a `TypedDict` or `Any`
- `CssData` - Data returned from [`get_css_data()`](../../../reference/api#django_components.Component.get_css_data), must be a `TypedDict` or `Any`

## Example

```python
from typing import NotRequired, Tuple, TypedDict
from pydantic import BaseModel
from django_components import Component, SlotContent, SlotFunc

###########################################
# 1. Define the types
###########################################

# Positional inputs
ButtonArgs = Tuple[str, ...]

# Keyword inputs
class ButtonKwargs(TypedDict):
    name: str
    age: int
    maybe_var: NotRequired[int] # May be ommited

# The data available to the `my_slot` scoped slot
class ButtonFooterSlotData(TypedDict):
    value: int

# Slots
class ButtonSlots(TypedDict):
    # SlotContent == str or slot func
    header: SlotContent
    # Use SlotFunc for slot functions.
    # The generic specifies the data available to the slot function
    footer: NotRequired[SlotFunc[ButtonFooterSlotData]]

# Data returned from `get_context_data`
class ButtonData(BaseModel):
    data1: str
    data2: int

# Data returned from `get_js_data`
class ButtonJsData(BaseModel):
    js_data1: str
    js_data2: int

# Data returned from `get_css_data`
class ButtonCssData(BaseModel):
    css_data1: str
    css_data2: int

###########################################
# 2. Define the component with those types
###########################################

ButtonType = Component[
    ButtonArgs,
    ButtonKwargs,
    ButtonSlots,
    ButtonData,
    ButtonJsData,
    ButtonCssData,
]

class Button(ButtonType):
    def get_context_data(self, *args, **kwargs):
        ...
```

When you then call
[`Component.render`](../../../reference/api#django_components.Component.render)
or [`Component.render_to_response`](../../../reference/api#django_components.Component.render_to_response),
you will get type hints:

```python
Button.render(
    # ERROR: Expects a string
    args=(123,),
    kwargs={
        "name": "John",
        # ERROR: Expects an integer
        "age": "invalid",
    },
    slots={
        "header": "...",
        # ERROR: Expects key "footer"
        "foo": "invalid",
    },
)
```

If you don't want to validate some parts, set them to [`Any`](https://docs.python.org/3/library/typing.html#typing.Any).

```python
ButtonType = Component[
    ButtonArgs,
    ButtonKwargs,
    ButtonSlots,
    Any,
    Any,
    Any,
]

class Button(ButtonType):
    ...
```

## Passing variadic args and kwargs

You may have a function that accepts a variable number of args or kwargs:

```py
def get_context_data(self, *args, **kwargs):
    ...
```

This is not supported with the typed components.

As a workaround:

- For a variable number of positional arguments (`*args`), set a positional argument that accepts a list of values:

    ```py
    # Tuple of one member of list of strings
    Args = Tuple[List[str]]
    ```

- For a variable number of keyword arguments (`**kwargs`), set a keyword argument that accepts a dictionary of values:

    ```py
    class Kwargs(TypedDict):
        variable: str
        another: int
        # Pass any extra keys under `extra`
        extra: Dict[str, any]
    ```

## Handling no args or no kwargs

To declare that a component accepts no args, kwargs, etc, you can use the
[`EmptyTuple`](../../../reference/api#django_components.EmptyTuple) and
[`EmptyDict`](../../../reference/api#django_components.EmptyDict) types:

```py
from django_components import Component, EmptyDict, EmptyTuple

class Button(Component[EmptyTuple, EmptyDict, EmptyDict, EmptyDict, EmptyDict, EmptyDict]):
    ...
```

## Runtime input validation with types

!!! warning

    Input validation was part of Django Components from version 0.96 to 0.135.

    Since v0.136, input validation is available as a separate extension.

To enable input validation, you need to install the [`djc-ext-pydantic`](https://github.com/django-components/djc-ext-pydantic) extension:

```bash
pip install djc-ext-pydantic
```

And add the extension to your project:

```py
COMPONENTS = {
    "extensions": [
        "djc_ext_pydantic.PydanticExtension",
    ],
}
```

`djc-ext-pydantic` integrates [Pydantic](https://pydantic.dev/) for input and data validation. It uses the types defined on the component's class to validate both inputs and outputs of Django components.

## Usage for Python <3.11

On Python 3.8-3.10, use `typing_extensions`

```py
from typing_extensions import TypedDict, NotRequired
```

Additionally on Python 3.8-3.9, also import `annotations`:

```py
from __future__ import annotations
```

Moreover, on 3.10 and less, you may not be able to use `NotRequired`, and instead you will need to mark either all keys are required, or all keys as optional, using TypeDict's `total` kwarg.

[See PEP-655](https://peps.python.org/pep-0655) for more info.
