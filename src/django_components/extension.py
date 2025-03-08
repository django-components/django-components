from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Tuple, Type, TypeVar

from django.template import Context

from django_components.app_settings import app_settings
from django_components.util.command import ComponentCommand
from django_components.util.misc import snake_to_pascal

if TYPE_CHECKING:
    from django_components import Component
    from django_components.component_registry import ComponentRegistry


TCallable = TypeVar("TCallable", bound=Callable)


################################################
# HOOK TYPES
#
# This is the source of truth for what data is available in each hook.
# NOTE: These types are also used in docs generation, see `docs/scripts/reference.py`.
################################################


class OnComponentClassCreatedContext(NamedTuple):
    component_cls: Type["Component"]
    """The created Component class"""


class OnComponentClassDeletedContext(NamedTuple):
    component_cls: Type["Component"]
    """The to-be-deleted Component class"""


class OnRegistryCreatedContext(NamedTuple):
    registry: "ComponentRegistry"
    """The created ComponentRegistry instance"""


class OnRegistryDeletedContext(NamedTuple):
    registry: "ComponentRegistry"
    """The to-be-deleted ComponentRegistry instance"""


class OnComponentRegisteredContext(NamedTuple):
    registry: "ComponentRegistry"
    """The registry the component was registered to"""
    name: str
    """The name the component was registered under"""
    component_cls: Type["Component"]
    """The registered Component class"""


class OnComponentUnregisteredContext(NamedTuple):
    registry: "ComponentRegistry"
    """The registry the component was unregistered from"""
    name: str
    """The name the component was registered under"""
    component_cls: Type["Component"]
    """The unregistered Component class"""


class OnComponentInputContext(NamedTuple):
    component: "Component"
    """The Component instance that received the input and is being rendered"""
    component_cls: Type["Component"]
    """The Component class"""
    component_id: str
    """The unique identifier for this component instance"""
    args: List
    """List of positional arguments passed to the component"""
    kwargs: Dict
    """Dictionary of keyword arguments passed to the component"""
    slots: Dict
    """Dictionary of slot definitions"""
    context: Context
    """The Django template Context object"""


class OnComponentDataContext(NamedTuple):
    component: "Component"
    """The Component instance that is being rendered"""
    component_cls: Type["Component"]
    """The Component class"""
    component_id: str
    """The unique identifier for this component instance"""
    context_data: Dict
    """Dictionary of context data from `Component.get_context_data()`"""
    js_data: Dict
    """Dictionary of JavaScript data from `Component.get_js_data()`"""
    css_data: Dict
    """Dictionary of CSS data from `Component.get_css_data()`"""


class BaseExtensionClass:
    def __init__(self, component: "Component") -> None:
        self.component = component


