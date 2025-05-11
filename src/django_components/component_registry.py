import sys
from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional, Set, Type, TypeVar, Union
from weakref import ReferenceType, finalize

from django.template import Library
from django.template.base import Parser, Token

from django_components.app_settings import ContextBehaviorType, app_settings
from django_components.extension import (
    OnComponentRegisteredContext,
    OnComponentUnregisteredContext,
    OnRegistryCreatedContext,
    OnRegistryDeletedContext,
    extensions,
)
from django_components.library import is_tag_protected, mark_protected_tags, register_tag
from django_components.tag_formatter import TagFormatterABC, get_tag_formatter
from django_components.util.weakref import cached_ref

if TYPE_CHECKING:
    from django_components.component import Component


# NOTE: `ReferenceType` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    AllRegistries = List[ReferenceType["ComponentRegistry"]]
else:
    AllRegistries = List[ReferenceType]


TComponent = TypeVar("TComponent", bound="Component")


class AlreadyRegistered(Exception):
    """
    Raised when you try to register a [Component](../api#django_components#Component),
    but it's already registered with given
    [ComponentRegistry](../api#django_components.ComponentRegistry).
    """

    pass


class NotRegistered(Exception):
    """
    Raised when you try to access a [Component](../api#django_components#Component),
    but it's NOT registered with given
    [ComponentRegistry](../api#django_components.ComponentRegistry).
    """

    pass


# Why do we store the tags with the components?
#
# With the addition of TagFormatter, each component class may have a unique
# set of template tags.
#
# For user's convenience, we automatically add/remove the tags from Django's tag Library,
# when a component is (un)registered.
#
# Thus we need to remember which component used which template tags.
class ComponentRegistryEntry(NamedTuple):
    cls: Type["Component"]
    tag: str


class RegistrySettings(NamedTuple):
    """
    Configuration for a [`ComponentRegistry`](../api#django_components.ComponentRegistry).

    These settings define how the components registered with this registry will behave when rendered.

    ```python
    from django_components import ComponentRegistry, RegistrySettings

    registry_settings = RegistrySettings(
        context_behavior="django",
        tag_formatter="django_components.component_shorthand_formatter",
    )

    registry = ComponentRegistry(settings=registry_settings)
    ```
    """

    context_behavior: Optional[ContextBehaviorType] = None
    """
    Same as the global
    [`COMPONENTS.context_behavior`](../settings#django_components.app_settings.ComponentsSettings.context_behavior)
    setting, but for this registry.

    If omitted, defaults to the global
    [`COMPONENTS.context_behavior`](../settings#django_components.app_settings.ComponentsSettings.context_behavior)
    setting.
    """

    # TODO_REMOVE_IN_V1
    CONTEXT_BEHAVIOR: Optional[ContextBehaviorType] = None
    """
    _Deprecated. Use `context_behavior` instead. Will be removed in v1._

    Same as the global
    [`COMPONENTS.context_behavior`](../settings#django_components.app_settings.ComponentsSettings.context_behavior)
    setting, but for this registry.

    If omitted, defaults to the global
    [`COMPONENTS.context_behavior`](../settings#django_components.app_settings.ComponentsSettings.context_behavior)
    setting.
    """

    tag_formatter: Optional[Union["TagFormatterABC", str]] = None
    """
    Same as the global
    [`COMPONENTS.tag_formatter`](../settings#django_components.app_settings.ComponentsSettings.tag_formatter)
    setting, but for this registry.

    If omitted, defaults to the global
    [`COMPONENTS.tag_formatter`](../settings#django_components.app_settings.ComponentsSettings.tag_formatter)
    setting.
    """

    # TODO_REMOVE_IN_V1
    TAG_FORMATTER: Optional[Union["TagFormatterABC", str]] = None
    """
    _Deprecated. Use `tag_formatter` instead. Will be removed in v1._

    Same as the global
    [`COMPONENTS.tag_formatter`](../settings#django_components.app_settings.ComponentsSettings.tag_formatter)
    setting, but for this registry.

    If omitted, defaults to the global
    [`COMPONENTS.tag_formatter`](../settings#django_components.app_settings.ComponentsSettings.tag_formatter)
    setting.
    """


class InternalRegistrySettings(NamedTuple):
    context_behavior: ContextBehaviorType
    tag_formatter: Union["TagFormatterABC", str]


# We keep track of all registries that exist so that, when users want to
# dynamically resolve component name to component class, they would be able
# to search across all registries.
ALL_REGISTRIES: AllRegistries = []


