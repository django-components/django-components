---
title: v0.141.1 (2025-07-03)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.141.1/
description: "- Components' JS and CSS scripts (e.g. from Component.js or Component.js_file) are now cached at class creation time."
---

# v0.141.1 (2025-07-03)

#### Fix

- Components' JS and CSS scripts (e.g. from `Component.js` or `Component.js_file`) are now cached at class creation time.

    This means that when you now restart the server while having a page opened in the browser,
    the JS / CSS files are immediately available.

    Previously, the JS/CSS were cached only after the components were rendered. So you had to reload
    the page to trigger the rendering, in order to make the JS/CSS files available.

- Fix the default cache for JS / CSS scripts to be unbounded.

    Previously, the default cache for the JS/CSS scripts (`LocMemCache`) was accidentally limited to 300 entries (~150 components).

- Do not send `template_rendered` signal when rendering a component with no template. ([#1277](https://github.com/django-components/django-components/issues/1277))