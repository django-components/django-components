---
title: v0.149.0 (2026-04-25)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.149.0/
description: "- Django's built-in {% cache %} tag now works correctly inside component templates"
---

# v0.149.0 (2026-04-25)

#### Fix

- **Django's built-in `{% cache %}` tag now works correctly inside component templates**

    When `{% cache %}` wraps `{% component %}` inside another component, django-components now caches the fully rendered HTML instead of a first-pass placeholder.

    This fixes cache hits for nested components and also preserves compatibility when explicitly loading Django's cache tag library with `{% load cache %}`.

    See [#1619](https://github.com/django-components/django-components/pull/1619).

- Fixed memory leaks in component caching and request context-processor data reuse.

    This release cleans up stale entries in `CacheExtension.render_id_to_cache_key` and reuses cached request context-processor data without retaining unnecessary references.

    See [#1613](https://github.com/django-components/django-components/pull/1613).

#### Refactor

- Improved CI and release compatibility.

    The test matrix is 10x faster, documentation builds now avoid the Pygments 2.20 mkdocstrings regression, and several development dependencies were updated.

    See [#1623](https://github.com/django-components/django-components/pull/1623) and [#1611](https://github.com/django-components/django-components/pull/1611).