---
title: v0.131 (2025-03-20)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.131/
description: "- Support for extensions (plugins) for django-components!"
---

# v0.131 (2025-03-20)

#### Feat

- Support for extensions (plugins) for django-components!

    - Hook into lifecycle events of django-components
    - Pre-/post-process component inputs, outputs, and templates
    - Add extra methods or attributes to Components
    - Add custom extension-specific CLI commands
    - Add custom extension-specific URL routes

    Read more on [Extensions](https://django-components.github.io/django-components/0.131/concepts/advanced/extensions/).

- New CLI commands:
    - `components list` - List all components
    - `components create <name>` - Create a new component (supersedes `startcomponent`)
    - `components upgrade` - Upgrade a component (supersedes `upgradecomponent`)
    - `components ext list` - List all extensions
    - `components ext run <extension> <command>` - Run a command added by an extension

- `@djc_test` decorator for writing tests that involve Components.

    - The decorator manages global state, ensuring that tests don't leak.
    - If using `pytest`, the decorator allows you to parametrize Django or Components settings.
    - The decorator also serves as a stand-in for Django's `@override_settings`.

    See the API reference for [`@djc_test`](https://django-components.github.io/django-components/0.131/reference/testing_api/#django_components.testing.djc_test) for more details.

- `ComponentRegistry` now has a `has()` method to check if a component is registered
   without raising an error.

- Get all created `Component` classes with `all_components()`.

- Get all created `ComponentRegistry` instances with `all_registries()`.

#### Refactor

- The `startcomponent` and `upgradecomponent` commands are deprecated, and will be removed in v1.

    Instead, use `components create <name>` and `components upgrade`.

#### Internal

- Settings are now loaded only once, and thus are considered immutable once loaded. Previously,
  django-components would load settings from `settings.COMPONENTS` on each access. The new behavior
  aligns with Django's settings.