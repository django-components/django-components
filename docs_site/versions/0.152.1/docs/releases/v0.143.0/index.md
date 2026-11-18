---
title: v0.143.0 (2025-10-22)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.143.0/
description: "- You can now define component input defaults directly on Component.Kwargs."
---

# v0.143.0 (2025-10-22)

#### Feat

- You can now define component input defaults directly on `Component.Kwargs`.

    Before, the defaults had to be defined on a separate `Component.Defaults` class:


    ```python
    class ProfileCard(Component):
        class Kwargs:
            user_id: int
            show_details: bool

        class Defaults:
            show_details = True
    ```


    Now, django-components can detect the defaults from `Component.Kwargs` and apply
    them. So you can merge `Component.Kwargs` with `Component.Defaults`:


    ```python
    class ProfileCard(Component):
        class Kwargs:
            user_id: int
            show_details: bool = True
    ```


    NOTE: This applies only when `Component.Kwargs` is a NamedTuple or dataclass.

- New helper `get_component_defaults()`:

    Now, the defaults may be defined on either `Component.Defaults` and `Component.Kwargs` classes.

    To get a final, merged dictionary of all the component's defaults, use `get_component_defaults()`:


    ```py
    from django_components import Component, Default, get_component_defaults

    class MyTable(Component):
        class Kwargs:
            position: str
            order: int
            items: list[int]
            variable: str = "from_kwargs"

        class Defaults:
            position: str = "left"
            items = Default(lambda: [1, 2, 3])

    defaults = get_component_defaults(MyTable)
    # {
    #     "position": "left",
    #     "items": [1, 2, 3],
    #     "variable": "from_kwargs",
    # }
    ```


- Simpler syntax for defining component inputs:

    When defining `Args`, `Kwargs`, `Slots`, `JsData`, `CssData`, `TemplateData`, these data classes now don't have to subclass any other class.

    If they are not subclassing (nor `@dataclass`), these data classes will be automatically converted to `NamedTuples`:

    Before - the `Args`, `Kwargs`, and `Slots` (etc..) had to be NamedTuples, dataclasses, or Pydantic models:


    ```py
    from typing import NamedTuple
    from django_components import Component

    class Button(Component):
        class Args(NamedTuple):
            size: int
            text: str

        class Kwargs(NamedTuple):
            variable: str
            maybe_var: Optional[int] = None

        class Slots(NamedTuple):
            my_slot: Optional[SlotInput] = None

        def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
            ...
    ```


    Now these classes are automatically converted to `NamedTuples` if they don't subclass anything else:


    ```py
    class Button(Component):
        class Args:  # Same as `Args(NamedTuple)`
            size: int
            text: str

        class Kwargs:  # Same as `Kwargs(NamedTuple)`
            variable: str
            maybe_var: Optional[int] = None

        class Slots:  # Same as `Slots(NamedTuple)`
            my_slot: Optional[SlotInput] = None

        def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
            ...
    ```


#### Refactor

- Add support for Python 3.14

- Extension authors: The `ExtensionComponentConfig` can be instantiated with `None` instead of a component instance.

  This allows to call component-level extension methods outside of the normal rendering lifecycle.