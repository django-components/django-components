Every component that you want to use in the template with the [`{% component %}`](django_components.templateags.component_tags)
tag needs to be registered with the [`ComponentRegistry`](django_components.component_registry.ComponentRegistry).
Normally, we use the [`@register`](django_components.component_registry.register) decorator for that:

```python
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    ...
```

But for the component to be registered, the code needs to be executed - and for that, the file needs to be imported as a module.

One way to do that is by importing all your components in `apps.py`:

```python
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = "my_app"

    def ready(self) -> None:
        from components.card.card import Card
        from components.list.list import List
        from components.menu.menu import Menu
        from components.button.button import Button
        ...
```

However, there's a simpler way!

By default, the Python files in the [`COMPONENTS.dirs`](django_components.app_settings.ComponentsSettings.dirs) directories (and app-level [`[app]/components/`](django_components.app_settings.ComponentsSettings.app_dirs)) are auto-imported in order to auto-register the components.

Autodiscovery occurs when Django is loaded, during the [`AppConfig.ready`](https://docs.djangoproject.com/en/5.1/ref/applications/#django.apps.AppConfig.ready)
hook of the `apps.py` file.

If you are using autodiscovery, keep a few points in mind:

- Avoid defining any logic on the module-level inside the `components` dir, that you would not want to run anyway.
- Components inside the auto-imported files still need to be registered with [`@register`](django_components.component_registry.register)
- Auto-imported component files must be valid Python modules, they must use suffix `.py`, and module name should follow [PEP-8](https://peps.python.org/pep-0008/#package-and-module-names).
- Subdirectories and files starting with an underscore `_` (except `__init__.py`) are ignored.

Autodiscovery can be disabled in the [settings](django_components.app_settings.ComponentsSettings.autodiscovery).

### Manually trigger autodiscovery

Autodiscovery can be also triggered manually, using the [`autodiscover`](django_components.autodiscovery.autodiscover) function. This is useful if you want to run autodiscovery at a custom point of the lifecycle:

```python
from django_components import autodiscover

autodiscover()
```

To get the same list of modules that [`autodiscover()`](../../../reference/api#django_components.autodiscover) would return,
but without importing them, use [`get_component_files()`](../../../reference/api#django_components.get_component_files):

```python
from django_components import get_component_files

modules = get_component_files(".py")
```
