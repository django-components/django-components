---
title: v0.142.1 (2025-10-06)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.142.1/
description: "- Fix bug introduced in v0.142.0 where django-components broke
  when the {% component_tags %} library was NOT among the built-ins."
---

# v0.142.1 (2025-10-06)

#### Fix

- Fix bug introduced in v0.142.0 where django-components broke
  when the `{% component_tags %}` library was NOT among the built-ins.

- Fix compatibility between Django's `inclusion_tag` and django-components.
  See [#1390](https://github.com/django-components/django-components/issues/1390)