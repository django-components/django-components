from typing import NamedTuple


class Empty(NamedTuple):
    """
    Type for an object with no members.

    You can use this to define [Component](../api#django_components.Component)
    types that accept NO args, kwargs, slots, etc:

    ```python
    from django_components import Component, Empty

    class Table(Component):
        Args = Empty
        Kwargs = Empty
        ...
    ```

    This class is a shorthand for:

    ```py
    class Empty(NamedTuple):
        pass
    ```

    Read more about [Typing and validation](../../concepts/advanced/typing_and_validation).
    """

    pass
