---
title: v0.70 🚨📢 (2024-05-01)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.70/
description: "- {% if_filled \"my_slot\" %} tags were replaced with {{ component_vars.is_filled.my_slot }} variables."
---

# v0.70 🚨📢 (2024-05-01)

#### BREAKING CHANGES

- `{% if_filled "my_slot" %}` tags were replaced with `{{ component_vars.is_filled.my_slot }}` variables.

- Simplified settings - `slot_context_behavior` and `context_behavior` were merged. See the [documentation](https://github.com/django-components/django-components#context-behavior) for more details.