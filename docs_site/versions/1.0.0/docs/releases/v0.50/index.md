---
title: v0.50 🚨📢 (2024-02-26)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.50/
description: "- {% component_block %} is now {% component %}, and {% component %} blocks need an ending {% endcomponent %} tag."
---

# v0.50 🚨📢 (2024-02-26)

#### BREAKING CHANGES

- `{% component_block %}` is now `{% component %}`, and `{% component %}` blocks need an ending `{% endcomponent %}` tag.

    The new `python manage.py upgradecomponent` command can be used to upgrade a directory (use `--path` argument to point to each dir) of templates that use components to the new syntax automatically.

    This change is done to simplify the API in anticipation of a 1.0 release of django_components. After 1.0 we intend to be stricter with big changes like this in point releases.