---
title: v0.111 (2024-11-26)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.111/
description: "⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See #791 and #789 and #818."
---

# v0.111 (2024-11-26)

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Prevent rendering Component tags during fill discovery stage to fix a case when a component inside the default slot
  tried to access provided data too early.