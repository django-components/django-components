---
title: v0.129 (2025-02-16)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.129/
description: "- Fix thread unsafe media resolve validation by moving it to ComponentMedia _post_init (#977
- Fix bug: Relative path in extends and include does not..."
---

# v0.129 (2025-02-16)

#### Fix

- Fix thread unsafe media resolve validation by moving it to ComponentMedia `__post_init` ([#977](https://github.com/django-components/django-components/pull/977)
- Fix bug: Relative path in extends and include does not work when using template_file ([#976](https://github.com/django-components/django-components/pull/976)
- Fix error when template cache setting (`template_cache_size`) is set to 0 ([#974](https://github.com/django-components/django-components/pull/974)