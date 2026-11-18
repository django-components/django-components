---
title: v0.100 🚨📢 (2024-09-11)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.100/
description: "- django_components.safer_staticfiles app was removed. It is no longer needed."
---

# v0.100 🚨📢 (2024-09-11)

#### BREAKING CHANGES

- `django_components.safer_staticfiles` app was removed. It is no longer needed.

- Installation changes:

    - Instead of defining component directories in `STATICFILES_DIRS`, set them to [`COMPONENTS.dirs`](https://github.com/django-components/django-components#dirs).
    - You now must define `STATICFILES_FINDERS`

    - [See here how to migrate your settings.py](https://github.com/django-components/django-components/blob/master/docs_site/content/docs/migrating_from_safer_staticfiles.md)

#### Feat

- Beside the top-level `/components` directory, you can now define also app-level components dirs, e.g. `[app]/components`
  (See [`COMPONENTS.app_dirs`](https://github.com/django-components/django-components#app_dirs)).

#### Refactor

- When you call `as_view()` on a component instance, that instance will be passed to `View.as_view()`