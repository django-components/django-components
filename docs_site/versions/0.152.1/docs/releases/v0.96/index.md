---
title: v0.96 (2024-09-04)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.96/
description: "- Run-time type validation for Python >=3.11 - If the Component class is typed, e.g. Component[Args, Kwargs, ...], the args, kwargs, slots, and data..."
---

# v0.96 (2024-09-04)

#### Feat

- Run-time type validation for Python >=3.11 - If the `Component` class is typed, e.g. `Component[Args, Kwargs, ...]`, the args, kwargs, slots, and data are validated against the given types. (See [Runtime input validation with types](https://github.com/django-components/django-components#runtime-input-validation-with-types))

- Render hooks - Set `on_render_before` and `on_render_after` methods on `Component` to intercept or modify the template or context before rendering, or the rendered result afterwards. (See [Component hooks](https://github.com/django-components/django-components#component-hooks))

- `component_vars.is_filled` context variable can be accessed from within `on_render_before` and `on_render_after` hooks as `self.is_filled.my_slot`