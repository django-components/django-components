---
title: Versioning and support
description: What a django-components 1.x upgrade can change in your project, which releases get fixes, and how long each Django and Python version is supported.
---

# Versioning and support

Allow any 1.x release, and an upgrade will not break code that uses the
documented API, apart from the [two exceptions](#what-1x-promises) below:

```toml
# pyproject.toml
[project]
dependencies = [
    "django-components>=1.0.0,<2",
]
```

django-components is in [maintenance mode](#maintenance-mode): new
releases bring fixes and support for new Django and Python versions, and
new features go to Citry.

## Kinds of release

django-components follows [semantic versioning](https://semver.org/).

- **Patch** (1.0.0 to 1.0.1): bug fixes and security fixes.
- **Minor** (1.0.0 to 1.1.0): can add support for a new Django or Python
  version, deprecate a feature, or drop a Django or Python version that
  has reached its end of life.
- **Major** (2.0.0): may remove deprecated features and make other
  breaking changes. No 2.0.0 release is planned.

## What 1.x promises

Code that uses the [public API](#public-api) keeps working on every 1.x
release, with two exceptions:

- A minor release can drop a Django or Python version that has reached
  its end of life (see [Django and Python](#django-and-python)).
- A security fix can refuse input that earlier releases accepted, or
  handle it differently (for example, render it escaped), when that is
  needed to close a security hole. The release notes for that release
  say so.

Any other change that would break the public API waits for 2.0.0.

A deprecated feature keeps working until 2.0.0. The documentation marks
it as deprecated and tells you to stop using it.

## What the public API is { #public-api }

The public API is everything this documentation describes: the behavior
the guides describe, and every page under
[API reference](../reference/index.md), such as the classes and
functions, [settings](../reference/settings.md),
[template tags](../reference/template_tags.md), middleware,
[URLs](../reference/urls.md), [commands](../reference/commands.md),
signals, the testing API and
[extension hooks](../reference/extension_hooks.md).

Anything the documentation does not describe is internal. Internal code
may change in any release, even a patch release. If you rely on it, pin
the exact django-components version and test each upgrade.

## Which releases get fixes

Bug and security fixes go to the newest 1.x minor release only. Once
1.2.0 is out, a fix ships as 1.2.1, not as a 1.1.x release. With
`django-components>=1.0.0,<2`, upgrading gives you the release that gets
fixes.

0.x releases get no fixes. To move to 1.x, see
[Upgrading from 0.x versions](../upgrading/v0.md).

To report a security problem, follow the
[security policy](https://github.com/django-components/django-components/blob/master/SECURITY.md).

## Django and Python

- Each Django version is supported until
  [Django's own end of life](https://www.djangoproject.com/download/#supported-versions)
  for it.
- Each Python version is supported until it
  [reaches its end of life](https://devguide.python.org/versions/).
- A version is dropped only in a minor release, never in a patch
  release. The release notes name the version.

When your Django or Python version is dropped, your installer keeps the
last release that supports it. That release gets no more fixes, so
upgrade Django or Python to keep getting them.

The [Compatibility](compatibility.md) page lists the Python and Django
versions that the current release supports.

## Maintenance mode

django-components is in maintenance mode. New releases bring:

- security fixes,
- support for new Django and Python versions,
- bug fixes.

New features go to [Citry](https://citry.dev/), a Python frontend
framework that grew out of django-components and works with Django. To
move a project over one component at a time, follow the
[migration guide](https://citry.dev/guides/migrate-from-django-components/).
