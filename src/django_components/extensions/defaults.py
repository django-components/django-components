import sys
from dataclasses import MISSING, Field, dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Type
from weakref import WeakKeyDictionary

from django_components.extension import ComponentExtension, OnComponentClassCreatedContext, OnComponentInputContext

if TYPE_CHECKING:
    from django_components.component import Component


# NOTE: `WeakKeyDictionary` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    ComponentDefaultsCache = WeakKeyDictionary[Type["Component"], List["ComponentDefaultField"]]
else:
    ComponentDefaultsCache = WeakKeyDictionary


defaults_by_component: ComponentDefaultsCache = WeakKeyDictionary()


@dataclass
class Default:
    """
    Use this class to mark a field on the `Component.Defaults` class as a factory.

    Read more about [Component defaults](../../concepts/fundamentals/component_defaults).

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


# Figure out which defaults are factories and which are not, at class creation,
# so that the actual creation of the defaults dictionary is simple.
def _extract_defaults(defaults: Optional[Type]) -> List[ComponentDefaultField]:
    defaults_fields: List[ComponentDefaultField] = []
    if defaults is None:
        return defaults_fields

    for default_field_key in dir(defaults):
        # Iterate only over fields set by the user (so non-dunder fields).
        # Plus ignore `component_class` because that was set by the extension system.
        if default_field_key.startswith("__") or default_field_key == "component_class":
            continue

        default_field = getattr(defaults, default_field_key)

        # If the field was defined with dataclass.field(), take the default / factory from there.
        if isinstance(default_field, Field):
            if default_field.default is not MISSING:
                field_value = default_field.default
                is_factory = False
            elif default_field.default_factory is not MISSING:
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
        defaults_fields.append(field_data)

    return defaults_fields


def _apply_defaults(kwargs: Dict, defaults: List[ComponentDefaultField]) -> None:
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


class ComponentDefaults(ComponentExtension.ExtensionClass):
    """
    The interface for `Component.Defaults`.

    The fields of this class are used to set default values for the component's kwargs.

    **Example:**
    ```python
    from django_components import Component, Default

    class MyComponent(Component):
        class Defaults:
            position = "left"
            selected_items = Default(lambda: [1, 2, 3])
    """

    pass


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
    ExtensionClass = ComponentDefaults

    # Preprocess the `Component.Defaults` class, if given, so we don't have to do it
    # each time a component is rendered.
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        defaults_cls = getattr(ctx.component_cls, "Defaults", None)
        defaults_by_component[ctx.component_cls] = _extract_defaults(defaults_cls)

    # Apply defaults to missing or `None` values in `kwargs`
    def on_component_input(self, ctx: OnComponentInputContext) -> None:
        defaults = defaults_by_component.get(ctx.component_cls, None)
        if defaults is None:
            return

        _apply_defaults(ctx.kwargs, defaults)
