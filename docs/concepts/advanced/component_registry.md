In previous examples you could repeatedly see us using `@register()` to "register"
the components. In this section we dive deeper into what it actually means and how you can
manage (add or remove) components.

As a reminder, we may have a component like this:

```python
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "template.html"

    # This component takes one parameter, a date string to show in the template
    def get_context_data(self, date):
        return {
            "date": date,
        }
```

which we then render in the template as:

```django
{% component "calendar" date="1970-01-01" %}
{% endcomponent %}
```

As you can see, `@register` links up the component class
with the `{% component %}` template tag. So when the template tag comes across
a component called `"calendar"`, it can look up it's class and instantiate it.

## What is ComponentRegistry

The `@register` decorator is a shortcut for working with the `ComponentRegistry`.

`ComponentRegistry` manages which components can be used in the template tags.

Each `ComponentRegistry` instance is associated with an instance
of Django's `Library`. And Libraries are inserted into Django template
using the `{% load %}` tags.

The `@register` decorator accepts an optional kwarg `registry`, which specifies, the `ComponentRegistry` to register components into.
If omitted, the default `ComponentRegistry` instance defined in django_components is used.

```py
my_registry = ComponentRegistry()

@register(registry=my_registry)
class MyComponent(Component):
    ...
```

The default `ComponentRegistry` is associated with the `Library` that
you load when you call `{% load component_tags %}` inside your template, or when you
add `django_components.templatetags.component_tags` to the template builtins.

So when you register or unregister a component to/from a component registry,
then behind the scenes the registry automatically adds/removes the component's
template tags to/from the Library, so you can call the component from within the templates
such as `{% component "my_comp" %}`.

## Working with ComponentRegistry

The default `ComponentRegistry` instance can be imported as:

```py
from django_components import registry
```

You can use the registry to manually add/remove/get components:

```py
from django_components import registry

# Register components
registry.register("button", ButtonComponent)
registry.register("card", CardComponent)

# Get all or single
registry.all()  # {"button": ButtonComponent, "card": CardComponent}
registry.get("card")  # CardComponent

# Check if component is registered
registry.has("button")  # True

# Unregister single component
registry.unregister("card")

# Unregister all components
registry.clear()
```

## Registering components to custom ComponentRegistry

If you are writing a component library to be shared with others, you may want to manage your own instance of `ComponentRegistry`
and register components onto a different `Library` instance than the default one.

The `Library` instance can be set at instantiation of `ComponentRegistry`. If omitted,
then the default Library instance from django_components is used.

```py
from django.template import Library
from django_components import ComponentRegistry

my_library = Library(...)
my_registry = ComponentRegistry(library=my_library)
```

When you have defined your own `ComponentRegistry`, you can either register the components
with `my_registry.register()`, or pass the registry to the `@component.register()` decorator
via the `registry` kwarg:

```py
from path.to.my.registry import my_registry

@register("my_component", registry=my_registry)
class MyComponent(Component):
    ...
```

NOTE: The Library instance can be accessed under `library` attribute of `ComponentRegistry`.

## ComponentRegistry settings

When you are creating an instance of `ComponentRegistry`, you can define the components' behavior within the template.

The registry accepts these settings:

- `context_behavior`
- `tag_formatter`

```py
from django.template import Library
from django_components import ComponentRegistry, RegistrySettings

register = library = django.template.Library()
comp_registry = ComponentRegistry(
    library=library,
    settings=RegistrySettings(
        context_behavior="isolated",
        tag_formatter="django_components.component_formatter",
    ),
)
```

These settings are [the same as the ones you can set for django_components](#available-settings).

In fact, when you set `COMPONENT.tag_formatter` or `COMPONENT.context_behavior`, these are forwarded to the default `ComponentRegistry`.

This makes it possible to have multiple registries with different settings in one projects, and makes sharing of component libraries possible.
