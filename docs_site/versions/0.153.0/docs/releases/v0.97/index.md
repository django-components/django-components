---
title: v0.97 (2024-09-06)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.97/
description: "- Fixed template caching. You can now also manually create cached templates with cached_template()"
---

# v0.97 (2024-09-06)

#### Fix

- Fixed template caching. You can now also manually create cached templates with [`cached_template()`](https://github.com/django-components/django-components#template_cache_size---tune-the-template-cache)

#### Refactor

- The previously undocumented `get_template` was made private.

- In it's place, there's a new `get_template`, which supersedes `get_template_string` (will be removed in v1). The new `get_template` is the same as `get_template_string`, except
  it allows to return either a string or a Template instance.

- You now must use only one of `template`, `get_template`, `template_name`, or `get_template_name`.