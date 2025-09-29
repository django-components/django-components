from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from weakref import ref

import django.urls
from django.template import Context, Origin, Template
from django.urls import URLPattern, URLResolver, get_resolver, get_urlconf

from django_components.app_settings import app_settings
from django_components.compat.django import routes_to_django
from django_components.util.command import ComponentCommand
from django_components.util.misc import snake_to_pascal
from django_components.util.routing import URLRoute

if TYPE_CHECKING:
    from django_components import Component
    from django_components.component_registry import ComponentRegistry
    from django_components.perfutil.component import OnComponentRenderedResult
    from django_components.slots import Slot, SlotNode, SlotResult


TCallable = TypeVar("TCallable", bound=Callable)
TClass = TypeVar("TClass", bound=Type[Any])


################################################
# HOOK TYPES
#
# This is the source of truth for what data is available in each hook.
# NOTE: These types are also used in docs generation, see `docs/scripts/reference.py`.
################################################


# Mark a class as an extension hook context so we can place these in
# a separate documentation section
def mark_extension_hook_api(cls: TClass) -> TClass:
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
    slots: Dict[str, "Slot"]
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
    # TODO_V1 - Remove `context_data`
    context_data: Dict
    """Deprecated. Use `template_data` instead. Will be removed in v1.0."""
    template_data: Dict
    """Dictionary of template data from `Component.get_template_data()`"""
    js_data: Dict
    """Dictionary of JavaScript data from `Component.get_js_data()`"""
    css_data: Dict
    """Dictionary of CSS data from `Component.get_css_data()`"""


@mark_extension_hook_api
class OnComponentRenderedContext(NamedTuple):
    component: "Component"
    """The Component instance that is being rendered"""
    component_cls: Type["Component"]
    """The Component class"""
    component_id: str
    """The unique identifier for this component instance"""
    result: Optional[str]
    """The rendered component, or `None` if rendering failed"""
    error: Optional[Exception]
    """The error that occurred during rendering, or `None` if rendering was successful"""


@mark_extension_hook_api
class OnSlotRenderedContext(NamedTuple):
    component: "Component"
    """The Component instance that contains the `{% slot %}` tag"""
    component_cls: Type["Component"]
    """The Component class that contains the `{% slot %}` tag"""
    component_id: str
    """The unique identifier for this component instance"""
    slot: "Slot"
    """The Slot instance that was rendered"""
    slot_name: str
    """The name of the `{% slot %}` tag"""
    slot_node: "SlotNode"
    """The node instance of the `{% slot %}` tag"""
    slot_is_required: bool
    """Whether the slot is required"""
    slot_is_default: bool
    """Whether the slot is default"""
    result: "SlotResult"
    """The rendered result of the slot"""


@mark_extension_hook_api
class OnTemplateLoadedContext(NamedTuple):
    component_cls: Type["Component"]
    """The Component class whose template was loaded"""
    content: str
    """The template string"""
    origin: Optional[Origin]
    """The origin of the template"""
    name: Optional[str]
    """The name of the template"""


@mark_extension_hook_api
class OnTemplateCompiledContext(NamedTuple):
    component_cls: Type["Component"]
    """The Component class whose template was loaded"""
    template: Template
    """The compiled template object"""


@mark_extension_hook_api
class OnCssLoadedContext(NamedTuple):
    component_cls: Type["Component"]
    """The Component class whose CSS was loaded"""
    content: str
    """The CSS content (string)"""


@mark_extension_hook_api
class OnJsLoadedContext(NamedTuple):
    component_cls: Type["Component"]
    """The Component class whose JS was loaded"""
    content: str
    """The JS content (string)"""


################################################
# EXTENSIONS CORE
################################################


