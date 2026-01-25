## Typing overview

<!-- TODO_V1 - REMOVE IN v1 -->

!!! warning

    In versions 0.92 to 0.139 (inclusive), the component typing was specified through generics.

    Since v0.140, the types must be specified as class attributes of the Component class - `Args`, `Kwargs`, `Slots`, `TemplateData`, `JsData`, and `CssData`.

    See [Migrating from generics to class attributes](#migrating-from-generics-to-class-attributes) for more info.

!!! warning

    Input validation was NOT part of Django Components between versions 0.136 and 0.139 (inclusive).

The [`Component`](../../reference/api.md#django_components.Component) class optionally accepts class attributes
that allow you to define the types of args, kwargs, slots, as well as the data returned from the data methods.

Use this to add type hints to your components, to validate the inputs at runtime, and to document them.

```py
from django.template import Context
from django_components import Component, SlotInput

class Button(Component):
    class Args:
        size: int
        text: str

    class Kwargs:
        variable: str
        maybe_var: int | None = None  # May be omitted

    class Slots:
        my_slot: SlotInput | None = None

    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        ...

    template_file = "button.html"
```

The class attributes are:

- [`Args`](../../reference/api.md#django_components.Component.Args) - Type for positional arguments.
- [`Kwargs`](../../reference/api.md#django_components.Component.Kwargs) - Type for keyword arguments.
- [`Slots`](../../reference/api.md#django_components.Component.Slots) - Type for slots.
- [`TemplateData`](../../reference/api.md#django_components.Component.TemplateData) - Type for data returned from [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data).
- [`JsData`](../../reference/api.md#django_components.Component.JsData) - Type for data returned from [`get_js_data()`](../../reference/api.md#django_components.Component.get_js_data).
- [`CssData`](../../reference/api.md#django_components.Component.CssData) - Type for data returned from [`get_css_data()`](../../reference/api.md#django_components.Component.get_css_data).

You can specify as many or as few of these as you want, the rest will default to `None`.

## Typing inputs

You can use [`Component.Args`](../../reference/api.md#django_components.Component.Args),
[`Component.Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
and [`Component.Slots`](../../reference/api.md#django_components.Component.Slots) to type the component inputs.

When you set these input classes, the `args`, `kwargs`, and `slots` parameters of the data methods
([`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data),
[`get_js_data()`](../../reference/api.md#django_components.Component.get_js_data),
[`get_css_data()`](../../reference/api.md#django_components.Component.get_css_data))
will be instances of these classes.

This way, each component can have runtime validation of the inputs:

- When you use [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
  or [`@dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass),
  instantiating these classes will check ONLY for the presence of the attributes.
- When you use [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/),
  instantiating these classes will check for the presence AND type of the attributes.

If you omit the [`Args`](../../reference/api.md#django_components.Component.Args),
[`Kwargs`](../../reference/api.md#django_components.Component.Kwargs), or
[`Slots`](../../reference/api.md#django_components.Component.Slots) classes,
or set them to `None`, the inputs will be passed as plain lists or dictionaries,
and will not be validated.

```python
from typing_extensions import TypedDict
from django.template import Context
from django_components import Component, Slot, SlotInput

# The data available to the `footer` scoped slot
class ButtonFooterSlotData(TypedDict):
    value: int

# Define the component with the types
class Button(Component):
    class Args:
        name: str

    class Kwargs:
        surname: str
        age: int
        maybe_var: int | None = None  # May be omitted

    class Slots:
        # Use `SlotInput` to allow slots to be given as `Slot` instance,
        # plain string, or a function that returns a string.
        my_slot: SlotInput | None = None
        # Use `Slot` to allow ONLY `Slot` instances.
        # The generic is optional, and it specifies the data available
        # to the slot function.
        footer: Slot[ButtonFooterSlotData]

    # Add type hints to the data method
    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        # The parameters are instances of the classes we defined
        assert isinstance(args, Button.Args)
        assert isinstance(kwargs, Button.Kwargs)
        assert isinstance(slots, Button.Slots)

        args.name  # str
        kwargs.age  # int
        slots.footer  # Slot[ButtonFooterSlotData]

# Add type hints to the render call
Button.render(
    args=Button.Args(
        name="John",
    ),
    kwargs=Button.Kwargs(
        surname="Doe",
        age=30,
    ),
    slots=Button.Slots(
        footer=Slot(lambda ctx: "Click me!"),
    ),
)
```

If you don't want to validate some parts, set them to `None` or omit them.

The following will validate only the keyword inputs:

```python
class Button(Component):
    # We could also omit these
    Args = None
    Slots = None

    class Kwargs:
        name: str
        age: int

    # Only `kwargs` is instantiated. `args` and `slots` are not.
    def get_template_data(self, args, kwargs: Kwargs, slots, context: Context):
        assert isinstance(args, list)
        assert isinstance(slots, dict)
        assert isinstance(kwargs, Button.Kwargs)

        args[0]  # str
        slots["footer"]  # Slot[ButtonFooterSlotData]
        kwargs.age  # int
```

!!! info

    Components can receive slots as strings, functions, or instances of [`Slot`](../../reference/api.md#django_components.Slot).

    Internally these are all normalized to instances of [`Slot`](../../reference/api.md#django_components.Slot).

    Therefore, the `slots` dictionary available in data methods (like
    [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data))
    will always be a dictionary of [`Slot`](../../reference/api.md#django_components.Slot) instances.

    To correctly type this dictionary, you should set the fields of `Slots` to
    [`Slot`](../../reference/api.md#django_components.Slot) or [`SlotInput`](../../reference/api.md#django_components.SlotInput):

    [`SlotInput`](../../reference/api.md#django_components.SlotInput) is a union of `Slot`, string, and function types.

## Typing data

You can use [`Component.TemplateData`](../../reference/api.md#django_components.Component.TemplateData),
[`Component.JsData`](../../reference/api.md#django_components.Component.JsData),
and [`Component.CssData`](../../reference/api.md#django_components.Component.CssData) to type the data returned from [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data), [`get_js_data()`](../../reference/api.md#django_components.Component.get_js_data), and [`get_css_data()`](../../reference/api.md#django_components.Component.get_css_data).

When you set these classes, at render time they will be instantiated with the data returned from these methods.

This way, each component can have runtime validation of the returned data:

- When you use [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
  or [`@dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass),
  instantiating these classes will check ONLY for the presence of the attributes.
- When you use [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/),
  instantiating these classes will check for the presence AND type of the attributes.

If you omit the [`TemplateData`](../../reference/api.md#django_components.Component.TemplateData),
[`JsData`](../../reference/api.md#django_components.Component.JsData), or
[`CssData`](../../reference/api.md#django_components.Component.CssData) classes,
or set them to `None`, the validation and instantiation will be skipped.

```python
from django_components import Component

class Button(Component):
    class TemplateData:
        data1: str
        data2: int

    class JsData:
        js_data1: str
        js_data2: int

    class CssData:
        css_data1: str
        css_data2: int

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "data1": "...",
            "data2": 123,
        }

    def get_js_data(self, args, kwargs, slots, context):
        return {
            "js_data1": "...",
            "js_data2": 123,
        }

    def get_css_data(self, args, kwargs, slots, context):
        return {
            "css_data1": "...",
            "css_data2": 123,
        }
```

For each data method, you can either return a plain dictionary with the data, or an instance of the respective data class directly.

```python
from django_components import Component

class Button(Component):
    class TemplateData:
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

## Custom types

So far, we've defined the input classes like `Kwargs` as simple classes.

The truth is that when these classes don't subclass anything else,
they are converted to `NamedTuples` behind the scenes.

```py
class Table(Component):
    class Kwargs:
        name: str
        age: int
```

is the same as:

```py
class Table(Component):
    class Kwargs(NamedTuple):
        name: str
        age: int
```

You can actually set these classes to anything you want - whether it's dataclasses,
[Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), or custom classes:

```py
from typing import NamedTuple
from django_components import Component, SlotInput
from pydantic import BaseModel

class Button(Component):
    class Args(NamedTuple):
        size: int
        text: str

    @dataclass
    class Kwargs:
        variable: str
        maybe_var: int | None = None

    class Slots(BaseModel):
        my_slot: SlotInput | None = None

    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        ...
```

We recommend:

- [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
for the `Args` class
- [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple),
[dataclasses](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass),
or [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
for `Kwargs`, `Slots`, `TemplateData`, `JsData`, and `CssData` classes.

However, you can use any class, as long as they meet the conditions below.

### `Args` class

The [`Args`](../../reference/api.md#django_components.Component.Args) class
represents a list of positional arguments. It must meet two conditions:

1. The constructor for the `Args` class must accept positional arguments.

    ```py
    Args(*args)
    ```

2. The `Args` instance must be convertable to a list.

    ```py
    list(Args(1, 2, 3))
    ```

To implement the conversion to a list, you can implement the `__iter__()` method:

```py
class MyClass:
    def __init__(self):
        self.x = 1
        self.y = 2
    
    def __iter__(self):
        return iter([('x', self.x), ('y', self.y)])
```

### Dictionary classes

On the other hand, other types
([`Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
[`Slots`](../../reference/api.md#django_components.Component.Slots),
[`TemplateData`](../../reference/api.md#django_components.Component.TemplateData),
[`JsData`](../../reference/api.md#django_components.Component.JsData),
and [`CssData`](../../reference/api.md#django_components.Component.CssData))
represent dictionaries. They must meet these two conditions:

1. The constructor must accept keyword arguments.

    ```py
    Kwargs(**kwargs)
    Slots(**slots)
    ```

2. The instance must be convertable to a dictionary.

    ```py
    dict(Kwargs(a=1, b=2))
    dict(Slots(a=1, b=2))
    ```

To implement the conversion to a dictionary, you can implement either:

1. `_asdict()` method
    ```py
    class MyClass:
        def __init__(self):
            self.x = 1
            self.y = 2
        
        def _asdict(self):
            return {'x': self.x, 'y': self.y}
    ```

2. Or make the class dict-like with `__iter__()` and `__getitem__()`
    ```py
    class MyClass:
        def __init__(self):
            self.x = 1
            self.y = 2
        
        def __iter__(self):
            return iter([('x', self.x), ('y', self.y)])

        def __getitem__(self, key):
            return getattr(self, key)
    ```

## Passing variadic args and kwargs

You may have a component that accepts any number of args or kwargs.

However, this cannot be described with the current Python's typing system (as of v0.140).

As a workaround:

- For a variable number of positional arguments (`*args`), set a positional argument that accepts a list of values:

    ```py
    class Table(Component):
        class Args:
            args: list[str]

    Table.render(
        args=Table.Args(args=["a", "b", "c"]),
    )
    ```

- For a variable number of keyword arguments (`**kwargs`), set a keyword argument that accepts a dictionary of values:

    ```py
    class Table(Component):
        class Kwargs:
            variable: str
            another: int
            # Pass any extra keys under `extra`
            extra: dict[str, any]

    Table.render(
        kwargs=Table.Kwargs(
            variable="a",
            another=1,
            extra={"foo": "bar"},
        ),
    )
    ```

## Handling no args or no kwargs

To declare that a component accepts no args, kwargs, etc, define the types with no attributes using the `pass` keyword:

```py
from django_components import Component

class Button(Component):
    class Args:
        pass

    class Kwargs:
        pass

    class Slots:
        pass
```

This can get repetitive, so we added a [`Empty`](../../reference/api.md#django_components.Empty) type to make it easier:

```py
from django_components import Component, Empty

class Button(Component):
    Args = Empty
    Kwargs = Empty
    Slots = Empty
```

## Subclassing

Subclassing components with types is simple.

Since each type class is a separate class attribute, you can just override them in the Component subclass.

In the example below, `ButtonExtra` inherits `Kwargs` from `Button`, but overrides the `Args` class.

```py
from django_components import Component, Empty

class Button(Component):
    class Args:
        size: int

    class Kwargs:
        color: str

class ButtonExtra(Button):
    class Args:
        name: str
        size: int

# Stil works the same way!
ButtonExtra.render(
    args=ButtonExtra.Args(name="John", size=30),
    kwargs=ButtonExtra.Kwargs(color="red"),
)
```

The only difference is when it comes to type hints to the data methods like
[`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data).

When you define the nested classes like `Args` and `Kwargs` directly on the class, you
can reference them just by their class name (`Args` and `Kwargs`).

But when you have a Component subclass, and it uses `Args` or `Kwargs` from the parent,
you will have to reference the type as a [forward reference](https://peps.python.org/pep-0563/#forward-references), including the full name of the component
(`Button.Args` and `Button.Kwargs`).

Compare the following:

```py
class Button(Component):
    class Args:
        size: int

    class Kwargs:
        color: str

    # Both `Args` and `Kwargs` are defined on the class
    def get_template_data(self, args: Args, kwargs: Kwargs, slots, context):
        pass

class ButtonExtra(Button):
    class Args(NamedTuple):
        name: str
        size: int

    # `Args` is defined on the subclass, `Kwargs` is defined on the parent
    def get_template_data(self, args: Args, kwargs: "ButtonExtra.Kwargs", slots, context):
        pass

class ButtonSame(Button):
    # Both `Args` and `Kwargs` are defined on the parent
    def get_template_data(self, args: "ButtonSame.Args", kwargs: "ButtonSame.Kwargs", slots, context):
        pass
```

## Runtime type validation

When you add types to your component, and implement
them as [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple) or [`dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass), the validation will check only for the presence of the attributes.

So this will not catch if you pass a string to an `int` attribute.

To enable runtime type validation, you need to use [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), and install the [`djc-ext-pydantic`](https://github.com/django-components/djc-ext-pydantic) extension.

The `djc-ext-pydantic` extension ensures compatibility between django-components' classes such as `Component`, or `Slot` and Pydantic models.

First install the extension:

```bash
pip install djc-ext-pydantic
```

And then add the extension to your project:

```py
COMPONENTS = {
    "extensions": [
        "djc_pydantic.PydanticExtension",
    ],
}
```

<!-- TODO_V1 - REMOVE IN v1 -->

## Migrating from generics to class attributes

In versions 0.92 to 0.139 (inclusive), the component typing was specified through generics.

Since v0.140, the types must be specified as class attributes of the [Component](../../reference/api.md#django_components.Component) class -
[`Args`](../../reference/api.md#django_components.Component.Args),
[`Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
[`Slots`](../../reference/api.md#django_components.Component.Slots),
[`TemplateData`](../../reference/api.md#django_components.Component.TemplateData),
[`JsData`](../../reference/api.md#django_components.Component.JsData),
and [`CssData`](../../reference/api.md#django_components.Component.CssData).

This change was necessary to make it possible to subclass components. Subclassing with generics was otherwise too complicated. Read the discussion [here](https://github.com/django-components/django-components/issues/1122).

Because of this change, the [`Component.render()`](../../reference/api.md#django_components.Component.render)
method is no longer typed.
To type-check the inputs, you should wrap the inputs in [`Component.Args`](../../reference/api.md#django_components.Component.Args),
[`Component.Kwargs`](../../reference/api.md#django_components.Component.Kwargs),
[`Component.Slots`](../../reference/api.md#django_components.Component.Slots), etc.

For example, if you had a component like this:

```py
from typing import NotRequired, TypedDict, TypeAlias
from django_components import Component, Slot, SlotInput

ButtonArgs: TypeAlias = tuple[int, str]

class ButtonKwargs(TypedDict):
    variable: str
    another: int
    maybe_var: NotRequired[int] # May be omitted

class ButtonSlots(TypedDict):
    # Use `SlotInput` to allow slots to be given as `Slot` instance,
    # plain string, or a function that returns a string.
    my_slot: NotRequired[SlotInput]
    # Use `Slot` to allow ONLY `Slot` instances.
    another_slot: Slot

ButtonType: TypeAlias = Component[ButtonArgs, ButtonKwargs, ButtonSlots]

class Button(ButtonType):
    def get_context_data(self, *args, **kwargs):
        self.input.args[0]  # int
        self.input.kwargs["variable"]  # str
        self.input.slots["my_slot"]  # Slot[MySlotData]

Button.render(
    args=(1, "hello"),
    kwargs={
        "variable": "world",
        "another": 123,
    },
    slots={
        "my_slot": "...",
        "another_slot": Slot(lambda ctx: ...),
    },
)
```

The steps to migrate are:

1. Convert all the types (`ButtonArgs`, `ButtonKwargs`, `ButtonSlots`) to subclasses
    of [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple).
2. Move these types inside the Component class (`Button`), and rename them to `Args`, `Kwargs`, and `Slots`.
3. If you defined typing for the data methods (like [`get_context_data()`](../../reference/api.md#django_components.Component.get_context_data)), move them inside the Component class, and rename them to `TemplateData`, `JsData`, and `CssData`.
4. Remove the `Component` generic.
5. If you accessed the `args`, `kwargs`, or `slots` attributes via
    [`self.input`](../../reference/api.md#django_components.Component.input), you will need to add the type hints yourself, because [`self.input`](../../reference/api.md#django_components.Component.input) is no longer typed.

    Otherwise, you may use [`Component.get_template_data()`](../../reference/api.md#django_components.Component.get_template_data) instead of [`get_context_data()`](../../reference/api.md#django_components.Component.get_context_data), as `get_template_data()` receives `args`, `kwargs`, `slots` and `context` as arguments. You will still need to add the type hints yourself.

6. Lastly, you will need to update the [`Component.render()`](../../reference/api.md#django_components.Component.render)
    calls to wrap the inputs in [`Component.Args`](../../reference/api.md#django_components.Component.Args), [`Component.Kwargs`](../../reference/api.md#django_components.Component.Kwargs), and [`Component.Slots`](../../reference/api.md#django_components.Component.Slots), to manually add type hints.

Thus, the code above will become:

```py
from django.template import Context
from django_components import Component, Slot, SlotInput

# The Component class does not take any generics
class Button(Component):
    # Types are now defined inside the component class
    class Args:
        size: int
        text: str

    class Kwargs:
        variable: str
        another: int
        maybe_var: int | None = None  # May be omitted

    class Slots:
        # Use `SlotInput` to allow slots to be given as `Slot` instance,
        # plain string, or a function that returns a string.
        my_slot: SlotInput | None = None
        # Use `Slot` to allow ONLY `Slot` instances.
        another_slot: Slot

    # The args, kwargs, slots are instances of the component's Args, Kwargs, and Slots classes
    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        args.size  # int
        kwargs.variable  # str
        slots.my_slot  # Slot[MySlotData]

Button.render(
    # Wrap the inputs in the component's Args, Kwargs, and Slots classes
    args=Button.Args(1, "hello"),
    kwargs=Button.Kwargs(
        variable="world",
        another=123,
    ),
    slots=Button.Slots(
        my_slot="...",
        another_slot=Slot(lambda ctx: ...),
    ),
)
```
