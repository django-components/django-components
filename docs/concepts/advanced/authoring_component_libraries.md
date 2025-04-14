You can publish and share your components for others to use. Below you will find the steps to do so.

For live examples, see the [Community examples](../../overview/community.md#community-examples).

## Writing component libraries

1.  Create a Django project with a similar structure:

    ```txt
    project/
      |--  myapp/
        |--  __init__.py
        |--  apps.py
        |--  templates/
          |--  table/
            |--  table.py
            |--  table.js
            |--  table.css
            |--  table.html
        |--  menu.py   <--- single-file component
      |--  templatetags/
        |--  __init__.py
        |--  mytags.py
    ```

2.  Create custom [`Library`](https://docs.djangoproject.com/en/5.1/howto/custom-template-tags/#how-to-create-custom-template-tags-and-filters)
    and [`ComponentRegistry`](django_components.component_registry.ComponentRegistry) instances in `mytags.py`

    This will be the entrypoint for using the components inside Django templates.

    Remember that Django requires the [`Library`](https://docs.djangoproject.com/en/5.1/howto/custom-template-tags/#how-to-create-custom-template-tags-and-filters)
    instance to be accessible under the `register` variable ([See Django docs](https://docs.djangoproject.com/en/dev/howto/custom-template-tags)):

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

    As you can see above, this is also the place where we configure how our components should behave,
    using the [`settings`](django_components.component_registry.ComponentRegistry.settings) argument.
    If omitted, default settings are used.

    For library authors, we recommend setting [`context_behavior`](django_components.app_settings.ComponentsSettings.context_behavior)
    to [`"isolated"`](django_components.app_settings.ContextBehavior.ISOLATED), so that the state cannot leak into the components,
    and so the components' behavior is configured solely through the inputs. This means that the components will be more predictable and easier to debug.

    Next, you can decide how will others use your components by setting the
    [`tag_formatter`](django_components.app_settings.ComponentsSettings.tag_formatter)
    options.

    If omitted or set to `"django_components.component_formatter"`,
    your components will be used like this:

    ```django
    {% component "table" items=items headers=headers %}
    {% endcomponent %}
    ```

    Or you can use `"django_components.component_shorthand_formatter"`
    to use components like so:

    ```django
    {% table items=items headers=headers %}
    {% endtable %}
    ```

    Or you can define a [custom TagFormatter](#tagformatter).

    Either way, these settings will be scoped only to your components. So, in the user code,
    there may be components side-by-side that use different formatters:

    ```django
    {% load mytags %}

    {# Component from your library "mytags", using the "shorthand" formatter #}
    {% table items=items headers=header %}
    {% endtable %}

    {# User-created components using the default settings #}
    {% component "my_comp" title="Abc..." %}
    {% endcomponent %}
    ```

3.  Write your components and register them with your instance of [`ComponentRegistry`](../../reference/api#ComponentRegistry)

    There's one difference when you are writing components that are to be shared, and that's
    that the components must be explicitly registered with your instance of
    [`ComponentRegistry`](../../reference/api#ComponentRegistry) from the previous step.

    For better user experience, you can also define the types for the args, kwargs, slots and data.

    It's also a good idea to have a common prefix for your components, so they can be easily distinguished from users' components. In the example below, we use the prefix `my_` / `My`.

    ```djc_py
    from typing import Dict, NotRequired, Optional, Tuple, TypedDict

    from django_components import Component, SlotContent, register, types

    from myapp.templatetags.mytags import comp_registry

    # Define the types
    class EmptyDict(TypedDict):
        pass

    type MyMenuArgs = Tuple[int, str]

    class MyMenuSlots(TypedDict):
        default: NotRequired[Optional[SlotContent[EmptyDict]]]

    class MyMenuProps(TypedDict):
        vertical: NotRequired[bool]
        klass: NotRequired[str]
        style: NotRequired[str]

    # Define the component
    # NOTE: Don't forget to set the `registry`!
    @register("my_menu", registry=comp_registry)
    class MyMenu(Component[MyMenuArgs, MyMenuProps, MyMenuSlots]):
        def get_context_data(
            self,
            *args,
            attrs: Optional[Dict] = None,
        ):
            return {
                "attrs": attrs,
            }

        template: types.django_html = """
            {# Load django_components template tags #}
            {% load component_tags %}

            <div {% html_attrs attrs class="my-menu" %}>
                <div class="my-menu__content">
                    {% slot "default" default / %}
                </div>
            </div>
        """
    ```

4.  Import the components in `apps.py`

    Normally, users rely on [autodiscovery](../../concepts/autodiscovery) and [`COMPONENTS.dirs`](../../reference/settings#dirs)
    to load the component files.

    Since you, as the library author, are not in control of the file system, it is recommended to load the components manually.

    We recommend doing this in the [`AppConfig.ready()`](https://docs.djangoproject.com/en/5.1/ref/applications/#django.apps.AppConfig.ready)
    hook of your `apps.py`:

    ```py
    from django.apps import AppConfig

    class MyAppConfig(AppConfig):
        default_auto_field = "django.db.models.BigAutoField"
        name = "myapp"

        # This is the code that gets run when user adds myapp
        # to Django's INSTALLED_APPS
        def ready(self) -> None:
            # Import the components that you want to make available
            # inside the templates.
            from myapp.templates import (
                menu,
                table,
            )
    ```

    Note that you can also include any other startup logic within
    [`AppConfig.ready()`](https://docs.djangoproject.com/en/5.1/ref/applications/#django.apps.AppConfig.ready).

And that's it! The next step is to publish it.

## Publishing component libraries

Once you are ready to share your library, you need to build
a distribution and then publish it to PyPI.

django_components uses the [`build`](https://build.pypa.io/en/stable/) utility to build a distribution:

```bash
python -m build --sdist --wheel --outdir dist/ .
```

And to publish to PyPI, you can use [`twine`](https://docs.djangoproject.com/en/5.1/ref/applications/#django.apps.AppConfig.ready)
([See Python user guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives))

```bash
twine upload --repository pypi dist/* -u __token__ -p <PyPI_TOKEN>
```

Notes on publishing:

- If you use components where the HTML / CSS / JS files are separate, you may need to define
  [`MANIFEST.in`](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html)
  to include those files with the distribution
  ([see user guide](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html)).

## Installing and using component libraries

After the package has been published, all that remains is to install it in other django projects:

1. Install the package:

    ```bash
    pip install myapp django_components
    ```

2. Add the package to `INSTALLED_APPS`

    ```py
    INSTALLED_APPS = [
        ...
        "django_components",
        "myapp",
    ]
    ```

3. Optionally add the template tags to the [`builtins`](https://docs.djangoproject.com/en/5.1/topics/templates/#django.template.backends.django.DjangoTemplates),
   so you don't have to call `{% load mytags %}` in every template:

    ```python
    TEMPLATES = [
        {
            ...,
            'OPTIONS': {
                'builtins': [
                    'myapp.templatetags.mytags',
                ]
            },
        },
    ]
    ```

4. And, at last, you can use the components in your own project!

    ```django
    {% my_menu title="Abc..." %}
        Hello World!
    {% endmy_menu %}
    ```
