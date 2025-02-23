## Adding type hints with Generics

_New in version 0.92_

The `Component` class optionally accepts type parameters
that allow you to specify the types of args, kwargs, slots, and
data:

```py
class Button(Component[Args, Kwargs, Slots, Data, JsData, CssData]):
    ...
```

- `Args` - Must be a `Tuple` or `Any`
- `Kwargs` - Must be a `TypedDict` or `Any`
- `Data` - Must be a `TypedDict` or `Any`
- `Slots` - Must be a `TypedDict` or `Any`

Here's a full example:

```py
from typing import NotRequired, Tuple, TypedDict, SlotContent, SlotFunc

# Positional inputs
Args = Tuple[int, str]

# Kwargs inputs
class Kwargs(TypedDict):
    variable: str
    another: int
    maybe_var: NotRequired[int] # May be ommited

# Data returned from `get_context_data`
class Data(TypedDict):
    variable: str

# The data available to the `my_slot` scoped slot
class MySlotData(TypedDict):
    value: int

# Slots
class Slots(TypedDict):
    # Use SlotFunc for slot functions.
    # The generic specifies the `data` dictionary
    my_slot: NotRequired[SlotFunc[MySlotData]]
    # SlotContent == Union[str, SafeString]
    another_slot: SlotContent

class Button(Component[Args, Kwargs, Slots, Data, JsData, CssData]):
    def get_context_data(self, variable, another):
        return {
            "variable": variable,
        }
```

When you then call `Component.render` or `Component.render_to_response`, you will get type hints:

```py
Button.render(
    # Error: First arg must be `int`, got `float`
    args=(1.25, "abc"),
    # Error: Key "another" is missing
    kwargs={
        "variable": "text",
    },
)
```

### Usage for Python <3.11

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

## Passing additional args or kwargs

You may have a function that supports any number of args or kwargs:

```py
def get_context_data(self, *args, **kwargs):
    ...
```

This is not supported with the typed components.

As a workaround:

- For `*args`, set a positional argument that accepts a list of values:

  ```py
  # Tuple of one member of list of strings
  Args = Tuple[List[str]]
  ```

- For `*kwargs`, set a keyword argument that accepts a dictionary of values:

  ```py
  class Kwargs(TypedDict):
      variable: str
      another: int
      # Pass any extra keys under `extra`
      extra: Dict[str, any]
  ```

## Handling no args or no kwargs

To declare that a component accepts no Args, Kwargs, etc, you can use `EmptyTuple` and `EmptyDict` types:

```py
from django_components import Component, EmptyDict, EmptyTuple

Args = EmptyTuple
Kwargs = Data = Slots = EmptyDict

class Button(Component[Args, Kwargs, Slots, Data, JsData, CssData]):
    ...
```

## Runtime input validation with types

_New in version 0.96_

> NOTE: Kwargs, slots, and data validation is supported only for Python >=3.11

In Python 3.11 and later, when you specify the component types, you will get also runtime validation of the inputs you pass to `Component.render` or `Component.render_to_response`.

So, using the example from before, if you ignored the type errors and still ran the following code:

```py
Button.render(
    # Error: First arg must be `int`, got `float`
    args=(1.25, "abc"),
    # Error: Key "another" is missing
    kwargs={
        "variable": "text",
    },
)
```

This would raise a `TypeError`:

```txt
Component 'Button' expected positional argument at index 0 to be <class 'int'>, got 1.25 of type <class 'float'>
```

In case you need to skip these errors, you can either set the faulty member to `Any`, e.g.:

```py
# Changed `int` to `Any`
Args = Tuple[Any, str]
```

Or you can replace `Args` with `Any` altogether, to skip the validation of args:

```py
# Replaced `Args` with `Any`
class Button(Component[Any, Kwargs, Slots, Data, JsData, CssData]):
    ...
```

Same applies to kwargs, data, and slots.
