When a component is being rendered, the component inputs are passed to various methods like
[`get_template_data()`](../../../reference/api#django_components.Component.get_template_data),
[`get_js_data()`](../../../reference/api#django_components.Component.get_js_data),
or [`get_css_data()`](../../../reference/api#django_components.Component.get_css_data).

It can be cumbersome to specify default values for each input in each method.

To make things easier, Components can specify their defaults. Defaults are used when
no value is provided, or when the value is set to `None` for a particular input.

### Defining defaults

To define defaults for a component, you create a nested [`Defaults`](../../../reference/api#django_components.Component.Defaults)
class within your [`Component`](../../../reference/api#django_components.Component) class.
Each attribute in the `Defaults` class represents a default value for a corresponding input.

```py
from django_components import Component, Default, register

@register("my_table")
class MyTable(Component):

    class Defaults:
        position = "left"
        selected_items = Default(lambda: [1, 2, 3])

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "position": kwargs["position"],
            "selected_items": kwargs["selected_items"],
        }

    ...
```

In this example, `position` is a simple default value, while `selected_items` uses a factory function wrapped in [`Default`](../../../reference/api#django_components.Default) to ensure a new list is created each time the default is used.

Now, when we render the component, the defaults will be applied:

```django
{% component "my_table" position="right" / %}
```

In this case:

- `position` input is set to `right`, so no defaults applied
- `selected_items` is not set, so it will be set to `[1, 2, 3]`.

Same applies to rendering the Component in Python with the
[`render()`](../../../reference/api#django_components.Component.render) method:

```py
MyTable.render(
    kwargs={
        "position": "right",
        "selected_items": None,
    },
)
```

Notice that we've set `selected_items` to `None`. `None` values are treated as missing values,
and so `selected_items` will be set to `[1, 2, 3]`.

!!! warning

    The defaults are aplied only to keyword arguments. They are NOT applied to positional arguments!

!!! warning

    When [typing](../fundamentals/typing_and_validation.md) your components with [`Args`](../../../reference/api/#django_components.Component.Args),
    [`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
    or [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
    you may be inclined to define the defaults in the classes.

    ```py
    class ProfileCard(Component):
        class Kwargs(NamedTuple):
            show_details: bool = True
    ```

    This is **NOT recommended**, because:

    - The defaults will NOT be applied to inputs when using [`self.raw_kwargs`](../../../reference/api/#django_components.Component.raw_kwargs) property.
    - The defaults will NOT be applied when a field is given but set to `None`.

    Instead, define the defaults in the [`Defaults`](../../../reference/api/#django_components.Component.Defaults) class.

### Default factories

For objects such as lists, dictionaries or other instances, you have to be careful - if you simply set a default value, this instance will be shared across all instances of the component!

```py
from django_components import Component

class MyTable(Component):
    class Defaults:
        # All instances will share the same list!
        selected_items = [1, 2, 3]
```

To avoid this, you can use a factory function wrapped in [`Default`](../../../reference/api#django_components.Default).

```py
from django_components import Component, Default

class MyTable(Component):
    class Defaults:
        # A new list is created for each instance
        selected_items = Default(lambda: [1, 2, 3])
```

This is similar to how the dataclass fields work.

In fact, you can also use the dataclass's [`field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field) function to define the factories:

```py
from dataclasses import field
from django_components import Component

class MyTable(Component):
    class Defaults:
        selected_items = field(default_factory=lambda: [1, 2, 3])
```

### Accessing defaults

Since the defaults are defined on the component class, you can access the defaults for a component with the [`Component.Defaults`](../../../reference/api#django_components.Component.Defaults) property.

So if we have a component like this:

```py
from django_components import Component, Default, register

@register("my_table")
class MyTable(Component):

    class Defaults:
        position = "left"
        selected_items = Default(lambda: [1, 2, 3])

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "position": kwargs["position"],
            "selected_items": kwargs["selected_items"],
        }
```

We can access individual defaults like this:

```py
print(MyTable.Defaults.position)
print(MyTable.Defaults.selected_items)
```
