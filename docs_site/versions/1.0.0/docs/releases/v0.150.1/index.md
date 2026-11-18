---
title: v0.150.1 (2026-06-01)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.150.1/
description: "- Template expression errors now point at the correct source line in debug mode"
---

# v0.150.1 (2026-06-01)

#### Fix

- **Template expression errors now point at the correct source line in debug mode**

    Multi-node template expressions (e.g. `value="prefix {{ x }}"` passed to a component) are wrapped in an internal `StringifiedNode` node that previously carried no template origin. As a result, Django's debug-mode traceback annotator could not locate the failing source line. The host template's origin is now threaded through to these nodes, so errors raised inside such expressions are annotated against the correct template file.

    See [#1597](https://github.com/django-components/django-components/issues/1597) and [#1635](https://github.com/django-components/django-components/pull/1635).

- **`@djc_test` no longer re-executes already-imported component modules between tests**

    The fixture used to pop every autodiscovered module from `sys.modules` at teardown. Now, the teardown snapshots `sys.modules` at setup and only clears modules the test brought in itself.

    See [#1598](https://github.com/django-components/django-components/issues/1598) / [#1630](https://github.com/django-components/django-components/pull/1630).

- **Fixed a component cache memory leak**

    See [#1648](https://github.com/django-components/django-components/issues/1648).

#### Refactor

- **`ComponentRegistry.register()` raises `AlreadyRegistered` on any replacement**

    Previously `register()` silently overwrote an existing entry whenever the old and new classes had the same `class_id`. Now, different classes under the same name now raise `AlreadyRegistered`, and must call `registry.unregister(name)` first. Re-registering the **exact same class object** is still a no-op.