from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Type, TypeVar, Union

import django.urls
from django.template import Context
from django.urls import URLPattern, URLResolver, get_resolver, get_urlconf

from django_components.app_settings import app_settings
from django_components.compat.django import routes_to_django
from django_components.util.command import ComponentCommand
from django_components.util.misc import snake_to_pascal
from django_components.util.routing import URLRoute

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


# Mark a class as an extension hook context so we can place these in
# a separate documentation section
def mark_extension_hook_api(cls: Type[Any]) -> Type[Any]:
    cls._extension_hook_api = True
    return cls


@mark_extension_hook_api
class OnComponentClassCreatedContext(NamedTuple):
    component_cls: Type["Component"]
    """The created Component class"""


@mark_extension_hook_api
class OnComponentClassDeletedContext(NamedTuple):
    component_cls: Type["Component"]
    """The to-be-deleted Component class"""


@mark_extension_hook_api
class OnRegistryCreatedContext(NamedTuple):
    registry: "ComponentRegistry"
    """The created ComponentRegistry instance"""


@mark_extension_hook_api
class OnRegistryDeletedContext(NamedTuple):
    registry: "ComponentRegistry"
    """The to-be-deleted ComponentRegistry instance"""


@mark_extension_hook_api
class OnComponentRegisteredContext(NamedTuple):
    registry: "ComponentRegistry"
    """The registry the component was registered to"""
    name: str
    """The name the component was registered under"""
    component_cls: Type["Component"]
    """The registered Component class"""


@mark_extension_hook_api
class OnComponentUnregisteredContext(NamedTuple):
    registry: "ComponentRegistry"
    """The registry the component was unregistered from"""
    name: str
    """The name the component was registered under"""
    component_cls: Type["Component"]
    """The unregistered Component class"""


@mark_extension_hook_api
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


@mark_extension_hook_api
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


class OnComponentRenderedContext(NamedTuple):
    component: "Component"
    """The Component instance that is being rendered"""
    component_cls: Type["Component"]
    """The Component class"""
    component_id: str
    """The unique identifier for this component instance"""
    result: str
    """The rendered component"""


################################################
# EXTENSIONS CORE
################################################


class BaseExtensionClass:
    """Base class for all extension classes."""

    component_class: Type["Component"]
    """The Component class that this extension is defined on."""

    def __init__(self, component: "Component") -> None:
        self.component = component


