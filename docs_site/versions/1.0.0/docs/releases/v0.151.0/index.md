---
title: v0.151.0 (2026-06-03)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.151.0/
description: "- Hot reload - Component files (templates, JS, CSS) are now updated without a server restart"
---

# v0.151.0 (2026-06-03)

#### Feature

- **Hot reload - Component files (templates, JS, CSS) are now updated without a server restart**

    Before, with the `reload_on_file_change=True` setting, the entire
    Django server was restarted when you edited a component's HTML template, JS, or CSS file.

    Now, the files are updated in-memory, no server restart needed. The next request re-reads from disk automatically.

    Changes:
    - The `reload_on_file_change` setting now accepts values `"off"`, `"hot"`,`"restart"`, `True`, `False`.
    - The default has changed from `False` to `"hot"`.
    - The old `reload_on_file_change=True` behavior is still available as `reload_on_file_change="restart"`
    - The `restart` mode is deprecated and will be removed in v1.

    Actions:
    - If no `reload_on_file_change` was set -> Hot reload now enabled by default.
    - If `reload_on_file_change=True` -> Now hot-reloads instead of restarts
    - If `reload_on_file_change=False` -> No change.

    New `ReloadMode` enum is exported from `django_components` for use in settings.

    See [#1324](https://github.com/django-components/django-components/issues/1324) and [#1461](https://github.com/django-components/django-components/issues/1461).