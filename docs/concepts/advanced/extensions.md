_New in version 0.131_

Django-components functionality can be extended with "extensions". Extensions allow for powerful customization and integrations. They can:

- Tap into lifecycle events, such as when a component is created, deleted, registered, or unregistered.
- Add new attributes and methods to the components under an extension-specific nested class.
- Define custom commands that can be executed via the Django management command interface.

## Live examples

- [djc-ext-pydantic](https://github.com/django-components/djc-ext-pydantic)

## Setting up extensions

Extensions are configured in the Django settings under [`COMPONENTS.extensions`](../../../reference/settings#django_components.app_settings.ComponentsSettings.extensions).

Extensions can be set by either as an import string or by passing in a class:

```python
# settings.py

class MyExtension(ComponentExtension):
    name = "my_extension"

    class ExtensionClass(ComponentExtension.ExtensionClass):
        ...

COMPONENTS = ComponentsSettings(
    extensions=[
        MyExtension,
        "another_app.extensions.AnotherExtension",
        "my_app.extensions.ThirdExtension",
    ],
)
```

## Lifecycle hooks

Extensions can define methods to hook into lifecycle events, such as:

- Component creation or deletion
- Un/registering a component
- Creating or deleting a registry
- Pre-processing data passed to a component on render
- Post-processing data returned from [`get_template_data()`](../../../reference/api#django_components.Component.get_template_data)
  and others.

See the full list in [Extension Hooks Reference](../../../reference/extension_hooks).

## Configuring extensions per component

Each extension has a corresponding nested class within the [`Component`](../../../reference/api#django_components.Component) class. These allow
to configure the extensions on a per-component basis.

E.g.:

- `"view"` extension -> [`Component.View`](../../../reference/api#django_components.Component.View)
- `"cache"` extension -> [`Component.Cache`](../../../reference/api#django_components.Component.Cache)
- `"defaults"` extension -> [`Component.Defaults`](../../../reference/api#django_components.Component.Defaults)

!!! note

    **Accessing the component instance from inside the nested classes:**

    Each method of the nested classes has access to the `component` attribute,
    which points to the component instance.

    ```python
    class MyTable(Component):
        class MyExtension:
            def get(self, request):
                # `self.component` points to the instance of `MyTable` Component.
                return self.component.render_to_response(request=request)
    ```

### Example: Component as View

The [Components as Views](../../fundamentals/component_views_urls) feature is actually implemented as an extension
that is configured by a `View` nested class.

You can override the `get()`, `post()`, etc methods to customize the behavior of the component as a view:

```python
class MyTable(Component):
    class View:
        def get(self, request):
            # TO BE IMPLEMENTED BY USER
            # return self.component_cls.render_to_response(request=request)
            raise NotImplementedError("You must implement the `get` method.")

        def post(self, request):
            # TO BE IMPLEMENTED BY USER
            # return self.component_cls.render_to_response(request=request)
            raise NotImplementedError("You must implement the `post` method.")

        ...
```

### Example: Storybook integration

The Storybook integration (work in progress) is an extension that is configured by a `Storybook` nested class.

You can override methods such as `title`, `parameters`, etc, to customize how to generate a Storybook
JSON file from the component.

```python
class MyTable(Component):
    class Storybook:
        def title(self):
            return self.component_cls.__name__

        def parameters(self) -> Parameters:
            return {
                "server": {
                    "id": self.component_cls.__name__,
                }
            }

        def stories(self) -> List[StoryAnnotations]:
            return []

        ...
```

## Accessing extensions in components

Above, we've configured extensions `View` and `Storybook` for the `MyTable` component.

You can access the instances of these extension classes in the component instance.

For example, the View extension is available as `self.view`:

```python
class MyTable(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # `self.view` points to the instance of `View` extension.
        return {
            "view": self.view,
        }
```

And the Storybook extension is available as `self.storybook`:

```python
class MyTable(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # `self.storybook` points to the instance of `Storybook` extension.
        return {
            "title": self.storybook.title(),
        }
```

Thus, you can use extensions to add methods or attributes that will be available to all components
in their component context.

## Writing extensions

Creating extensions in django-components involves defining a class that inherits from
[`ComponentExtension`](../../../reference/api/#django_components.ComponentExtension).
This class can implement various lifecycle hooks and define new attributes or methods to be added to components.

### Defining an extension

To create an extension, define a class that inherits from [`ComponentExtension`](../../../reference/api/#django_components.ComponentExtension)
and implement the desired hooks.

- Each extension MUST have a `name` attribute. The name MUST be a valid Python identifier.
- The extension MAY implement any of the [hook methods](../../../reference/extension_hooks).
- Each hook method receives a context object with relevant data.

```python
from django_components.extension import ComponentExtension, OnComponentClassCreatedContext

class MyExtension(ComponentExtension):
    name = "my_extension"

    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        # Custom logic for when a component class is created
        ctx.component_cls.my_attr = "my_value"
```

!!! warning

    The `name` attribute MUST be unique across all extensions.

    Moreover, the `name` attribute MUST NOT conflict with existing Component class API.

    So if you name an extension `render`, it will conflict with the [`render()`](../../../reference/api/#django_components.Component.render) method of the `Component` class.

### Defining the extension class

In previous sections we've seen the `View` and `Storybook` extensions classes that were nested within the `Component` class:

```python
class MyComponent(Component):
    class View:
        ...

    class Storybook:
        ...
```

These can be understood as component-specific overrides or configuration.

The nested extension classes like `View` or `Storybook` will actually subclass from a base extension
class as defined on the [`ComponentExtension.ExtensionClass`](../../../reference/api/#django_components.ComponentExtension.ExtensionClass).

This is how extensions define the "default" behavior of their nested extension classes.

For example, the `View` base extension class defines the handlers for GET, POST, etc:

```python
from django_components.extension import ComponentExtension

class ViewExtension(ComponentExtension):
    name = "view"

    # The default behavior of the `View` extension class.
    class ExtensionClass(ComponentExtension.ExtensionClass):
        def get(self, request):
            # TO BE IMPLEMENTED BY USER
            # return self.component_cls.render_to_response(request=request)
            raise NotImplementedError("You must implement the `get` method.")

        def post(self, request):
            # TO BE IMPLEMENTED BY USER
            # return self.component_cls.render_to_response(request=request)
            raise NotImplementedError("You must implement the `post` method.")

        ...
```

In any component that then defines a nested `View` extension class, the `View` extension class will actually
subclass from the `ViewExtension.ExtensionClass` class.

In other words, when you define a component like this:

```python
class MyTable(Component):
    class View:
        def get(self, request):
            # Do something
            ...
```

It will actually be implemented as if the `View` class subclassed from base class `ViewExtension.ExtensionClass`:

```python
class MyTable(Component):
    class View(ViewExtension.ExtensionClass):
        def get(self, request):
            # Do something
            ...
```

!!! warning

    When writing an extension, the `ExtensionClass` MUST subclass the base class [`ComponentExtension.ExtensionClass`](../../../reference/api/#django_components.ComponentExtension.ExtensionClass).

    This base class ensures that the extension class will have access to the component instance.

### Registering extensions

Once the extension is defined, it needs to be registered in the Django settings to be used by the application.

Extensions can be given either as an extension class, or its import string:

```python
# settings.py
COMPONENTS = {
    "extensions": [
        "my_app.extensions.MyExtension",
    ],
}
```

Or by reference:

```python
# settings.py
from my_app.extensions import MyExtension

COMPONENTS = {
    "extensions": [
        MyExtension,
    ],
}
```

### Full example: Custom logging extension

To tie it all together, here's an example of a custom logging extension that logs when components are created, deleted, or rendered:

- Each component can specify which color to use for the logging by setting `Component.ColorLogger.color`.
- The extension will log the component name and color when the component is created, deleted, or rendered.

```python
from django_components.extension import (
    ComponentExtension,
    OnComponentClassCreatedContext,
    OnComponentClassDeletedContext,
    OnComponentInputContext,
)

class ColorLoggerExtensionClass(ComponentExtension.ExtensionClass):
    color: str


class ColorLoggerExtension(ComponentExtension):
    name = "color_logger"

    # All `Component.ColorLogger` classes will inherit from this class.
    ExtensionClass = ColorLoggerExtensionClass

    # These hooks don't have access to the Component instance, only to the Component class,
    # so we access the color as `Component.ColorLogger.color`.
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        log.info(
            f"Component {ctx.component_cls} created.",
            color=ctx.component_cls.ColorLogger.color,
        )

    def on_component_class_deleted(self, ctx: OnComponentClassDeletedContext) -> None:
        log.info(
            f"Component {ctx.component_cls} deleted.",
            color=ctx.component_cls.ColorLogger.color,
        )

    # This hook has access to the Component instance, so we access the color
    # as `self.component.color_logger.color`.
    def on_component_input(self, ctx: OnComponentInputContext) -> None:
        log.info(
            f"Rendering component {ctx.component_cls}.",
            color=ctx.component.color_logger.color,
        )
```

To use the `ColorLoggerExtension`, add it to your settings:

```python
# settings.py
COMPONENTS = {
    "extensions": [
        ColorLoggerExtension,
    ],
}
```

Once registered, in any component, you can define a `ColorLogger` attribute:

```python
class MyComponent(Component):
    class ColorLogger:
        color = "red"
```

This will log the component name and color when the component is created, deleted, or rendered.

### Utility functions

django-components provides a few utility functions to help with writing extensions:

- [`all_components()`](../../../reference/api#django_components.all_components) - returns a list of all created component classes.
- [`all_registries()`](../../../reference/api#django_components.all_registries) - returns a list of all created registry instances.

### Accessing the component class from within an extension

When you are writing the extension class that will be nested inside a Component class, e.g.

```py
class MyTable(Component):
    class MyExtension:
        def some_method(self):
            ...
```

You can access the owner Component class (`MyTable`) from within methods of the extension class (`MyExtension`) by using the `component_class` attribute:

```py
class MyTable(Component):
    class MyExtension:
        def some_method(self):
            print(self.component_class)
```

Here is how the `component_class` attribute may be used with our `ColorLogger`
extension shown above:

```python
class ColorLoggerExtensionClass(ComponentExtension.ExtensionClass):
    color: str

    def log(self, msg: str) -> None:
        print(f"{self.component_class.name}: {msg}")


class ColorLoggerExtension(ComponentExtension):
    name = "color_logger"

    # All `Component.ColorLogger` classes will inherit from this class.
    ExtensionClass = ColorLoggerExtensionClass
```

### Pass slot metadata

When a slot is passed to a component, it is copied, so that the original slot is not modified
with rendering metadata.

Therefore, don't use slot's identity to associate metadata with the slot:

```py
# ❌ Don't do this:
slots_cache = {}

class LoggerExtension(ComponentExtension):
    name = "logger"

    def on_component_input(self, ctx: OnComponentInputContext):
        for slot in ctx.component.slots.values():
            slots_cache[id(slot)] = {"some": "metadata"}
```

Instead, use the [`Slot.extra`](../../../reference/api#django_components.Slot.extra) attribute,
which is copied from the original slot:

```python
# ✅ Do this:
class LoggerExtension(ComponentExtension):
    name = "logger"

    # Save component-level logger settings for each slot when a component is rendered.
    def on_component_input(self, ctx: OnComponentInputContext):
        for slot in ctx.component.slots.values():
            slot.extra["logger"] = ctx.component.logger

    # Then, when a fill is rendered with `{% slot %}`, we can access the logger settings
    # from the slot's metadata.
    def on_slot_rendered(self, ctx: OnSlotRenderedContext):
        logger = ctx.slot.extra["logger"]
        logger.log(...)
```

## Extension commands

Extensions in django-components can define custom commands that can be executed via the Django management command interface. This allows for powerful automation and customization capabilities.

For example, if you have an extension that defines a command that prints "Hello world", you can run the command with:

```bash
python manage.py components ext run my_ext hello
```

Where:

- `python manage.py components` - is the Django entrypoint
- `ext run` - is the subcommand to run extension commands
- `my_ext` - is the extension name
- `hello` - is the command name

### Defining Commands

To define a command, subclass from [`ComponentCommand`](../../../reference/extension_commands#django_components.ComponentCommand).
This subclass should define:

- `name` - the command's name
- `help` - the command's help text
- `handle` - the logic to execute when the command is run

```python
from django_components import ComponentCommand, ComponentExtension

class HelloCommand(ComponentCommand):
    name = "hello"
    help = "Say hello"

    def handle(self, *args, **kwargs):
        print("Hello, world!")

class MyExt(ComponentExtension):
    name = "my_ext"
    commands = [HelloCommand]
```

### Defining Command Arguments and Options

Commands can accept positional arguments and options (e.g. `--foo`), which are defined using the
[`arguments`](../../../reference/extension_commands#django_components.ComponentCommand.arguments)
attribute of the [`ComponentCommand`](../../../reference/extension_commands#django_components.ComponentCommand) class.

The arguments are parsed with [`argparse`](https://docs.python.org/3/library/argparse.html)
into a dictionary of arguments and options. These are then available
as keyword arguments to the [`handle`](../../../reference/extension_commands#django_components.ComponentCommand.handle)
method of the command.

```python
from django_components import CommandArg, ComponentCommand, ComponentExtension

class HelloCommand(ComponentCommand):
    name = "hello"
    help = "Say hello"

    arguments = [
        # Positional argument
        CommandArg(
            name_or_flags="name",
            help="The name to say hello to",
        ),
        # Optional argument
        CommandArg(
            name_or_flags=["--shout", "-s"],
            action="store_true",
            help="Shout the hello",
        ),
    ]

    def handle(self, name: str, *args, **kwargs):
        shout = kwargs.get("shout", False)
        msg = f"Hello, {name}!"
        if shout:
            msg = msg.upper()
        print(msg)
```

You can run the command with arguments and options:

```bash
python manage.py components ext run my_ext hello John --shout
>>> HELLO, JOHN!
```

!!! note

    Command definitions are parsed with `argparse`, so you can use all the features of `argparse` to define your arguments and options.

    See the [argparse documentation](https://docs.python.org/3/library/argparse.html) for more information.

    django-components defines types as
    [`CommandArg`](../../../reference/extension_commands#django_components.CommandArg),
    [`CommandArgGroup`](../../../reference/extension_commands#django_components.CommandArgGroup),
    [`CommandSubcommand`](../../../reference/extension_commands#django_components.CommandSubcommand),
    and [`CommandParserInput`](../../../reference/extension_commands#django_components.CommandParserInput)
    to help with type checking.

!!! note

    If a command doesn't have the [`handle`](../../../reference/extension_commands#django_components.ComponentCommand.handle)
    method defined, the command will print a help message and exit.

### Grouping Arguments

Arguments can be grouped using [`CommandArgGroup`](../../../reference/extension_commands#django_components.CommandArgGroup)
to provide better organization and help messages.

Read more on [argparse argument groups](https://docs.python.org/3/library/argparse.html#argument-groups).

```python
from django_components import CommandArg, CommandArgGroup, ComponentCommand, ComponentExtension

class HelloCommand(ComponentCommand):
    name = "hello"
    help = "Say hello"

    # Argument parsing is managed by `argparse`.
    arguments = [
        # Positional argument
        CommandArg(
            name_or_flags="name",
            help="The name to say hello to",
        ),
        # Optional argument
        CommandArg(
            name_or_flags=["--shout", "-s"],
            action="store_true",
            help="Shout the hello",
        ),
        # When printing the command help message, `--bar` and `--baz`
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

    def handle(self, name: str, *args, **kwargs):
        shout = kwargs.get("shout", False)
        msg = f"Hello, {name}!"
        if shout:
            msg = msg.upper()
        print(msg)
```

### Subcommands

Extensions can define subcommands, allowing for more complex command structures.

Subcommands are defined similarly to root commands, as subclasses of
[`ComponentCommand`](../../../reference/extension_commands#django_components.ComponentCommand) class.

However, instead of defining the subcommands in the
[`commands`](../../../reference/extension_commands#django_components.ComponentExtension.commands)
attribute of the extension, you define them in the
[`subcommands`](../../../reference/extension_commands#django_components.ComponentCommand.subcommands)
attribute of the parent command:

```python
from django_components import CommandArg, CommandArgGroup, ComponentCommand, ComponentExtension

class ChildCommand(ComponentCommand):
    name = "child"
    help = "Child command"

    def handle(self, *args, **kwargs):
        print("Child command")

class ParentCommand(ComponentCommand):
    name = "parent"
    help = "Parent command"
    subcommands = [
        ChildCommand,
    ]

    def handle(self, *args, **kwargs):
        print("Parent command")
```

In this example, we can run two commands.

Either the parent command:

```bash
python manage.py components ext run parent
>>> Parent command
```

Or the child command:

```bash
python manage.py components ext run parent child
>>> Child command
```

!!! warning

    Subcommands are independent of the parent command. When a subcommand runs, the parent command is NOT executed.

    As such, if you want to pass arguments to both the parent and child commands, e.g.:

    ```bash
    python manage.py components ext run parent --foo child --bar
    ```

    You should instead pass all the arguments to the subcommand:

    ```bash
    python manage.py components ext run parent child --foo --bar
    ```

### Print command help

By default, all commands will print their help message when run with the `--help` / `-h` flag.

```bash
python manage.py components ext run my_ext --help
```

The help message prints out all the arguments and options available for the command, as well as any subcommands.

### Testing Commands

Commands can be tested using Django's [`call_command()`](https://docs.djangoproject.com/en/5.2/ref/django-admin/#running-management-commands-from-your-code)
function, which allows you to simulate running the command in tests.

```python
from django.core.management import call_command

call_command('components', 'ext', 'run', 'my_ext', 'hello', '--name', 'John')
```

To capture the output of the command, you can use the [`StringIO`](https://docs.python.org/3/library/io.html#io.StringIO)
module to redirect the output to a string:

```python
from io import StringIO

out = StringIO()
with patch("sys.stdout", new=out):
    call_command('components', 'ext', 'run', 'my_ext', 'hello', '--name', 'John')
output = out.getvalue()
```

And to temporarily set the extensions, you can use the [`@djc_test`](../../../reference/testing_api#djc_test) decorator.

Thus, a full test example can then look like this:

```python
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django_components.testing import djc_test

@djc_test(
    components_settings={
        "extensions": [
            "my_app.extensions.MyExtension",
        ],
    },
)
def test_hello_command(self):
    out = StringIO()
    with patch("sys.stdout", new=out):
        call_command('components', 'ext', 'run', 'my_ext', 'hello', '--name', 'John')
    output = out.getvalue()
    assert output == "Hello, John!\n"
```

## Extension URLs

Extensions can define custom views and endpoints that can be accessed through the Django application.

To define URLs for an extension, set them in the [`urls`](../../../reference/api#django_components.ComponentExtension.urls) attribute of your [`ComponentExtension`](../../../reference/api#django_components.ComponentExtension) class. Each URL is defined using the [`URLRoute`](../../../reference/extension_urls#django_components.URLRoute) class, which specifies the path, handler, and optional name for the route.

Here's an example of how to define URLs within an extension:

```python
from django_components.extension import ComponentExtension, URLRoute
from django.http import HttpResponse

def my_view(request):
    return HttpResponse("Hello from my extension!")

class MyExtension(ComponentExtension):
    name = "my_extension"

    urls = [
        URLRoute(path="my-view/", handler=my_view, name="my_view"),
        URLRoute(path="another-view/<int:id>/", handler=my_view, name="another_view"),
    ]
```

!!! warning

    The [`URLRoute`](../../../reference/extension_urls#django_components.URLRoute) objects
    are different from objects created with Django's
    [`django.urls.path()`](https://docs.djangoproject.com/en/5.2/ref/urls/#path).
    Do NOT use `URLRoute` objects in Django's [`urlpatterns`](https://docs.djangoproject.com/en/5.2/topics/http/urls/#example)
    and vice versa!

    django-components uses a custom [`URLRoute`](../../../reference/extension_urls#django_components.URLRoute) class to define framework-agnostic routing rules.

    As of v0.131, `URLRoute` objects are directly converted to Django's `URLPattern` and `URLResolver` objects.

### Accessing Extension URLs

The URLs defined in an extension are available under the path

```
/components/ext/<extension_name>/
```

For example, if you have defined a URL with the path `my-view/<str:name>/` in an extension named `my_extension`, it can be accessed at:

```
/components/ext/my_extension/my-view/john/
```

### Nested URLs

Extensions can also define nested URLs to allow for more complex routing structures.

To define nested URLs, set the [`children`](../../../reference/extension_urls#django_components.URLRoute.children)
attribute of the [`URLRoute`](../../../reference/extension_urls#django_components.URLRoute) object to
a list of child [`URLRoute`](../../../reference/extension_urls#django_components.URLRoute) objects:

```python
class MyExtension(ComponentExtension):
    name = "my_extension"

    urls = [
        URLRoute(
            path="parent/",
            name="parent_view",
            children=[
                URLRoute(path="child/<str:name>/", handler=my_view, name="child_view"),
            ],
        ),
    ]
```

In this example, the URL

```
/components/ext/my_extension/parent/child/john/
```

would call the `my_view` handler with the parameter `name` set to `"John"`.

### Passing kwargs and other extra fields to URL routes

The [`URLRoute`](../../../reference/extension_urls#django_components.URLRoute) class is framework-agnostic,
so that extensions could be used with non-Django frameworks in the future.

However, that means that there may be some extra fields that Django's
[`django.urls.path()`](https://docs.djangoproject.com/en/5.2/ref/urls/#path)
accepts, but which are not defined on the `URLRoute` object.

To address this, the [`URLRoute`](../../../reference/extension_urls#django_components.URLRoute) object has
an [`extra`](../../../reference/extension_urls#django_components.URLRoute.extra) attribute,
which is a dictionary that can be used to pass any extra kwargs to `django.urls.path()`:

```python
URLRoute(
    path="my-view/<str:name>/",
    handler=my_view,
    name="my_view",
    extra={"kwargs": {"foo": "bar"} },
)
```

Is the same as:

```python
django.urls.path(
    "my-view/<str:name>/",
    view=my_view,
    name="my_view",
    kwargs={"foo": "bar"},
)
```

because `URLRoute` is converted to Django's route like so:

```python
django.urls.path(
    route.path,
    view=route.handler,
    name=route.name,
    **route.extra,
)
```