class ExtensionComponentConfig:
    """
    `ExtensionComponentConfig` is the base class for all extension component configs.

    Extensions can define nested classes on the component class,
    such as [`Component.View`](./api.md#django_components.Component.View) or
    [`Component.Cache`](./api.md#django_components.Component.Cache):

    ```py
    class MyComp(Component):
        class View:
            def get(self, request):
                ...

        class Cache:
            ttl = 60
    ```

    This allows users to configure extension behavior per component.

    Behind the scenes, the nested classes that users define on their components
    are merged with the extension's "base" class.

    So the example above is the same as:

    ```py
    class MyComp(Component):
        class View(ViewExtension.ComponentConfig):
            def get(self, request):
                ...

        class Cache(CacheExtension.ComponentConfig):
            ttl = 60
    ```

    Where both `ViewExtension.ComponentConfig` and `CacheExtension.ComponentConfig` are
    subclasses of `ExtensionComponentConfig`.
    """

    component_cls: Type["Component"]
    """The [`Component`](./api.md#django_components.Component) class that this extension is defined on."""

    # TODO_v1 - Remove, superseded by `component_cls`
    component_class: Type["Component"]
    """The [`Component`](./api.md#django_components.Component) class that this extension is defined on."""

    @property
    def component(self) -> "Component":
        """
        When a [`Component`](./api.md#django_components.Component) is instantiated,
        also the nested extension classes (such as `Component.View`) are instantiated,
        receiving the component instance as an argument.

        This attribute holds the owner [`Component`](./api.md#django_components.Component) instance
        that this extension is defined on.
        """
        component = self._component_ref()
        if component is None:
            raise RuntimeError("Component has been garbage collected")
        return component

    def __init__(self, component: "Component") -> None:
        # NOTE: Use weak reference to avoid a circular reference between the component instance
        # and the extension class.
        self._component_ref = ref(component)


# TODO_v1 - Delete
BaseExtensionClass = ExtensionComponentConfig
"""
Deprecated. Will be removed in v1.0. Use
[`ComponentConfig`](./api.md#django_components.ExtensionComponentConfig) instead.
"""


# TODO_V1 - Delete, meta class was needed only for backwards support for ExtensionClass.
class ExtensionMeta(type):
    def __new__(mcs, name: Any, bases: Tuple, attrs: Dict) -> Any:
        # Rename `ExtensionClass` to `ComponentConfig`
        if "ExtensionClass" in attrs:
            attrs["ComponentConfig"] = attrs.pop("ExtensionClass")

        return super().__new__(mcs, name, bases, attrs)