# NOTE: This class is used for generating documentation for the extension hooks API.
#       To be recognized, all hooks must start with `on_` prefix.
class ComponentExtension:
    """
    Base class for all extensions.

    Read more on [Extensions](../../concepts/advanced/extensions).
    """

    ###########################
    # USER INPUT
    ###########################

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
        class MyExtension(ComponentExtension.ExtensionClass):
            ...
    ```

    This setting decides what the extension class will inherit from.
    """

    commands: List[Type[ComponentCommand]] = []
    """
    List of commands that can be run by the extension.

    These commands will be available to the user as `components ext run <extension> <command>`.

    Commands are defined as subclasses of
    [`ComponentCommand`](../extension_commands#django_components.ComponentCommand).

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

    urls: List[URLRoute] = []

    ###########################
    # Misc
    ###########################

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

    def on_component_input(self, ctx: OnComponentInputContext) -> Optional[str]:
        """
        Called when a [`Component`](../api#django_components.Component) was triggered to render,
        but before a component's context and data methods are invoked.

        Use this hook to modify or validate component inputs before they're processed.

        This is the first hook that is called when rendering a component. As such this hook is called before
        [`Component.get_context_data()`](../api#django_components.Component.get_context_data),
        [`Component.get_js_data()`](../api#django_components.Component.get_js_data),
        and [`Component.get_css_data()`](../api#django_components.Component.get_css_data) methods,
        and the
        [`on_component_data`](../extension_hooks#django_components.extension.ComponentExtension.on_component_data)
        hook.

        This hook also allows to skip the rendering of a component altogether. If the hook returns
        a non-null value, this value will be used instead of rendering the component.

        You can use this to implement a caching mechanism for components, or define components
        that will be rendered conditionally.

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
        Called when a [`Component`](../api#django_components.Component) was triggered to render,
        after a component's context and data methods have been processed.

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

    def on_component_rendered(self, ctx: OnComponentRenderedContext) -> Optional[str]:
        """
        Called when a [`Component`](../api#django_components.Component) was rendered, including
        all its child components.

        Use this hook to access or post-process the component's rendered output.

        To modify the output, return a new string from this hook.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentRenderedContext

        class MyExtension(ComponentExtension):
            def on_component_rendered(self, ctx: OnComponentRenderedContext) -> Optional[str]:
                # Append a comment to the component's rendered output
                return ctx.result + "<!-- MyExtension comment -->"
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

    def __init__(self) -> None:
        self._initialized = False
        self._events: List[Tuple[str, Any]] = []
        self._url_resolvers: Dict[str, URLResolver] = {}
        # Keep track of which URLRoute (framework-agnostic) maps to which URLPattern (Django-specific)
        self._route_to_url: Dict[URLRoute, Union[URLPattern, URLResolver]] = {}

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

            # Allow to extension class to access the owner `Component` class that via
            # `ExtensionClass.component_class`.
            component_ext_subclass = type(ext_class_name, bases, {"component_class": component_cls})

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

    def _init_app(self) -> None:
        if self._initialized:
            return

        self._initialized = True

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
        for hook, data in self._events:
            if hook == "on_component_class_created":
                on_component_created_data: OnComponentClassCreatedContext = data
                self._init_component_class(on_component_created_data.component_cls)
            getattr(self, hook)(data)
        self._events = []

        # Populate the `urlpatterns` with URLs specified by the extensions
        # TODO_V3 - Django-specific logic - replace with hook
        urls: List[URLResolver] = []
        for extension in self.extensions:
            # NOTE: The empty list is a placeholder for the URLs that will be added later
            curr_ext_url_resolver = django.urls.path(f"{extension.name}/", django.urls.include([]))
            urls.append(curr_ext_url_resolver)

            # Remember which extension the URLResolver belongs to
            self._url_resolvers[extension.name] = curr_ext_url_resolver

            self.add_extension_urls(extension.name, extension.urls)

        # NOTE: `urlconf_name` is the actual source of truth that holds either a list of URLPatterns
        # or an import string thereof.
        # However, Django's `URLResolver` caches the resolved value of `urlconf_name`
        # under the key `url_patterns`.
        # So we set both:
        # - `urlconf_name` to update the source of truth
        # - `url_patterns` to override the caching
        extensions_url_resolver.urlconf_name = urls
        extensions_url_resolver.url_patterns = urls

        # Rebuild URL resolver cache to be able to resolve the new routes by their names.
        urlconf = get_urlconf()
        resolver = get_resolver(urlconf)
        resolver._populate()

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

    def add_extension_urls(self, name: str, urls: List[URLRoute]) -> None:
        if not self._initialized:
            raise RuntimeError("Cannot add extension URLs before initialization")

        url_resolver = self._url_resolvers[name]
        all_urls = url_resolver.url_patterns
        new_urls = routes_to_django(urls)

        did_add_urls = False

        # Allow to add only those routes that are not yet added
        for route, urlpattern in zip(urls, new_urls):
            if route in self._route_to_url:
                raise ValueError(f"URLRoute {route} already exists")
            self._route_to_url[route] = urlpattern
            all_urls.append(urlpattern)
            did_add_urls = True

        # Force Django's URLResolver to update its lookups, so things like `reverse()` work
        if did_add_urls:
            # Django's root URLResolver
            urlconf = get_urlconf()
            root_resolver = get_resolver(urlconf)
            root_resolver._populate()

    def remove_extension_urls(self, name: str, urls: List[URLRoute]) -> None:
        if not self._initialized:
            raise RuntimeError("Cannot remove extension URLs before initialization")

        url_resolver = self._url_resolvers[name]
        urls_to_remove = routes_to_django(urls)
        all_urls = url_resolver.url_patterns

        # Remove the URLs in reverse order, so that we don't have to deal with index shifting
        for index in reversed(range(len(all_urls))):
            if not urls_to_remove:
                break

            # Instead of simply checking if the URL is in the `urls_to_remove` list, we search for
            # the index of the URL within the `urls_to_remove` list, so we can remove it from there.
            # That way, in theory, the iteration should be faster as the list gets smaller.
            try:
                found_index = urls_to_remove.index(all_urls[index])
            except ValueError:
                found_index = -1

            if found_index != -1:
                all_urls.pop(index)
                urls_to_remove.pop(found_index)

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

    def on_component_input(self, ctx: OnComponentInputContext) -> Optional[str]:
        for extension in self.extensions:
            result = extension.on_component_input(ctx)
            # The extension short-circuited the rendering process to return this
            if result is not None:
                return result
        return None

    def on_component_data(self, ctx: OnComponentDataContext) -> None:
        for extension in self.extensions:
            extension.on_component_data(ctx)

    def on_component_rendered(self, ctx: OnComponentRenderedContext) -> str:
        for extension in self.extensions:
            result = extension.on_component_rendered(ctx)
            if result is not None:
                ctx = ctx._replace(result=result)
        return ctx.result


# NOTE: This is a singleton which is takes the extensions from `app_settings.EXTENSIONS`
extensions = ExtensionManager()


################################
# VIEW
################################

# Extensions can define their own URLs, which will be added to the `urlpatterns` list.
# These will be available under the `/components/ext/<extension_name>/` path, e.g.:
# `/components/ext/my_extension/path/to/route/<str:name>/<int:id>/`
urlpatterns = [
    django.urls.path("ext/", django.urls.include([])),
]

# NOTE: Normally we'd pass all the routes introduced by extensions to `django.urls.include()` and
#       `django.urls.path()` to construct the `URLResolver` objects that would take care of the rest.
#
#       However, Django's `urlpatterns` are constructed BEFORE the `ready()` hook is called,
#       and so before the extensions are ready.
#
#       As such, we lazily set the extensions' routes to the `URLResolver` object. And we use the `include()
#       and `path()` funtions above to ensure that the `URLResolver` object is created correctly.
extensions_url_resolver: URLResolver = urlpatterns[0]
