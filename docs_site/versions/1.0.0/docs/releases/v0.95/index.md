---
title: v0.95 (2024-08-29)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.95/
description: "- Added support for dynamic components, where the component name is passed as a variable. (See Dynamic components)"
---

# v0.95 (2024-08-29)

#### Feat

- Added support for dynamic components, where the component name is passed as a variable. (See [Dynamic components](https://github.com/django-components/django-components#dynamic-components))

#### Refactor

- Changed `Component.input` to raise `RuntimeError` if accessed outside of render context. Previously it returned `None` if unset.