# NOTE: This class is used for generating documentation for the extension hooks API.
#       To be recognized, all hooks must start with `on_` prefix.
class ComponentExtension:
    """
    Base class for all extensions.

    Read more on [Extensions](../../concepts/advanced/extensions).
    """

    name: str
    """
    Name of the extension.

    Name must be lowercase, and must be a valid Python identifier (e.g. `"my_extension"`).

    The extension may add new features to the [`Component`](../api#django_components.Component)
    class by allowing users to define and access a nested class in the `Component` class.

    The extension name determines the name of the nested class in the `Component` class, and the attribute
    under which the extension will be accessible.

    E.g. if the extension name is `"my_extension"`, then the nested class in the `Component` class
    will be `MyExtension`, and the extension will be accessible as `MyComp.my_extension`.

    ```python
    class MyComp(Component):
        class MyExtension:
            ...

        def get_context_data(self):
            return {
                "my_extension": self.my_extension.do_something(),
            }
    ```
    """

    class_name: str
    """
    Name of the extension class.

    By default, this is the same as `name`, but with snake_case converted to PascalCase.

    So if the extension name is `"my_extension"`, then the extension class name will be `"MyExtension"`.

    ```python
    class MyComp(Component):
        class MyExtension:  # <--- This is the extension class
            ...
    ```
    """

    ExtensionClass = BaseExtensionClass
    """
    Base class that the "extension class" nested within a [`Component`](../api#django_components.Component)
    class will inherit from.

    This is where you can define new methods and attributes that will be available to the component
    instance.

    Background:

    The extension may add new features to the `Component` class by allowing users to
    define and access a nested class in the `Component` class. E.g.:

    ```python
    class MyComp(Component):
        class MyExtension:
            ...

        def get_context_data(self):
            return {
                "my_extension": self.my_extension.do_something(),
            }
    ```

    When rendering a component, the nested extension class will be set as a subclass of `ExtensionClass`.
    So it will be same as if the user had directly inherited from `ExtensionClass`. E.g.:

    ```python
    class MyComp(Component):
        class MyExtension(BaseExtensionClass):
            ...
    ```

    This setting decides what the extension class will inherit from.
    """

    commands: List[Type[ComponentCommand]] = []
    """
    List of commands that can be run by the extension.

    These commands will be available to the user as `components ext run <extension> <command>`.

    Commands are defined as subclasses of [`ComponentCommand`](../api#django_components.ComponentCommand).

    **Example:**

    This example defines an extension with a command that prints "Hello world". To run the command,
    the user would run `components ext run hello_world hello`.

    ```python
    from django_components import ComponentCommand, ComponentExtension, CommandArg, CommandArgGroup

    class HelloWorldCommand(ComponentCommand):
        name = "hello"
        help = "Hello world command."

        # Allow to pass flags `--foo`, `--bar` and `--baz`.
        # Argument parsing is managed by `argparse`.
        arguments = [
            CommandArg(
                name_or_flags="--foo",
                help="Foo description.",
            ),
            # When printing the command help message, `bar` and `baz`
            # will be grouped under "group bar".
            CommandArgGroup(
                title="group bar",
                description="Group description.",
                arguments=[
                    CommandArg(
                        name_or_flags="--bar",
                        help="Bar description.",
                    ),
                    CommandArg(
                        name_or_flags="--baz",
                        help="Baz description.",
                    ),
                ],
            ),
        ]

        # Callback that receives the parsed arguments and options.
        def handle(self, *args, **kwargs):
            print(f"HelloWorldCommand.handle: args={args}, kwargs={kwargs}")

    # Associate the command with the extension
    class HelloWorldExtension(ComponentExtension):
        name = "hello_world"

        commands = [
            HelloWorldCommand,
        ]
    ```
    """

    def __init_subclass__(cls) -> None:
        if not cls.name.isidentifier():
            raise ValueError(f"Extension name must be a valid Python identifier, got {cls.name}")
        if not cls.name.islower():
            raise ValueError(f"Extension name must be lowercase, got {cls.name}")

        if not getattr(cls, "class_name", None):
            cls.class_name = snake_to_pascal(cls.name)

    ###########################
    # Component lifecycle hooks
    ###########################

    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        """
        Called when a new [`Component`](../api#django_components.Component) class is created.

        This hook is called after the [`Component`](../api#django_components.Component) class
        is fully defined but before it's registered.

        Use this hook to perform any initialization or validation of the
        [`Component`](../api#django_components.Component) class.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentClassCreatedContext

        class MyExtension(ComponentExtension):
            def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
                # Add a new attribute to the Component class
                ctx.component_cls.my_attr = "my_value"
        ```
        """
        pass

    def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
        """
        Called when a [`Component`](../api#django_components.Component) class is being deleted.

        This hook is called before the [`Component`](../api#django_components.Component) class
        is deleted from memory.

        Use this hook to perform any cleanup related to the [`Component`](../api#django_components.Component) class.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentClassDeletedContext

        class MyExtension(ComponentExtension):
            def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
                # Remove Component class from the extension's cache on deletion
                self.cache.pop(ctx.component_cls, None)
        ```
        """
        pass

    def on_registry_created(self, ctx: OnRegistryCreatedContext) -> None:
        """
        Called when a new [`ComponentRegistry`](../api#django_components.ComponentRegistry) is created.

        This hook is called after a new
        [`ComponentRegistry`](../api#django_components.ComponentRegistry) instance is initialized.

        Use this hook to perform any initialization needed for the registry.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnRegistryCreatedContext

        class MyExtension(ComponentExtension):
            def on_registry_created(self, ctx: OnRegistryCreatedContext) -> None:
                # Add a new attribute to the registry
                ctx.registry.my_attr = "my_value"
        ```
        """
        pass

    def on_registry_deleted(self, ctx: OnRegistryDeletedContext) -> None:
        """
        Called when a [`ComponentRegistry`](../api#django_components.ComponentRegistry) is being deleted.

        This hook is called before
        a [`ComponentRegistry`](../api#django_components.ComponentRegistry) instance is deleted.

        Use this hook to perform any cleanup related to the registry.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnRegistryDeletedContext

        class MyExtension(ComponentExtension):
            def on_registry_deleted(self, ctx: OnRegistryDeletedContext) -> None:
                # Remove registry from the extension's cache on deletion
                self.cache.pop(ctx.registry, None)
        ```
        """
        pass

    def on_component_registered(self, ctx: OnComponentRegisteredContext) -> None:
        """
        Called when a [`Component`](../api#django_components.Component) class is
        registered with a [`ComponentRegistry`](../api#django_components.ComponentRegistry).

        This hook is called after a [`Component`](../api#django_components.Component) class
        is successfully registered.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentRegisteredContext

        class MyExtension(ComponentExtension):
            def on_component_registered(self, ctx: OnComponentRegisteredContext) -> None:
                print(f"Component {ctx.component_cls} registered to {ctx.registry} as '{ctx.name}'")
        ```
        """
        pass

    def on_component_unregistered(self, ctx: OnComponentUnregisteredContext) -> None:
        """
        Called when a [`Component`](../api#django_components.Component) class is
        unregistered from a [`ComponentRegistry`](../api#django_components.ComponentRegistry).

        This hook is called after a [`Component`](../api#django_components.Component) class
        is removed from the registry.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentUnregisteredContext

        class MyExtension(ComponentExtension):
            def on_component_unregistered(self, ctx: OnComponentUnregisteredContext) -> None:
                print(f"Component {ctx.component_cls} unregistered from {ctx.registry} as '{ctx.name}'")
        ```
        """
        pass

    ###########################
    # Component render hooks
    ###########################

    def on_component_input(self, ctx: OnComponentInputContext) -> None:
        """
        Called when a [`Component`](../api#django_components.Component) was triggered to render,
        but before a component's context and data methods are invoked.

        This hook is called before
        [`Component.get_context_data()`](../api#django_components.Component.get_context_data),
        [`Component.get_js_data()`](../api#django_components.Component.get_js_data)
        and [`Component.get_css_data()`](../api#django_components.Component.get_css_data).

        Use this hook to modify or validate component inputs before they're processed.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentInputContext

        class MyExtension(ComponentExtension):
            def on_component_input(self, ctx: OnComponentInputContext) -> None:
                # Add extra kwarg to all components when they are rendered
                ctx.kwargs["my_input"] = "my_value"
        ```
        """
        pass

    def on_component_data(self, ctx: OnComponentDataContext) -> None:
        """
        Called when a Component was triggered to render, after a component's context
        and data methods have been processed.

        This hook is called after
        [`Component.get_context_data()`](../api#django_components.Component.get_context_data),
        [`Component.get_js_data()`](../api#django_components.Component.get_js_data)
        and [`Component.get_css_data()`](../api#django_components.Component.get_css_data).

        This hook runs after [`on_component_input`](../api#django_components.ComponentExtension.on_component_input).

        Use this hook to modify or validate the component's data before rendering.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentDataContext

        class MyExtension(ComponentExtension):
            def on_component_data(self, ctx: OnComponentDataContext) -> None:
                # Add extra template variable to all components when they are rendered
                ctx.context_data["my_template_var"] = "my_value"
        ```
        """
        pass


