import sys
import typing
from typing import Any, Tuple

# See https://peps.python.org/pep-0655/#usage-in-python-3-11
# NOTE: Pydantic requires typing_extensions.TypedDict until (not incl) 3.12
if sys.version_info >= (3, 12):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict as TypedDict

try:
    from typing import Annotated  # type: ignore
except ImportError:

    @typing.no_type_check
    class Annotated:  # type: ignore
        def __init__(self, type_: str, *args: Any, **kwargs: Any):
            self.type_ = type_
            self.metadata = args, kwargs

        def __repr__(self) -> str:
            return f"Annotated[{self.type_}, {self.metadata[0]!r}, {self.metadata[1]!r}]"

        def __getitem__(self, params: Any) -> "Annotated[Any, Any, Any]":  # type: ignore
            if not isinstance(params, tuple):
                params = (params,)
            return Annotated(self.type_, *params, **self.metadata[1])  # type: ignore

        def __class_getitem__(self, *params: Any) -> "Annotated[Any, Any, Any]":  # type: ignore
            return Annotated(*params)  # type: ignore


EmptyTuple = Tuple[()]
"""
Tuple with no members.

You can use this to define a [Component](../api#django_components.Component)
that accepts NO positional arguments:

```python
from django_components import Component, EmptyTuple

class Table(Component(EmptyTuple, Any, Any, Any, Any, Any))
    ...
```

After that, when you call [`Component.render()`](../api#django_components.Component.render)
or [`Component.render_to_response()`](../api#django_components.Component.render_to_response),
the `args` parameter will raise type error if `args` is anything else than an empty
tuple.

```python
Table.render(
    args: (),
)
```

Omitting `args` is also fine:

```python
Table.render()
```

Other values are not allowed. This will raise an error with MyPy:

```python
Table.render(
    args: ("one", 2, "three"),
)
```
"""


class EmptyDict(TypedDict):
    """
    TypedDict with no members.

    You can use this to define a [Component](../api#django_components.Component)
    that accepts NO kwargs, or NO slots, or returns NO data from
    [`Component.get_context_data()`](../api#django_components.Component.get_context_data)
    /
    [`Component.get_js_data()`](../api#django_components.Component.get_js_data)
    /
    [`Component.get_css_data()`](../api#django_components.Component.get_css_data):

    Accepts NO kwargs:

    ```python
    from django_components import Component, EmptyDict

    class Table(Component(Any, EmptyDict, Any, Any, Any, Any))
        ...
    ```

    Accepts NO slots:

    ```python
    from django_components import Component, EmptyDict

    class Table(Component(Any, Any, EmptyDict, Any, Any, Any))
        ...
    ```

    Returns NO data from `get_context_data()`:

    ```python
    from django_components import Component, EmptyDict

    class Table(Component(Any, Any, Any, EmptyDict, Any, Any))
        ...
    ```

    Going back to the example with NO kwargs, when you then call
    [`Component.render()`](../api#django_components.Component.render)
    or [`Component.render_to_response()`](../api#django_components.Component.render_to_response),
    the `kwargs` parameter will raise type error if `kwargs` is anything else than an empty
    dict.

    ```python
    Table.render(
        kwargs: {},
    )
    ```

    Omitting `kwargs` is also fine:

    ```python
    Table.render()
    ```

    Other values are not allowed. This will raise an error with MyPy:

    ```python
    Table.render(
        kwargs: {
            "one": 2,
            "three": 4,
        },
    )
    ```
    """

    pass
