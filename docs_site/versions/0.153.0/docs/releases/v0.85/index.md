---
title: v0.85 🚨📢 (2024-07-29)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.85/
description: "- Autodiscovery module resolution changed. Following undocumented behavior was removed:"
---

# v0.85 🚨📢 (2024-07-29)

#### BREAKING CHANGES

- Autodiscovery module resolution changed. Following undocumented behavior was removed:

    - Previously, autodiscovery also imported any `[app]/components.py` files, and used `SETTINGS_MODULE` to search for component dirs.

        To migrate from:

        - `[app]/components.py` - Define each module in `COMPONENTS.libraries` setting,
            or import each module inside the `AppConfig.ready()` hook in respective `apps.py` files.

        - `SETTINGS_MODULE` - Define component dirs using `STATICFILES_DIRS`

    - Previously, autodiscovery handled relative files in `STATICFILES_DIRS`. To align with Django, `STATICFILES_DIRS` now must be full paths ([Django docs](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STATICFILES_DIRS)).