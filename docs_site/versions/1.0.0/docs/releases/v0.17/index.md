---
title: v0.17 (2021-09-10)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.17/
description: "- Renamed Component.context and Component.template to get_context_data and get_template_name. The old methods still work, but emit a deprecation warning."
---

# v0.17 (2021-09-10)

#### BREAKING CHANGES

- Renamed `Component.context` and `Component.template` to `get_context_data` and `get_template_name`. The old methods still work, but emit a deprecation warning.

    This change was done to sync naming with Django's class based views, and make using django-components more familiar to Django users. `Component.context` and `Component.template` will be removed when version 1.0 is released.