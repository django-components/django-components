---
title: v0.150.0 (2026-05-02)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.150.0/
description: "- Supported Django versions now match the currently supported Django release line."
---

# v0.150.0 (2026-05-02)

#### Compatibility

- Supported Django versions now match the currently supported Django release line.

    Django 4.2 support was removed from the compatibility docs, package metadata, dependency floors, tox environments, and related compatibility code.

    See [#1620](https://github.com/django-components/django-components/issues/1620).

#### Fix

- **Components now render correctly inside inclusion tags that return `None`**

    Some third-party inclusion tags rely on Django accepting `None` as an empty context. django-components now handles that case before adding its internal dependency-rendering marker.

    See [#1603](https://github.com/django-components/django-components/issues/1603).

- **Template expression errors now preserve the original traceback**

    When Django template debug mode is enabled, errors raised from multi-node template expressions now surface the original rendering exception instead of being replaced by an unrelated traceback annotation error.

    See [#1597](https://github.com/django-components/django-components/issues/1597).

- **Component registry cleanup no longer unregisters newer replacement components**

    Registry finalizer callbacks no longer keep stale component classes alive or unregister a newer component class after a reimport replaces the old one.

    See [#1598](https://github.com/django-components/django-components/issues/1598).

- **Moved documentation URLs now redirect to their current locations**

    This helps search engines recover from stale indexed documentation URLs, including old release notes, contributing, development, and HTML/JS/CSS files pages.

    See [#1355](https://github.com/django-components/django-components/issues/1355).

#### Docs

- Docs builds now use strict link validation, and version-relative documentation links are preserved.

    This prevents broken internal docs links from slipping through CI while keeping links in older docs versions pointed at their own version instead of always pointing to `latest`.

    See [#1343](https://github.com/django-components/django-components/issues/1343).

- The JS and CSS variable examples now show the supported access patterns.

    JS examples now read `get_js_data()` values through `$onComponent()`, and CSS examples now read `get_css_data()` values through CSS variables.

    See [#1594](https://github.com/django-components/django-components/issues/1594).

- The `on_render` hook documentation now renders Django-loaded templates with the correct context type.

    The example now uses the underlying template object when rendering with the Django `Context` passed to `on_render`.

    See [#1593](https://github.com/django-components/django-components/issues/1593).

#### Maintenance

- Documentation deployment now avoids strict-build failures from generated release-note metadata warnings.

    See [#1636](https://github.com/django-components/django-components/pull/1636).

- Updated development and CI dependencies.

    See [#1624](https://github.com/django-components/django-components/pull/1624), [#1625](https://github.com/django-components/django-components/pull/1625), [#1626](https://github.com/django-components/django-components/pull/1626), [#1633](https://github.com/django-components/django-components/pull/1633), and [#1634](https://github.com/django-components/django-components/pull/1634).