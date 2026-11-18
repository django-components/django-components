---
title: v0.116 (2024-12-06)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.116/
description: "⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See #791 and #789 and #818."
---

# v0.116 (2024-12-06)

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Fix the order of execution of JS scripts:
  - Scripts in `Component.Media.js` are executed in the order they are defined
  - Scripts in `Component.js` are executed AFTER `Media.js` scripts

- Fix compatibility with AlpineJS
  - Scripts in `Component.Media.js` are now again inserted as `<script>` tags
  - By default, `Component.Media.js` are inserted as synchronous `<script>` tags,
    so the AlpineJS components registered in the `Media.js` scripts will now again
    run BEFORE the core AlpineJS script.

  AlpineJS can be configured like so:

  Option 1 - AlpineJS loaded in `<head>` with `defer` attribute:

  ```html
  <html>
    <head>
      {% component_css_dependencies %}
      <script defer src="https://unpkg.com/alpinejs"></script>
    </head>
    <body>
      {% component 'my_alpine_component' / %}
      {% component_js_dependencies %}
    </body>
  </html>
  ```


  Option 2 - AlpineJS loaded in `<body>` AFTER `{% component_js_depenencies %}`:

  ```html
  <html>
      <head>
          {% component_css_dependencies %}
      </head>
      <body>
          {% component 'my_alpine_component' / %}
          {% component_js_dependencies %}

          <script src="https://unpkg.com/alpinejs"></script>
      </body>
  </html>
  ```
