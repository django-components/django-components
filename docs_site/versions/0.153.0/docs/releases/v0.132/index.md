---
title: v0.132 (2025-03-22)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.132/
description: "⚠️ Attention ⚠️ - Please update to v0.134 to fix bugs introduced in v0.132."
---

# v0.132 (2025-03-22)

⚠️ Attention ⚠️ - Please update to v0.134 to fix bugs introduced in v0.132.

#### Feat

- Allow to use glob patterns as paths for additional JS / CSS in
  `Component.Media.js` and `Component.Media.css`


    ```py
    class MyComponent(Component):
        class Media:
            js = ["*.js"]
            css = ["*.css"]
    ```


#### Fix

- Fix installation for Python 3.13 on Windows.