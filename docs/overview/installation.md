1. Install `django_components` into your environment:

    ```bash
    pip install django_components
    ```

2. Load `django_components` into Django by adding it into `INSTALLED_APPS` in in your settings file:

    ```python
    INSTALLED_APPS = [
        ...,
        'django_components',
    ]
    ```

3. `BASE_DIR` setting is required. Ensure that it is defined:

    ```python
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    ```

4. _Optional._ Set [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
   and/or [`COMPONENTS.app_dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
   so django_components knows where to find component HTML, JS and CSS files:

    If [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
    is omitted, django-components will by default look for a top-level `/components` directory,
    `{BASE_DIR}/components`.

    ```python
    from django_components import ComponentsSettings

    COMPONENTS = ComponentsSettings(
        dirs=[
            ...,
            Path(BASE_DIR) / "components",
        ],
    )
    ```

    In addition to [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs),
    django_components will also load components from app-level directories, such as `my-app/components/`.
    The directories within apps are configured with
    [`COMPONENTS.app_dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs),
    and the default is `[app]/components`.

    !!! note

        The input to [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
        is the same as for `STATICFILES_DIRS`, and the paths must be full paths.
        [See Django docs](https://docs.djangoproject.com/en/5.0/ref/settings/#staticfiles-dirs).

5. Next, modify `TEMPLATES` section of settings.py as follows:

    - _Remove `'APP_DIRS': True,`_
        - NOTE: Instead of `APP_DIRS: True`, we will use
          [`django.template.loaders.app_directories.Loader`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.loaders.app_directories.Loader),
          which has the same effect.
    - Add `loaders` to `OPTIONS` list and set it to following value:

    This allows Django to load component HTML files as Django templates.

    ```python
    TEMPLATES = [
        {
            ...,
            'OPTIONS': {
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

2. Add [`ComponentDependencyMiddleware`](../reference/middlewares.md#django_components.dependencies.ComponentDependencyMiddleware)
   to `MIDDLEWARE` setting.

    The middleware searches the outgoing HTML for all components that were rendered
    to generate the HTML, and adds the JS and CSS associated with those components.

    ```python
    MIDDLEWARE = [
        ...
        "django_components.middleware.ComponentDependencyMiddleware",
    ]
    ```

    Read more in [Rendering JS/CSS dependencies](../concepts/advanced/rendering_js_css.md).

3. Add django-component's URL paths to your `urlpatterns`:

    ```python
    from django.urls import include, path

    urlpatterns = [
        ...
        path("", include("django_components.urls")),
    ]
    ```

4. _Optional._ If you want to change where the JS and CSS is rendered, use
    [`{% component_js_dependencies %}`](../reference/template_tags.md#component_css_dependencies)
    and [`{% component_css_dependencies %}`](../reference/template_tags.md#component_js_dependencies).

    By default, the JS `<script>` and CSS `<link>` tags are automatically inserted
    into the HTML (See [JS and CSS output locations](../../concepts/advanced/rendering_js_css/#js-and-css-output-locations)).

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

5. _Optional._ By default, components' JS and CSS files are cached in memory.
   
    If you want to change the cache backend, set the [`COMPONENTS.cache`](../reference/settings.md#django_components.app_settings.ComponentsSettings.cache) setting.

    Read more in [Caching](../../guides/setup/caching).

## Optional

### Builtin template tags
To avoid loading the app in each template using `{% load component_tags %}`, you can add the tag as a 'builtin' in settings.py

```python
TEMPLATES = [
    {
        ...,
        'OPTIONS': {
            'builtins': [
                'django_components.templatetags.component_tags',
            ]
        },
    },
]
```

---

Now you're all set! Read on to find out how to build your first component.
