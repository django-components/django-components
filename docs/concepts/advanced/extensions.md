_New in version 0.131_

Django-components functionality can be extended with "extensions". Extensions allow for powerful customization and integrations. They can:

- Tap into lifecycle events, such as when a component is created, deleted, registered, or unregistered.
- Add new attributes and methods to the components under an extension-specific nested class.

## Setting up extensions

Extensions are configured in the Django settings under [`COMPONENTS.extensions`](../../../reference/settings#django_components.app_settings.ComponentsSettings.extensions).

Extensions can be set by either as an import string or by passing in a class:

```python
# settings.py

class MyExtension(ComponentsExtension):
    name = "my_extension"

    class ExtensionClass(BaseExtensionClass):
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
- Post-processing data returned from [`get_context_data()`](../../../reference/api#django_components.Component.get_context_data)
  and others.

See the full list in [Extension Hooks Reference](../../../reference/extension_hooks).

## Configuring extensions per component

Each extension has a corresponding nested class within the [`Component`](../../../reference/api#django_components.Component) class. These allow
to configure the extensions on a per-component basis.

!!! note

    **Accessing the component instance from inside the nested classes:**

    Each method of the nested classes has access to the `component` attribute,
    which points to the component instance.

    ```python
    class MyTable(Component):
        class View:
            def get(self, request):
                # `self.component` points to the instance of `MyTable` Component.
                return self.component.get(request)
    ```

### Example: Component as View

The [Components as Views](../../fundamentals/components_as_views) feature is actually implemented as an extension
that is configured by a `View` nested class.

You can override the `get`, `post`, etc methods to customize the behavior of the component as a view:

```python
class MyTable(Component):
    class View:
        def get(self, request):
            return self.component.get(request)

        def post(self, request):
            return self.component.post(request)

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
            return self.component.__class__.__name__

        def parameters(self) -> Parameters:
            return {
                "server": {
                    "id": self.component.__class__.__name__,
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
    def get_context_data(self, request):
        # `self.view` points to the instance of `View` extension.
        return {
            "view": self.view,
        }
```

And the Storybook extension is available as `self.storybook`:

```python
class MyTable(Component):
    def get_context_data(self, request):
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
from django_components.extension import ComponentExtension, BaseExtensionClass

class ViewExtension(ComponentExtension):
    name = "view"

    # The default behavior of the `View` extension class.
    class ExtensionClass(BaseExtensionClass):
        def get(self, request):
            return self.component.get(request)

        def post(self, request):
            return self.component.post(request)

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

    When writing an extension, the `ExtensionClass` MUST subclass the base class [`BaseExtensionClass`](../../../reference/api/#django_components.ComponentExtension.BaseExtensionClass).

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

class ColorLoggerExtensionClass(BaseExtensionClass):
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
