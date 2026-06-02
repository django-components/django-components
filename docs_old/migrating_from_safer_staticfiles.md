# Migrating from safer_staticfiles

This guide is for you if you're upgrating django_components to v0.100 or later
from older versions.

In version 0.100, we changed how components' static JS and CSS files are handled.
See more in the ["Static files" section](https://github.com/django-components/django-components/tree/master/sampleproject).

Migration steps:

1. Remove `django_components.safer_staticfiles` from `INSTALLED_APPS` in your `settings.py`,
   and replace it with `django.contrib.staticfiles`.

   Before:

   ```py
   INSTALLED_APPS = [
      "django.contrib.admin",
      ...
      # "django.contrib.staticfiles",  # <-- ADD
      "django_components",
      "django_components.safer_staticfiles",  # <-- REMOVE
   ]
   ```

   After:

   ```py
   INSTALLED_APPS = [
      "django.contrib.admin",
      ...
      "django.contrib.staticfiles",
      "django_components",
   ]
   ```

2. Add `STATICFILES_FINDERS` to `settings.py`, and add `django_components.finders.ComponentsFileSystemFinder`:

   ```py
   STATICFILES_FINDERS = [
      # Default finders
      "django.contrib.staticfiles.finders.FileSystemFinder",
      "django.contrib.staticfiles.finders.AppDirectoriesFinder",
      # Django components
      "django_components.finders.ComponentsFileSystemFinder",  # <-- ADDED
   ]
   ```

3. Add `COMPONENTS.dirs` to `settings.py`.

   If you previously defined `STATICFILES_DIRS`, move
   only those directories from `STATICFILES_DIRS` that point to components directories, and keep the rest.

   E.g. if you have `STATICFILES_DIRS` like this:

   ```py
   STATICFILES_DIRS = [
      BASE_DIR / "components",  # <-- MOVE
      BASE_DIR / "myapp" / "components",  # <-- MOVE
      BASE_DIR / "assets",
   ]
   ```

   Then first two entries point to components dirs, whereas `/assets` points to non-component static files.
   In this case move only the first two paths:

   ```py
   COMPONENTS = {
      "dirs": [
         BASE_DIR / "components",  # <-- MOVED
         BASE_DIR / "myapp" / "components",  # <-- MOVED
      ],
   }

   STATICFILES_DIRS = [
      BASE_DIR / "assets",
   ]
   ```

   Moreover, if you defined app-level component directories in `STATICFILES_DIRS` before,
   you can now define as a RELATIVE path in `app_dirs`:

   ```py
   COMPONENTS = {
      "dirs": [
         # Search top-level "/components/" dir
         BASE_DIR / "components",
      ],
      "app_dirs": [
         # Search "/[app]/components/" dirs
         "components",
      ],
   }

   STATICFILES_DIRS = [
      BASE_DIR / "assets",
   ]
   ```
