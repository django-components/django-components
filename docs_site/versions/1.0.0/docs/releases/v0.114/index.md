---
title: v0.114 (2024-11-27)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.114/
description: "⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See #791 and #789 and #818."
---

# v0.114 (2024-11-27)

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Prevent rendering Slot tags during fill discovery stage to fix a case when a component inside a slot
  fill tried to access provided data too early.