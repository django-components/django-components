---
title: v0.115 (2024-12-02)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.115/
description: "⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See #791 and #789 and #818."
---

# v0.115 (2024-12-02)

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Fix integration with ManifestStaticFilesStorage on Windows by resolving component filepaths
 (like `Component.template_name`) to POSIX paths.