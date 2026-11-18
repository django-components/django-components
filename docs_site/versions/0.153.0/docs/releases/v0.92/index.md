---
title: v0.92 🚨📢 (2024-08-22)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.92/
description: "- Component class is no longer a subclass of View. To configure the View class, set the Component.View nested class. HTTP methods like get or post can..."
---

# v0.92 🚨📢 (2024-08-22)

#### BREAKING CHANGES

- `Component` class is no longer a subclass of `View`. To configure the `View` class, set the `Component.View` nested class. HTTP methods like `get` or `post` can still be defined directly on `Component` class, and `Component.as_view()` internally calls `Component.View.as_view()`. (See [Modifying the View class](https://github.com/django-components/django-components#modifying-the-view-class))

#### Feat

- The inputs (args, kwargs, slots, context, ...) that you pass to `Component.render()` can be accessed from within `get_context_data`, `get_template` and `get_template_name` via `self.input`. (See [Accessing data passed to the component](https://github.com/django-components/django-components#accessing-data-passed-to-the-component))

- Typing: `Component` class supports generics that specify types for `Component.render` (See [Adding type hints with Generics](https://github.com/django-components/django-components#adding-type-hints-with-generics))