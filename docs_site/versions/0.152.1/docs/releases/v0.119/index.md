---
title: v0.119 (2024-12-13)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.119/
description: "⚠️ Attention ⚠️ - This release introduced bugs #849, #855. Please update to v0.121."
---

# v0.119 (2024-12-13)

⚠️ Attention ⚠️ - This release introduced bugs [#849](https://github.com/django-components/django-components/pull/849), [#855](https://github.com/django-components/django-components/pull/855). Please update to v0.121.

#### Fix

- Fix compatibility with custom subclasses of Django's `Template` that need to access
  `origin` or other initialization arguments. (https://github.com/django-components/django-components/pull/828)

#### Refactor

- Compatibility with `django-debug-toolbar-template-profiler`:
  - Monkeypatching of Django's `Template` now happens at `AppConfig.ready()` (https://github.com/django-components/django-components/pull/825)

- Internal parsing of template tags tag was updated. No API change. (https://github.com/django-components/django-components/pull/827)