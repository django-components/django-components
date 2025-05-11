### Basic installation

1. Install `django_components` into your environment:

    ```bash
    pip install django_components
    ```

2. Load `django_components` into Django by adding it into `INSTALLED_APPS` in your settings file:

    ```python
    # app/settings.py
    INSTALLED_APPS = [
        ...,
        'django_components',
    ]
    ```

3. `BASE_DIR` setting is required. Ensure that it is defined:

    ```python
    # app/settings.py
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    ```

4. Next, modify `TEMPLATES` section of `settings.py` as follows:

    - _Remove `'APP_DIRS': True,`_
        - NOTE: Instead of `APP_DIRS: True`, we will use
          [`django.template.loaders.app_directories.Loader`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.loaders.app_directories.Loader),
          which has the same effect.
    - Add `loaders` to `OPTIONS` list and set it to following value:

    This allows Django to load component HTML files as Django templates.

    ```python
    TEMPLATES = [
        {
            ...,
            'OPTIONS': {
                ...,
                'loaders':[(
                    'django.template.loaders.cached.Loader', [
                        # Default Django loader
                        'django.template.loaders.filesystem.Loader',
                        # Including this is the same as APP_DIRS=True
                        'django.template.loaders.app_directories.Loader',
                        # Components loader
                        'django_components.template_loader.Loader',
                    ]
                )],
            },
        },
    ]
    ```

5. Add django-component's URL paths to your `urlpatterns`:

    Django components already prefixes all URLs with `components/`. So when you are
    adding the URLs to `urlpatterns`, you can use an empty string as the first argument:

    ```python
    from django.urls import include, path

    urlpatterns = [
        ...
        path("", include("django_components.urls")),
    ]
    ```

## Adding support for JS and CSS

If you want to use JS or CSS with components, you will need to:

1. Add `"django_components.finders.ComponentsFileSystemFinder"` to `STATICFILES_FINDERS` in your settings file.

    This allows Django to serve component JS and CSS as static files.

    ```python
    STATICFILES_FINDERS = [
        # Default finders
        "django.contrib.staticfiles.finders.FileSystemFinder",
        "django.contrib.staticfiles.finders.AppDirectoriesFinder",
        # Django components
        "django_components.finders.ComponentsFileSystemFinder",
    ]
    ```


2. _Optional._ If you want to change where the JS and CSS is rendered, use
    [`{% component_js_dependencies %}`](../reference/template_tags.md#component_css_dependencies)
    and [`{% component_css_dependencies %}`](../reference/template_tags.md#component_js_dependencies).

    By default, the JS `<script>` and CSS `<link>` tags are automatically inserted
    into the HTML (See [Default JS / CSS locations](../../concepts/advanced/rendering_js_css/#default-js-css-locations)).

    ```django
    <!doctype html>
    <html>
      <head>
        ...
        {% component_css_dependencies %}
      </head>
      <body>
        ...
        {% component_js_dependencies %}
      </body>
    </html>
    ```

3. _Optional._ By default, components' JS and CSS files are cached in memory.
   
    If you want to change the cache backend, set the [`COMPONENTS.cache`](../reference/settings.md#django_components.app_settings.ComponentsSettings.cache) setting.

    Read more in [Caching](../../guides/setup/caching).

## Optional

### Builtin template tags

To avoid loading the app in each template using `{% load component_tags %}`, you can add the tag as a 'builtin' in `settings.py`:

```python
TEMPLATES = [
    {
        ...,
        'OPTIONS': {
            ...,
            'builtins': [
                'django_components.templatetags.component_tags',
            ]
        },
    },
]
```

### Component directories

django-components needs to know where to search for component HTML, JS and CSS files.

There are two ways to configure the component directories:

- [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs) sets global component directories.
- [`COMPONENTS.app_dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs) sets app-level component directories.

By default, django-components will look for a top-level `/components` directory,
`{BASE_DIR}/components`, equivalent to:

```python
from django_components import ComponentsSettings

COMPONENTS = ComponentsSettings(
    dirs=[
        ...,
        Path(BASE_DIR) / "components",
    ],
)
```

For app-level directories, the default is `[app]/components`, equivalent to:

```python
from django_components import ComponentsSettings

COMPONENTS = ComponentsSettings(
    app_dirs=[
        ...,
        "components",
    ],
)
```

!!! note

    The input to [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
    is the same as for `STATICFILES_DIRS`, and the paths must be full paths.
    [See Django docs](https://docs.djangoproject.com/en/5.2/ref/settings/#staticfiles-dirs).

---

Now you're all set! Read on to find out how to build your first component.