def all_registries() -> List["ComponentRegistry"]:
    """
    Get a list of all created [`ComponentRegistry`](../api#django_components.ComponentRegistry) instances.
    """
    registries: List["ComponentRegistry"] = []
    for reg_ref in ALL_REGISTRIES:
        reg = reg_ref()
        if reg is not None:
            registries.append(reg)
    return registries


class ComponentRegistry:
    """
    Manages [components](../api#django_components.Component) and makes them available
    in the template, by default as [`{% component %}`](../template_tags#component)
    tags.

    ```django
    {% component "my_comp" key=value %}
    {% endcomponent %}
    ```

    To enable a component to be used in a template, the component must be registered with a component registry.

    When you register a component to a registry, behind the scenes the registry
    automatically adds the component's template tag (e.g. `{% component %}` to
    the [`Library`](https://docs.djangoproject.com/en/5.2/howto/custom-template-tags/#code-layout).
    And the opposite happens when you unregister a component - the tag is removed.

    See [Registering components](../../concepts/advanced/component_registry).

    Args:
        library (Library, optional): Django\
            [`Library`](https://docs.djangoproject.com/en/5.2/howto/custom-template-tags/#code-layout)\
            associated with this registry. If omitted, the default Library instance from django_components is used.
        settings (Union[RegistrySettings, Callable[[ComponentRegistry], RegistrySettings]], optional): Configure\
            how the components registered with this registry will behave when rendered.\
            See [`RegistrySettings`](../api#django_components.RegistrySettings). Can be either\
            a static value or a callable that returns the settings. If omitted, the settings from\
            [`COMPONENTS`](../settings#django_components.app_settings.ComponentsSettings) are used.

    **Notes:**

    - The default registry is available as [`django_components.registry`](../api#django_components.registry).
    - The default registry is used when registering components with [`@register`](../api#django_components.register)
    decorator.

    **Example:**

    ```python
    # Use with default Library
    registry = ComponentRegistry()

    # Or a custom one
    my_lib = Library()
    registry = ComponentRegistry(library=my_lib)

    # Usage
    registry.register("button", ButtonComponent)
    registry.register("card", CardComponent)
    registry.all()
    registry.clear()
    registry.get("button")
    registry.has("button")
    ```

    # Using registry to share components

    You can use component registry for isolating or "packaging" components:

    1. Create new instance of `ComponentRegistry` and Library:
        ```django
        my_comps = Library()
        my_comps_reg = ComponentRegistry(library=my_comps)
        ```

    2. Register components to the registry:
        ```django
        my_comps_reg.register("my_button", ButtonComponent)
        my_comps_reg.register("my_card", CardComponent)
        ```

    3. In your target project, load the Library associated with the registry:
        ```django
        {% load my_comps %}
        ```

    4. Use the registered components in your templates:
        ```django
        {% component "button" %}
        {% endcomponent %}
        ```
    """

    def __init__(
        self,
        library: Optional[Library] = None,
        settings: Optional[Union[RegistrySettings, Callable[["ComponentRegistry"], RegistrySettings]]] = None,
    ) -> None:
        self._registry: Dict[str, ComponentRegistryEntry] = {}  # component name -> component_entry mapping
        self._tags: Dict[str, Set[str]] = {}  # tag -> list[component names]
        self._library = library
        self._settings = settings

        ALL_REGISTRIES.append(cached_ref(self))

        extensions.on_registry_created(
            OnRegistryCreatedContext(
                registry=self,
            )
        )

    def __del__(self) -> None:
        # Skip if `extensions` was deleted before this registry
        if not extensions:
            return

        extensions.on_registry_deleted(
            OnRegistryDeletedContext(
                registry=self,
            )
        )

        # Unregister all components when the registry is deleted
        self.clear()

    def __copy__(self) -> "ComponentRegistry":
        new_registry = ComponentRegistry(self.library, self._settings)
        new_registry._registry = self._registry.copy()
        new_registry._tags = self._tags.copy()
        return new_registry

    @property
    def library(self) -> Library:
        """
        The template tag [`Library`](https://docs.djangoproject.com/en/5.2/howto/custom-template-tags/#code-layout)
        that is associated with the registry.
        """
        # Lazily use the default library if none was passed
        if self._library is not None:
            lib = self._library
        else:
            from django_components.templatetags.component_tags import register as tag_library

            # For the default library, we want to protect our template tags from
            # being overriden.
            # On the other hand, if user provided their own Library instance,
            # it is up to the user to use `mark_protected_tags` if they want
            # to protect any tags.
            mark_protected_tags(tag_library)
            lib = self._library = tag_library
        return lib

    @property
    def settings(self) -> InternalRegistrySettings:
        """
        [Registry settings](../api#django_components.RegistrySettings) configured for this registry.
        """
        # NOTE: We allow the settings to be given as a getter function
        # so the settings can respond to changes.
        if callable(self._settings):
            settings_input: Optional[RegistrySettings] = self._settings(self)
        else:
            settings_input = self._settings

        if settings_input:
            context_behavior = settings_input.context_behavior or settings_input.CONTEXT_BEHAVIOR
            tag_formatter = settings_input.tag_formatter or settings_input.TAG_FORMATTER
        else:
            context_behavior = None
            tag_formatter = None

        return InternalRegistrySettings(
            context_behavior=context_behavior or app_settings.CONTEXT_BEHAVIOR.value,
            tag_formatter=tag_formatter or app_settings.TAG_FORMATTER,
        )

    def register(self, name: str, component: Type["Component"]) -> None:
        """
        Register a [`Component`](../api#django_components.Component) class
        with this registry under the given name.

        A component MUST be registered before it can be used in a template such as:
        ```django
        {% component "my_comp" %}
        {% endcomponent %}
        ```

        Args:
            name (str): The name under which the component will be registered. Required.
            component (Type[Component]): The component class to register. Required.

        **Raises:**

        - [`AlreadyRegistered`](../exceptions#django_components.AlreadyRegistered)
        if a different component was already registered under the same name.

        **Example:**

        ```python
        registry.register("button", ButtonComponent)
        ```
        """
        existing_component = self._registry.get(name)
        if existing_component and existing_component.cls.class_id != component.class_id:
            raise AlreadyRegistered('The component "%s" has already been registered' % name)

        entry = self._register_to_library(name, component)

        # Keep track of which components use which tags, because multiple components may
        # use the same tag.
        tag = entry.tag
        if tag not in self._tags:
            self._tags[tag] = set()
        self._tags[tag].add(name)

        self._registry[name] = entry

        # If the component class is deleted, unregister it from this registry.
        finalize(entry.cls, lambda: self.unregister(name) if name in self._registry else None)

        extensions.on_component_registered(
            OnComponentRegisteredContext(
                registry=self,
                name=name,
                component_cls=entry.cls,
            )
        )

    def unregister(self, name: str) -> None:
        """
        Unregister the [`Component`](../api#django_components.Component) class
        that was registered under the given name.

        Once a component is unregistered, it is no longer available in the templates.

        Args:
            name (str): The name under which the component is registered. Required.

        **Raises:**

        - [`NotRegistered`](../exceptions#django_components.NotRegistered)
        if the given name is not registered.

        **Example:**

        ```python
        # First register component
        registry.register("button", ButtonComponent)
        # Then unregister
        registry.unregister("button")
        ```
        """
        # Validate
        self.get(name)

        entry = self._registry[name]
        tag = entry.tag

        # Unregister the tag from library.
        # If this was the last component using this tag, unlink component from tag.
        if tag in self._tags:
            if name in self._tags[tag]:
                self._tags[tag].remove(name)

            # Cleanup
            is_tag_empty = not len(self._tags[tag])
            if is_tag_empty:
                self._tags.pop(tag, None)
        else:
            is_tag_empty = True

        # Only unregister a tag if it's NOT protected
        is_protected = is_tag_protected(self.library, tag)
        if not is_protected:
            # Unregister the tag from library if this was the last component using this tag
            if is_tag_empty and tag in self.library.tags:
                self.library.tags.pop(tag, None)

        entry = self._registry[name]
        del self._registry[name]

        extensions.on_component_unregistered(
            OnComponentUnregisteredContext(
                registry=self,
                name=name,
                component_cls=entry.cls,
            )
        )

    def get(self, name: str) -> Type["Component"]:
        """
        Retrieve a [`Component`](../api#django_components.Component)
        class registered under the given name.

        Args:
            name (str): The name under which the component was registered. Required.

        Returns:
            Type[Component]: The component class registered under the given name.

        **Raises:**

        - [`NotRegistered`](../exceptions#django_components.NotRegistered)
          if the given name is not registered.

        **Example:**

        ```python
        # First register component
        registry.register("button", ButtonComponent)
        # Then get
        registry.get("button")
        # > ButtonComponent
        ```
        """
        if name not in self._registry:
            raise NotRegistered('The component "%s" is not registered' % name)

        return self._registry[name].cls

    def has(self, name: str) -> bool:
        """
        Check if a [`Component`](../api#django_components.Component)
        class is registered under the given name.

        Args:
            name (str): The name under which the component was registered. Required.

        Returns:
            bool: `True` if the component is registered, `False` otherwise.

        **Example:**

        ```python
        # First register component
        registry.register("button", ButtonComponent)
        # Then check
        registry.has("button")
        # > True
        ```
        """
        return name in self._registry

    def all(self) -> Dict[str, Type["Component"]]:
        """
        Retrieve all registered [`Component`](../api#django_components.Component) classes.

        Returns:
            Dict[str, Type[Component]]: A dictionary of component names to component classes

        **Example:**

        ```python
        # First register components
        registry.register("button", ButtonComponent)
        registry.register("card", CardComponent)
        # Then get all
        registry.all()
        # > {
        # >   "button": ButtonComponent,
        # >   "card": CardComponent,
        # > }
        ```
        """
        comps = {key: entry.cls for key, entry in self._registry.items()}
        return comps

    def clear(self) -> None:
        """
        Clears the registry, unregistering all components.

        Example:

        ```python
        # First register components
        registry.register("button", ButtonComponent)
        registry.register("card", CardComponent)
        # Then clear
        registry.clear()
        # Then get all
        registry.all()
        # > {}
        ```
        """
        all_comp_names = list(self._registry.keys())
        for comp_name in all_comp_names:
            self.unregister(comp_name)

        self._registry = {}
        self._tags = {}

    def _register_to_library(
        self,
        comp_name: str,
        component: Type["Component"],
    ) -> ComponentRegistryEntry:
        # Lazily import to avoid circular dependencies
        from django_components.component import ComponentNode

        registry = self

        # Define a tag function that pre-processes the tokens, extracting
        # the component name and passing the rest to the actual tag function.
        def tag_fn(parser: Parser, token: Token) -> ComponentNode:
            # Let the TagFormatter pre-process the tokens
            bits = token.split_contents()
            formatter = get_tag_formatter(registry)
            result = formatter.parse([*bits])
            start_tag = formatter.start_tag(result.component_name)
            end_tag = formatter.end_tag(result.component_name)

            # NOTE: The tokens returned from TagFormatter.parse do NOT include the tag itself,
            # so we add it back in.
            bits = [bits[0], *result.tokens]
            token.contents = " ".join(bits)

            return ComponentNode.parse(
                parser,
                token,
                registry=registry,
                name=result.component_name,
                start_tag=start_tag,
                end_tag=end_tag,
            )

        formatter = get_tag_formatter(registry)
        start_tag = formatter.start_tag(comp_name)
        register_tag(self.library, start_tag, tag_fn)

        return ComponentRegistryEntry(cls=component, tag=start_tag)