# NOTE: This class is used for generating documentation for the extension hooks API.
#       To be recognized, all hooks must start with `on_` prefix.
class ComponentExtension(metaclass=ExtensionMeta):
    """
    Base class for all extensions.

    Read more on [Extensions](../concepts/advanced/extensions.md).

    **Example:**

    ```python
    class ExampleExtension(ComponentExtension):
        name = "example"

        # Component-level behavior and settings. User will be able to override
        # the attributes and methods defined here on the component classes.
        class ComponentConfig(ComponentExtension.ComponentConfig):
            foo = "1"
            bar = "2"

            def baz(cls):
                return "3"

        # URLs
        urls = [
            URLRoute(path="dummy-view/", handler=dummy_view, name="dummy"),
            URLRoute(path="dummy-view-2/<int:id>/<str:name>/", handler=dummy_view_2, name="dummy-2"),
        ]

        # Commands
        commands = [
            HelloWorldCommand,
        ]

        # Hooks
        def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
            print(ctx.component_cls.__name__)

        def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
            print(ctx.component_cls.__name__)
    ```

    Which users then can override on a per-component basis. E.g.:

    ```python
    class MyComp(Component):
        class Example:
            foo = "overridden"

            def baz(self):
                return "overridden baz"
    ```
    """

    ###########################
    # USER INPUT
    ###########################

    name: ClassVar[str]
    """
    Name of the extension.

    Name must be lowercase, and must be a valid Python identifier (e.g. `"my_extension"`).

    The extension may add new features to the [`Component`](./api.md#django_components.Component)
    class by allowing users to define and access a nested class in
    the [`Component`](./api.md#django_components.Component) class.

    The extension name determines the name of the nested class in
    the [`Component`](./api.md#django_components.Component) class, and the attribute
    under which the extension will be accessible.

    E.g. if the extension name is `"my_extension"`, then the nested class in
    the [`Component`](./api.md#django_components.Component) class will be
    `MyExtension`, and the extension will be accessible as `MyComp.my_extension`.

    ```python
    class MyComp(Component):
        class MyExtension:
            ...

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "my_extension": self.my_extension.do_something(),
            }
    ```

    !!! info

        The extension class name can be customized by setting
        the [`class_name`](./api.md#django_components.ComponentExtension.class_name) attribute.
    """

    class_name: ClassVar[str]
    """
    Name of the extension class.

    By default, this is set automatically at class creation. The class name is the same as
    the [`name`](./api.md#django_components.ComponentExtension.name) attribute, but with snake_case
    converted to PascalCase.

    So if the extension name is `"my_extension"`, then the extension class name will be `"MyExtension"`.

    ```python
    class MyComp(Component):
        class MyExtension:  # <--- This is the extension class
            ...
    ```

    To customize the class name, you can manually set the `class_name` attribute.

    The class name must be a valid Python identifier.

    **Example:**

    ```python
    class MyExt(ComponentExtension):
        name = "my_extension"
        class_name = "MyCustomExtension"
    ```

    This will make the extension class name `"MyCustomExtension"`.

    ```python
    class MyComp(Component):
        class MyCustomExtension:  # <--- This is the extension class
            ...
    ```
    """

    ComponentConfig: ClassVar[Type[ExtensionComponentConfig]] = ExtensionComponentConfig
    """
    Base class that the "component-level" extension config nested within
    a [`Component`](./api.md#django_components.Component) class will inherit from.

    This is where you can define new methods and attributes that will be available to the component
    instance.

    Background:

    The extension may add new features to the [`Component`](./api.md#django_components.Component) class
    by allowing users to define and access a nested class in
    the [`Component`](./api.md#django_components.Component) class. E.g.:

    ```python
    class MyComp(Component):
        class MyExtension:
            ...

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "my_extension": self.my_extension.do_something(),
            }
    ```

    When rendering a component, the nested extension class will be set as a subclass of
    `ComponentConfig`. So it will be same as if the user had directly inherited from extension's
    `ComponentConfig`. E.g.:

    ```python
    class MyComp(Component):
        class MyExtension(ComponentExtension.ComponentConfig):
            ...
    ```

    This setting decides what the extension class will inherit from.
    """

    commands: ClassVar[List[Type[ComponentCommand]]] = []
    """
    List of commands that can be run by the extension.

    These commands will be available to the user as `components ext run <extension> <command>`.

    Commands are defined as subclasses of
    [`ComponentCommand`](./extension_commands.md#django_components.ComponentCommand).

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

    urls: ClassVar[List[URLRoute]] = []

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
        Called when a new [`Component`](./api.md#django_components.Component) class is created.

        This hook is called after the [`Component`](./api.md#django_components.Component) class
        is fully defined but before it's registered.

        Use this hook to perform any initialization or validation of the
        [`Component`](./api.md#django_components.Component) class.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentClassCreatedContext

        class MyExtension(ComponentExtension):
            def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
                # Add a new attribute to the Component class
                ctx.component_cls.my_attr = "my_value"
        ```
        """

    def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
        """
        Called when a [`Component`](./api.md#django_components.Component) class is being deleted.

        This hook is called before the [`Component`](./api.md#django_components.Component) class
        is deleted from memory.

        Use this hook to perform any cleanup related to the [`Component`](./api.md#django_components.Component) class.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentClassDeletedContext

        class MyExtension(ComponentExtension):
            def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
                # Remove Component class from the extension's cache on deletion
                self.cache.pop(ctx.component_cls, None)
        ```
        """

    def on_registry_created(self, ctx: OnRegistryCreatedContext) -> None:
        """
        Called when a new [`ComponentRegistry`](./api.md#django_components.ComponentRegistry) is created.

        This hook is called after a new
        [`ComponentRegistry`](./api.md#django_components.ComponentRegistry) instance is initialized.

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

    def on_registry_deleted(self, ctx: OnRegistryDeletedContext) -> None:
        """
        Called when a [`ComponentRegistry`](./api.md#django_components.ComponentRegistry) is being deleted.

        This hook is called before
        a [`ComponentRegistry`](./api.md#django_components.ComponentRegistry) instance is deleted.

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

    def on_component_registered(self, ctx: OnComponentRegisteredContext) -> None:
        """
        Called when a [`Component`](./api.md#django_components.Component) class is
        registered with a [`ComponentRegistry`](./api.md#django_components.ComponentRegistry).

        This hook is called after a [`Component`](./api.md#django_components.Component) class
        is successfully registered.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentRegisteredContext

        class MyExtension(ComponentExtension):
            def on_component_registered(self, ctx: OnComponentRegisteredContext) -> None:
                print(f"Component {ctx.component_cls} registered to {ctx.registry} as '{ctx.name}'")
        ```
        """

    def on_component_unregistered(self, ctx: OnComponentUnregisteredContext) -> None:
        """
        Called when a [`Component`](./api.md#django_components.Component) class is
        unregistered from a [`ComponentRegistry`](./api.md#django_components.ComponentRegistry).

        This hook is called after a [`Component`](./api.md#django_components.Component) class
        is removed from the registry.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentUnregisteredContext

        class MyExtension(ComponentExtension):
            def on_component_unregistered(self, ctx: OnComponentUnregisteredContext) -> None:
                print(f"Component {ctx.component_cls} unregistered from {ctx.registry} as '{ctx.name}'")
        ```
        """

    ###########################
    # Component render hooks
    ###########################

    def on_component_input(self, ctx: OnComponentInputContext) -> Optional[str]:
        """
        Called when a [`Component`](./api.md#django_components.Component) was triggered to render,
        but before a component's context and data methods are invoked.

        Use this hook to modify or validate component inputs before they're processed.

        This is the first hook that is called when rendering a component. As such this hook is called before
        [`Component.get_template_data()`](./api.md#django_components.Component.get_template_data),
        [`Component.get_js_data()`](./api.md#django_components.Component.get_js_data),
        and [`Component.get_css_data()`](./api.md#django_components.Component.get_css_data) methods,
        and the
        [`on_component_data`](./extension_hooks.md#django_components.extension.ComponentExtension.on_component_data)
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

        !!! warning

            In this hook, the components' inputs are still mutable.

            As such, if a component defines [`Args`](./api.md#django_components.Component.Args),
            [`Kwargs`](./api.md#django_components.Component.Kwargs),
            [`Slots`](./api.md#django_components.Component.Slots) types, these types are NOT yet instantiated.

            Instead, component fields like [`Component.args`](./api.md#django_components.Component.args),
            [`Component.kwargs`](./api.md#django_components.Component.kwargs),
            [`Component.slots`](./api.md#django_components.Component.slots)
            are plain `list` / `dict` objects.
        """

    def on_component_data(self, ctx: OnComponentDataContext) -> None:
        """
        Called when a [`Component`](./api.md#django_components.Component) was triggered to render,
        after a component's context and data methods have been processed.

        This hook is called after
        [`Component.get_template_data()`](./api.md#django_components.Component.get_template_data),
        [`Component.get_js_data()`](./api.md#django_components.Component.get_js_data)
        and [`Component.get_css_data()`](./api.md#django_components.Component.get_css_data).

        This hook runs after [`on_component_input`](./api.md#django_components.ComponentExtension.on_component_input).

        Use this hook to modify or validate the component's data before rendering.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnComponentDataContext

        class MyExtension(ComponentExtension):
            def on_component_data(self, ctx: OnComponentDataContext) -> None:
                # Add extra template variable to all components when they are rendered
                ctx.template_data["my_template_var"] = "my_value"
        ```
        """

    def on_component_rendered(self, ctx: OnComponentRenderedContext) -> Optional[str]:
        """
        Called when a [`Component`](./api.md#django_components.Component) was rendered, including
        all its child components.

        Use this hook to access or post-process the component's rendered output.

        This hook works similarly to
        [`Component.on_render_after()`](./api.md#django_components.Component.on_render_after):

        1. To modify the output, return a new string from this hook. The original output or error will be ignored.

        2. To cause this component to return a new error, raise that error. The original output and error
            will be ignored.

        3. If you neither raise nor return string, the original output or error will be used.

        **Examples:**

        Change the final output of a component:

        ```python
        from django_components import ComponentExtension, OnComponentRenderedContext

        class MyExtension(ComponentExtension):
            def on_component_rendered(self, ctx: OnComponentRenderedContext) -> Optional[str]:
                # Append a comment to the component's rendered output
                return ctx.result + "<!-- MyExtension comment -->"
        ```

        Cause the component to raise a new exception:

        ```python
        from django_components import ComponentExtension, OnComponentRenderedContext

        class MyExtension(ComponentExtension):
            def on_component_rendered(self, ctx: OnComponentRenderedContext) -> Optional[str]:
                # Raise a new exception
                raise Exception("Error message")
        ```

        Return nothing (or `None`) to handle the result as usual:

        ```python
        from django_components import ComponentExtension, OnComponentRenderedContext

        class MyExtension(ComponentExtension):
            def on_component_rendered(self, ctx: OnComponentRenderedContext) -> Optional[str]:
                if ctx.error is not None:
                    # The component raised an exception
                    print(f"Error: {ctx.error}")
                else:
                    # The component rendered successfully
                    print(f"Result: {ctx.result}")
        ```
        """

    ##########################
    # Template / JS / CSS hooks
    ##########################

    def on_template_loaded(self, ctx: OnTemplateLoadedContext) -> Optional[str]:
        """
        Called when a Component's template is loaded as a string.

        This hook runs only once per [`Component`](./api.md#django_components.Component) class and works for both
        [`Component.template`](./api.md#django_components.Component.template) and
        [`Component.template_file`](./api.md#django_components.Component.template_file).

        Use this hook to read or modify the template before it's compiled.

        To modify the template, return a new string from this hook.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnTemplateLoadedContext

        class MyExtension(ComponentExtension):
            def on_template_loaded(self, ctx: OnTemplateLoadedContext) -> Optional[str]:
                # Modify the template
                return ctx.content.replace("Hello", "Hi")
        ```
        """

    def on_template_compiled(self, ctx: OnTemplateCompiledContext) -> None:
        """
        Called when a Component's template is compiled
        into a [`Template`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template) object.

        This hook runs only once per [`Component`](./api.md#django_components.Component) class and works for both
        [`Component.template`](./api.md#django_components.Component.template) and
        [`Component.template_file`](./api.md#django_components.Component.template_file).

        Use this hook to read or modify the template (in-place) after it's compiled.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnTemplateCompiledContext

        class MyExtension(ComponentExtension):
            def on_template_compiled(self, ctx: OnTemplateCompiledContext) -> None:
                print(f"Template origin: {ctx.template.origin.name}")
        ```
        """

    def on_css_loaded(self, ctx: OnCssLoadedContext) -> Optional[str]:
        """
        Called when a Component's CSS is loaded as a string.

        This hook runs only once per [`Component`](./api.md#django_components.Component) class and works for both
        [`Component.css`](./api.md#django_components.Component.css) and
        [`Component.css_file`](./api.md#django_components.Component.css_file).

        Use this hook to read or modify the CSS.

        To modify the CSS, return a new string from this hook.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnCssLoadedContext

        class MyExtension(ComponentExtension):
            def on_css_loaded(self, ctx: OnCssLoadedContext) -> Optional[str]:
                # Modify the CSS
                return ctx.content.replace("Hello", "Hi")
        ```
        """

    def on_js_loaded(self, ctx: OnJsLoadedContext) -> Optional[str]:
        """
        Called when a Component's JS is loaded as a string.

        This hook runs only once per [`Component`](./api.md#django_components.Component) class and works for both
        [`Component.js`](./api.md#django_components.Component.js) and
        [`Component.js_file`](./api.md#django_components.Component.js_file).

        Use this hook to read or modify the JS.

        To modify the JS, return a new string from this hook.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnCssLoadedContext

        class MyExtension(ComponentExtension):
            def on_js_loaded(self, ctx: OnJsLoadedContext) -> Optional[str]:
                # Modify the JS
                return ctx.content.replace("Hello", "Hi")
        ```
        """

    ##########################
    # Tags lifecycle hooks
    ##########################

    def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
        """
        Called when a [`{% slot %}`](./template_tags.md#slot) tag was rendered.

        Use this hook to access or post-process the slot's rendered output.

        To modify the output, return a new string from this hook.

        **Example:**

        ```python
        from django_components import ComponentExtension, OnSlotRenderedContext

        class MyExtension(ComponentExtension):
            def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
                # Append a comment to the slot's rendered output
                return ctx.result + "<!-- MyExtension comment -->"
        ```

        **Access slot metadata:**

        You can access the [`{% slot %}` tag](./template_tags.md#slot)
        node ([`SlotNode`](./api.md#django_components.SlotNode)) and its metadata using `ctx.slot_node`.

        For example, to find the [`Component`](./api.md#django_components.Component) class to which
        belongs the template where the [`{% slot %}`](./template_tags.md#slot) tag is defined, you can use
        [`ctx.slot_node.template_component`](./api.md#django_components.SlotNode.template_component):

        ```python
        from django_components import ComponentExtension, OnSlotRenderedContext

        class MyExtension(ComponentExtension):
            def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
                # Access slot metadata
                slot_node = ctx.slot_node
                slot_owner = slot_node.template_component
                print(f"Slot owner: {slot_owner}")
        ```
        """


# Decorator to store events in `ExtensionManager._events` when django_components is not yet initialized.
def store_events(func: TCallable) -> TCallable:
    fn_name = func.__name__

    @wraps(func)
    def wrapper(self: "ExtensionManager", ctx: Any) -> Any:
        if not self._initialized:
            self._events.append((fn_name, ctx))
            return None

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

            # If a Component class has a nested extension class, e.g.
            # ```python
            # class MyComp(Component):
            #     class MyExtension:
            #         ...
            # ```
            # then create a dummy class to make `MyComp.MyExtension` extend
            # the base class `extension.ComponentConfig`.
            #
            # So it will be same as if the user had directly inherited from `extension.ComponentConfig`.
            # ```python
            # class MyComp(Component):
            #     class MyExtension(MyExtension.ComponentConfig):
            #         ...
            # ```
            component_ext_subclass = getattr(component_cls, ext_class_name, None)

            # Add escape hatch, so that user can override the extension class
            # from within the component class. E.g.:
            # ```python
            # class MyExtDifferentButStillSame(MyExtension.ComponentConfig):
            #     ...
            #
            # class MyComp(Component):
            #     my_extension_class = MyExtDifferentButStillSame
            #     class MyExtension:
            #         ...
            # ```
            #
            # Will be effectively the same as:
            # ```python
            # class MyComp(Component):
            #     class MyExtension(MyExtDifferentButStillSame):
            #         ...
            # ```
            ext_class_override_attr = extension.name + "_class"  # "my_extension_class"
            ext_base_class = getattr(component_cls, ext_class_override_attr, extension.ComponentConfig)

            # Extensions have 3 levels of configuration:
            # 1. Factory defaults - The values that the extension author set on the extension class
            # 2. User global defaults with `COMPONENTS.extensions_defaults`
            # 3. User component-level settings - The values that the user set on the component class
            #
            # The component-level settings override the global defaults, which in turn override
            # the factory defaults.
            #
            # To apply these defaults, we set them as bases for our new extension class.
            #
            # The final class will look like this:
            # ```
            # class MyExtension(MyComp.MyExtension, MyExtensionDefaults, MyExtensionBase):
            #     component_cls = MyComp
            #     ...
            # ```
            # Where:
            # - `MyComp.MyExtension` is the extension class that the user defined on the component class.
            # - `MyExtensionDefaults` is a dummy class that holds the extension defaults from settings.
            # - `MyExtensionBase` is the base class that the extension class inherits from.
            bases_list = [ext_base_class]

            all_extensions_defaults = app_settings.EXTENSIONS_DEFAULTS or {}
            extension_defaults = all_extensions_defaults.get(extension.name, None)
            if extension_defaults:
                # Create dummy class that holds the extension defaults
                defaults_class = type(f"{ext_class_name}Defaults", (), extension_defaults.copy())
                bases_list.insert(0, defaults_class)

            if component_ext_subclass:
                bases_list.insert(0, component_ext_subclass)

            bases: Tuple[Type, ...] = tuple(bases_list)

            # Allow component-level extension class to access the owner `Component` class that via
            # `component_cls`.
            component_ext_subclass = type(
                ext_class_name,
                bases,
                # TODO_v1 - Remove `component_class`, superseded by `component_cls`
                {"component_cls": component_cls, "component_class": component_cls},
            )

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

        # Populate the `urlpatterns` with URLs specified by the extensions
        # TODO_V3 - Django-specific logic - replace with hook
        urls: List[URLResolver] = []
        seen_names: Set[str] = set()

        from django_components import Component  # noqa: PLC0415

        for extension in self.extensions:
            # Ensure that the extension name won't conflict with existing Component class API
            if hasattr(Component, extension.name) or hasattr(Component, extension.class_name):
                raise ValueError(f"Extension name '{extension.name}' conflicts with existing Component class API")

            if extension.name.lower() in seen_names:
                raise ValueError(f"Multiple extensions cannot have the same name '{extension.name}'")

            seen_names.add(extension.name.lower())

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

        # Flush stored events
        #
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

    def on_component_rendered(
        self,
        ctx: OnComponentRenderedContext,
    ) -> Optional["OnComponentRenderedResult"]:
        for extension in self.extensions:
            try:
                result = extension.on_component_rendered(ctx)
            except Exception as error:  # noqa: BLE001
                # Error from `on_component_rendered()` - clear HTML and set error
                ctx = ctx._replace(result=None, error=error)
            else:
                # No error from `on_component_rendered()` - set HTML and clear error
                if result is not None:
                    ctx = ctx._replace(result=result, error=None)
        return ctx.result, ctx.error

    ##########################
    # Template / JS / CSS hooks
    ##########################

    def on_template_loaded(self, ctx: OnTemplateLoadedContext) -> str:
        for extension in self.extensions:
            content = extension.on_template_loaded(ctx)
            if content is not None:
                ctx = ctx._replace(content=content)
        return ctx.content

    def on_template_compiled(self, ctx: OnTemplateCompiledContext) -> None:
        for extension in self.extensions:
            extension.on_template_compiled(ctx)

    def on_css_loaded(self, ctx: OnCssLoadedContext) -> str:
        for extension in self.extensions:
            content = extension.on_css_loaded(ctx)
            if content is not None:
                ctx = ctx._replace(content=content)
        return ctx.content

    def on_js_loaded(self, ctx: OnJsLoadedContext) -> str:
        for extension in self.extensions:
            content = extension.on_js_loaded(ctx)
            if content is not None:
                ctx = ctx._replace(content=content)
        return ctx.content

    def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
        for extension in self.extensions:
            result = extension.on_slot_rendered(ctx)
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
