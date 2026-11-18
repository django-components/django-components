---
title: v0.81 🚨📢 (2024-06-12)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.81/
description: "- The order of arguments to render_to_response has changed, to align with the (now public) render method of Component class."
---

# v0.81 🚨📢 (2024-06-12)

#### BREAKING CHANGES

- The order of arguments to `render_to_response` has changed, to align with the (now public) `render` method of `Component` class.

#### Feat

- `Component.render()` is public and documented

- Slots passed `render_to_response` and `render` can now be rendered also as functions.