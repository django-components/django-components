---
title: v0.153.0
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.153.0/
description: "- Dropped support for Python 3.10."
---

# v0.153.0

#### Breaking changes 🚨📢

- Dropped support for Python 3.10.

- `django-components` no longer installs `typing-extensions`. If your code imports `typing_extensions`, add it to your own dependencies.

#### Feature

- Add support for Python 3.15. Python 3.15 needs Django 6.1.3 or newer, so on Python 3.15 `django-components` requires that version.