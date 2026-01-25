import dataclasses
from collections.abc import Callable
from inspect import isclass
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias
from weakref import WeakKeyDictionary

from django_components.extension import (
    ComponentExtension,
    ExtensionComponentConfig,
    OnComponentClassCreatedContext,
    OnComponentInputContext,
)

if TYPE_CHECKING:
    from django_components.component import Component


ComponentDefaultsCache: TypeAlias = WeakKeyDictionary[type["Component"], list["ComponentDefaultField"]]


defaults_by_component: ComponentDefaultsCache = WeakKeyDictionary()


@dataclasses.dataclass
class Default:
    """
    Use this class to mark a field on the `Component.Defaults` class as a factory.

    Read more about [Component defaults](../concepts/fundamentals/component_defaults.md).

    **Example:**

    ```py
    from django_components import Default

    class MyComponent(Component):
        class Defaults:
            # Plain value doesn't need a factory
            position = "left"
            # Lists and dicts need to be wrapped in `Default`
            # Otherwise all instances will share the same value
            selected_items = Default(lambda: [1, 2, 3])
    ```
    """

    value: Callable[[], Any]


class ComponentDefaultField(NamedTuple):
    """Internal representation of a field on the `Defaults` class."""

    key: str
    value: Any
    is_factory: bool


def get_component_defaults(component: "type[Component] | Component") -> dict[str, Any]:
    """
    Generate a defaults dictionary for a [`Component`](api.md#django_components.Component).

    The defaults dictionary is generated from the [`Component.Defaults`](api.md#django_components.Component.Defaults)
    and [`Component.Kwargs`](api.md#django_components.Component.Kwargs) classes.
    `Kwargs` take precedence over `Defaults`.

    Read more about [Component defaults](../concepts/fundamentals/component_defaults.md).

    **Example:**

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

    # Get the defaults dictionary
    defaults = get_component_defaults(MyTable)
    # {
    #     "position": "left",
    #     "items": [1, 2, 3],
    #     "variable": "from_kwargs",
    # }
    ```
    """
    component_cls = component if isclass(component) else component.__class__
    defaults_fields = defaults_by_component[component_cls]  # type: ignore[index]
    defaults: dict[str, Any] = {}
    _apply_defaults(defaults, defaults_fields)
    return defaults