# Decorator to store events in `ExtensionManager._events` when django_components is not yet initialized.
def store_events(func: TCallable) -> TCallable:
    fn_name = func.__name__

    @wraps(func)
    def wrapper(self: "ExtensionManager", ctx: Any) -> Any:
        if not self._initialized:
            self._events.append((fn_name, ctx))
            return

        return func(self, ctx)

    return wrapper  # type: ignore[return-value]


# Manage all extensions from a single place
class ExtensionManager:
    ###########################
    # Internal
    ###########################

    _initialized = False
    _events: List[Tuple[str, Any]] = []

    @property
    def extensions(self) -> List[ComponentExtension]:
        return app_settings.EXTENSIONS

    def _init_component_class(self, component_cls: Type["Component"]) -> None:
        # If not yet initialized, this class will be initialized later once we run `_init_app`
        if not self._initialized:
            return

        for extension in self.extensions:
            ext_class_name = extension.class_name

            # If a Component class has an extension class, e.g.
            # ```python
            # class MyComp(Component):
            #     class MyExtension:
            #         ...
            # ```
            # then create a dummy class to make `MyComp.MyExtension` extend
            # the base class `extension.ExtensionClass`.
            #
            # So it will be same as if the user had directly inherited from `extension.ExtensionClass`.
            # ```python
            # class MyComp(Component):
            #     class MyExtension(MyExtension.ExtensionClass):
            #         ...
            # ```
            component_ext_subclass = getattr(component_cls, ext_class_name, None)

            # Add escape hatch, so that user can override the extension class
            # from within the component class. E.g.:
            # ```python
            # class MyExtDifferentStillSame(MyExtension.ExtensionClass):
            #     ...
            #
            # class MyComp(Component):
            #     my_extension_class = MyExtDifferentStillSame
            #     class MyExtension:
            #         ...
            # ```
            #
            # Will be effectively the same as:
            # ```python
            # class MyComp(Component):
            #     class MyExtension(MyExtDifferentStillSame):
            #         ...
            # ```
            ext_class_override_attr = extension.name + "_class"  # "my_extension_class"
            ext_base_class = getattr(component_cls, ext_class_override_attr, extension.ExtensionClass)

            if component_ext_subclass:
                bases: tuple[Type, ...] = (component_ext_subclass, ext_base_class)
            else:
                bases = (ext_base_class,)
            component_ext_subclass = type(ext_class_name, bases, {})

            # Finally, reassign the new class extension class on the component class.
            setattr(component_cls, ext_class_name, component_ext_subclass)

    def _init_component_instance(self, component: "Component") -> None:
        # Each extension has different class defined nested on the Component class:
        # ```python
        # class MyComp(Component):
        #     class MyExtension:
        #         ...
        #     class MyOtherExtension:
        #         ...
        # ```
        #
        # We instantiate them all, passing the component instance to each. These are then
        # available under the extension name on the component instance.
        # ```python
        # component.my_extension
        # component.my_other_extension
        # ```
        for extension in self.extensions:
            # NOTE: `_init_component_class` creates extension-specific nested classes
            # on the created component classes, e.g.:
            # ```py
            # class MyComp(Component):
            #     class MyExtension:
            #         ...
            # ```
            # It should NOT happen in production, but in tests it may happen, if some extensions
            # are test-specific, then the built-in component classes (like DynamicComponent) will
            # be initialized BEFORE the extension is set in the settings. As such, they will be missing
            # the nested class. In that case, we retroactively create the extension-specific nested class,
            # so that we may proceed.
            if not hasattr(component, extension.class_name):
                self._init_component_class(component.__class__)

            used_ext_class = getattr(component, extension.class_name)
            extension_instance = used_ext_class(component)
            setattr(component, extension.name, extension_instance)

    # The triggers for following hooks may occur before the `apps.py` `ready()` hook is called.
    # - on_component_class_created
    # - on_component_class_deleted
    # - on_registry_created
    # - on_registry_deleted
    # - on_component_registered
    # - on_component_unregistered
    #
    # The problem is that the extensions are set up only at the initialization (`ready()` hook in `apps.py`).
    #
    # So in the case that these hooks are triggered before initialization,
    # we store these "events" in a list, and then "flush" them all when `ready()` is called.
    #
    # This way, we can ensure that all extensions are present before any hooks are called.
    def _init_app(self) -> None:
        if self._initialized:
            return

        self._initialized = True

        for hook, data in self._events:
            if hook == "on_component_class_created":
                on_component_created_data: OnComponentClassCreatedContext = data
                self._init_component_class(on_component_created_data.component_cls)
            getattr(self, hook)(data)
        self._events = []

    def get_extension(self, name: str) -> ComponentExtension:
        for extension in self.extensions:
            if extension.name == name:
                return extension
        raise ValueError(f"Extension {name} not found")

    def get_extension_command(self, name: str, command_name: str) -> Type[ComponentCommand]:
        extension = self.get_extension(name)
        for command in extension.commands:
            if command.name == command_name:
                return command
        raise ValueError(f"Command {command_name} not found in extension {name}")

    #############################
    # Component lifecycle hooks
    #############################

    @store_events
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        for extension in self.extensions:
            extension.on_component_class_created(ctx)

    @store_events
    def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
        for extension in self.extensions:
            extension.on_component_class_deleted(ctx)

    @store_events
    def on_registry_created(self, ctx: OnRegistryCreatedContext) -> None:
        for extension in self.extensions:
            extension.on_registry_created(ctx)

    @store_events
    def on_registry_deleted(self, ctx: OnRegistryDeletedContext) -> None:
        for extension in self.extensions:
            extension.on_registry_deleted(ctx)

    @store_events
    def on_component_registered(self, ctx: OnComponentRegisteredContext) -> None:
        for extension in self.extensions:
            extension.on_component_registered(ctx)

    @store_events
    def on_component_unregistered(self, ctx: OnComponentUnregisteredContext) -> None:
        for extension in self.extensions:
            extension.on_component_unregistered(ctx)

    ###########################
    # Component render hooks
    ###########################

    def on_component_input(self, ctx: OnComponentInputContext) -> None:
        for extension in self.extensions:
            extension.on_component_input(ctx)

    def on_component_data(self, ctx: OnComponentDataContext) -> None:
        for extension in self.extensions:
            extension.on_component_data(ctx)


# NOTE: This is a singleton which is takes the extensions from `app_settings.EXTENSIONS`
extensions = ExtensionManager()
