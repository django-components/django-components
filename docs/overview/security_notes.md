_It is strongly recommended to read this section before using django-components in production._

## Static files

**TL;DR: No action needed from v0.100 onwards. Before v0.100, use `safer_staticfiles` to avoid exposing backend logic.**

Components can be organized however you prefer.
That said, our prefered way is to keep the files of a component close together by bundling them in the same directory.

This means that files containing backend logic, such as Python modules and HTML templates, live in the same directory as static files, e.g. JS and CSS.

From v0.100 onwards, we keep component files (as defined by
[`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
and [`COMPONENTS.app_dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs))
separate from the rest of the static
files (defined by `STATICFILES_DIRS`). That way, the Python and HTML files are NOT exposed by the server. Only the static JS, CSS, and
[other common formats](../reference/settings.md#django_components.app_settings.ComponentsSettings.static_files_allowed).

!!! note

    If you need to expose different file formats, you can configure these with
    [`COMPONENTS.static_files_allowed`](../reference/settings.md#django_components.app_settings.ComponentsSettings.static_files_allowed)
    and [`COMPONENTS.static_files_forbidden`](../reference/settings.md#django_components.app_settings.ComponentsSettings.static_files_forbidden).

<!-- # TODO_REMOVE_IN_V1 - Remove mentions of safer_staticfiles in V1 -->

### Static files prior to v0.100

Prior to v0.100, if your were using _django.contrib.staticfiles_ to collect static files, no distinction was made between the different kinds of files.

As a result, your Python code and templates may inadvertently become available on your static file server.
You probably don't want this, as parts of your backend logic will be exposed, posing a **potential security vulnerability**.

From _v0.27_ until _v0.100_, django-components shipped with an additional installable app _django_components.**safer_staticfiles**_.
It was a drop-in replacement for _django.contrib.staticfiles_.
Its behavior is 100% identical except it ignores `.py` and `.html` files, meaning these will not end up on your static files server.

To use it, add it to `INSTALLED_APPS` and remove *django.contrib.staticfiles*.

```python
INSTALLED_APPS = [
    # 'django.contrib.staticfiles',   # <-- REMOVE
    'django_components',
    'django_components.safer_staticfiles'  # <-- ADD
]
```

If you are on an pre-v0.27 version of django-components, your alternatives are:

- a) passing `--ignore <pattern>` options to the _collecstatic_ CLI command,
- b) defining a subclass of StaticFilesConfig.

Both routes are described in the official [docs of the _staticfiles_ app](https://docs.djangoproject.com/en/4.2/ref/contrib/staticfiles/#customizing-the-ignored-pattern-list).

Note that `safer_staticfiles` excludes the `.py` and `.html` files for [collectstatic command](https://docs.djangoproject.com/en/5.0/ref/contrib/staticfiles/#collectstatic):

```sh
python manage.py collectstatic
```

but it is ignored on the [development server](https://docs.djangoproject.com/en/5.0/ref/django-admin/#runserver):

```sh
python manage.py runserver
```

For a step-by-step guide on deploying production server with static files,
[see the demo project](https://github.com/django-components/django-components/tree/master/sampleproject).

See the older versions of the sampleproject for a setup with pre-v0.100 version.