# Figure out which defaults are factories and which are not, at class creation,
# so that the actual creation of the defaults dictionary is simple.
def _extract_defaults(defaults: type | None, kwargs: type | None) -> list["ComponentDefaultField"]:
    """
    Given the `Defaults` and `Kwargs` classes from a component, this function extracts
    the default values from them.
    """
    # First, extract defaults from the `Defaults` class
    defaults_fields_map: dict[str, ComponentDefaultField] = {}
    if defaults is not None:
        for default_field_key in dir(defaults):
            # Iterate only over fields set by the user (so non-dunder fields).
            # Plus ignore `component_class` because that was set by the extension system.
            # TODO_V1 - Remove `component_class`
            if default_field_key.startswith("__") or default_field_key in {"component_class", "component_cls"}:
                continue

            default_field = getattr(defaults, default_field_key)

            if isinstance(default_field, property):
                continue

            # If the field was defined with dataclass.field(), take the default / factory from there.
            if isinstance(default_field, dataclasses.Field):
                if default_field.default is not dataclasses.MISSING:
                    field_value = default_field.default
                    is_factory = False
                elif default_field.default_factory is not dataclasses.MISSING:
                    field_value = default_field.default_factory
                    is_factory = True
                else:
                    field_value = None
                    is_factory = False

            # If the field was defined with our `Default` class, it defined a factory
            elif isinstance(default_field, Default):
                field_value = default_field.value
                is_factory = True

            # If the field was defined with a simple assignment, assume it's NOT a factory.
            else:
                field_value = default_field
                is_factory = False

            field_data = ComponentDefaultField(
                key=default_field_key,
                value=field_value,
                is_factory=is_factory,
            )
            defaults_fields_map[default_field_key] = field_data

    # Next, extract defaults from the `Kwargs` class.
    # We check for dataclasses and NamedTuple, as those are the supported ways to define defaults.
    # Support for other types of `Kwargs` classes, like Pydantic models, is left to extensions.
    kwargs_fields_map: dict[str, ComponentDefaultField] = {}
    if kwargs is not None:
        if dataclasses.is_dataclass(kwargs):
            for field in dataclasses.fields(kwargs):
                if field.default is not dataclasses.MISSING:
                    field_value = field.default
                    is_factory = False
                elif field.default_factory is not dataclasses.MISSING:
                    field_value = field.default_factory
                    is_factory = True
                else:
                    continue  # No default value

                field_data = ComponentDefaultField(
                    key=field.name,
                    value=field_value,
                    is_factory=is_factory,
                )
                kwargs_fields_map[field.name] = field_data

        # Check for NamedTuple.
        # Note that we check for `_fields` to avoid accidentally matching `tuple` subclasses.
        elif issubclass(kwargs, tuple) and hasattr(kwargs, "_fields"):
            # `_field_defaults` is a dict of {field_name: default_value}
            for field_name, default_value in getattr(kwargs, "_field_defaults", {}).items():
                field_data = ComponentDefaultField(
                    key=field_name,
                    value=default_value,
                    is_factory=False,
                )
                kwargs_fields_map[field_name] = field_data

    # Merge the two, with `kwargs` overwriting `defaults`.
    merged_fields_map = {**defaults_fields_map, **kwargs_fields_map}
    return list(merged_fields_map.values())


def _apply_defaults(kwargs: dict, defaults: list["ComponentDefaultField"]) -> None:
    """
    Apply the defaults from `Component.Defaults` to the given `kwargs`.

    Defaults are applied only to missing or `None` values.
    """
    for default_field in defaults:
        # Defaults are applied only to missing or `None` values
        given_value = kwargs.get(default_field.key, None)
        if given_value is not None:
            continue

        if default_field.is_factory:
            default_value = default_field.value()
        else:
            default_value = default_field.value

        kwargs[default_field.key] = default_value


class ComponentDefaults(ExtensionComponentConfig):
    """
    The interface for `Component.Defaults`.

    The fields of this class are used to set default values for the component's kwargs.

    Read more about [Component defaults](../concepts/fundamentals/component_defaults.md).

    **Example:**

    ```python
    from django_components import Component, Default

    class MyComponent(Component):
        class Defaults:
            position = "left"
            selected_items = Default(lambda: [1, 2, 3])
    ```
    """


class DefaultsExtension(ComponentExtension):
    """
    This extension adds a nested `Defaults` class to each `Component`.

    This nested `Defaults` class is used to set default values for the component's kwargs.

    **Example:**

    ```py
    from django_components import Component, Default

    class MyComponent(Component):
        class Defaults:
            position = "left"
            # Factory values need to be wrapped in `Default`
            selected_items = Default(lambda: [1, 2, 3])
    ```

    This extension is automatically added to all components.
    """

    name = "defaults"
    ComponentConfig = ComponentDefaults

    # Preprocess the `Component.Defaults` class, if given, so we don't have to do it
    # each time a component is rendered.
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        defaults_cls = getattr(ctx.component_cls, "Defaults", None)
        # Allow to simply define `Component.Kwargs` with defaults instead of 2 separate classes
        kwargs_cls = getattr(ctx.component_cls, "Kwargs", None)
        defaults_by_component[ctx.component_cls] = _extract_defaults(defaults_cls, kwargs_cls)

    # Apply defaults to missing or `None` values in `kwargs`
    def on_component_input(self, ctx: OnComponentInputContext) -> None:
        defaults = defaults_by_component.get(ctx.component_cls, None)
        if defaults is None:
            return

        _apply_defaults(ctx.kwargs, defaults)