# This variable represents the global component registry
registry: ComponentRegistry = ComponentRegistry()
"""
The default and global [component registry](./#django_components.ComponentRegistry).
Use this instance to directly register or remove components:

See [Registering components](../../concepts/advanced/component_registry).

```python
# Register components
registry.register("button", ButtonComponent)
registry.register("card", CardComponent)

# Get single
registry.get("button")

# Get all
registry.all()

# Check if component is registered
registry.has("button")

# Unregister single
registry.unregister("button")

# Unregister all
registry.clear()
```
"""

# NOTE: Aliased so that the arg to `@register` can also be called `registry`
_the_registry = registry


def register(name: str, registry: Optional[ComponentRegistry] = None) -> Callable[
    [Type[TComponent]],
    Type[TComponent],
]:
    """
    Class decorator for registering a [component](./#django_components.Component)
    to a [component registry](./#django_components.ComponentRegistry).

    See [Registering components](../../concepts/advanced/component_registry).

    Args:
        name (str): Registered name. This is the name by which the component will be accessed\
            from within a template when using the [`{% component %}`](../template_tags#component) tag. Required.
        registry (ComponentRegistry, optional): Specify the [registry](./#django_components.ComponentRegistry)\
            to which to register this component. If omitted, component is registered to the default registry.

    Raises:
        AlreadyRegistered: If there is already a component registered under the same name.

    **Examples**:

    ```python
    from django_components import Component, register

    @register("my_component")
    class MyComponent(Component):
        ...
    ```

    Specifing [`ComponentRegistry`](./#django_components.ComponentRegistry) the component
    should be registered to by setting the `registry` kwarg:

    ```python
    from django.template import Library
    from django_components import Component, ComponentRegistry, register

    my_lib = Library()
    my_reg = ComponentRegistry(library=my_lib)

    @register("my_component", registry=my_reg)
    class MyComponent(Component):
        ...
    ```
    """
    if registry is None:
        registry = _the_registry

    def decorator(component: Type[TComponent]) -> Type[TComponent]:
        registry.register(name=name, component=component)
        return component

    return decorator
