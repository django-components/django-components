---
title: v0.124 (2025-01-07)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.124/
description: "- Instead of inlining the JS and CSS under Component.js and Component.css, you can move
    them to their own files, and link the JS/CSS files with..."
---

# v0.124 (2025-01-07)

#### Feat

- Instead of inlining the JS and CSS under `Component.js` and `Component.css`, you can move
    them to their own files, and link the JS/CSS files with `Component.js_file`  and `Component.css_file`.

    Even when you specify the JS/CSS with `Component.js_file` or `Component.css_file`, then you can still
    access the content under `Component.js` or `Component.css` - behind the scenes, the content of the JS/CSS files
    will be set to `Component.js` / `Component.css` upon first access.

    The same applies to `Component.template_file`, which will populate `Component.template` upon first access.

    With this change, the role of `Component.js/css` and the JS/CSS in `Component.Media` has changed:

    - The JS/CSS defined in `Component.js/css` or `Component.js/css_file` is the "main" JS/CSS
    - The JS/CSS defined in `Component.Media.js/css` are secondary or additional

    See the updated ["Getting Started" tutorial](https://django-components.github.io/django-components/0.124/getting_started/adding_js_and_css/)

#### Refactor

- The canonical way to define a template file was changed from `template_name` to `template_file`, to align with the rest of the API.

    `template_name` remains for backwards compatibility. When you get / set `template_name`,
    internally this is proxied to `template_file`.

- The undocumented `Component.component_id` was removed. Instead, use `Component.id`. Changes:

    - While `component_id` was unique every time you instantiated `Component`, the new `id` is unique
    every time you render the component (e.g. with `Component.render()`)
    - The new `id` is available only during render, so e.g. from within `get_context_data()`

- Component's HTML / CSS / JS are now resolved and loaded lazily. That is, if you specify `template_name`/`template_file`,
  `js_file`, `css_file`, or `Media.js/css`, the file paths will be resolved only once you:

    1. Try to access component's HTML / CSS / JS, or
    2. Render the component.

    Read more on [Accessing component's HTML / JS / CSS](https://django-components.github.io/django-components/0.124/concepts/fundamentals/defining_js_css_html_files/#customize-how-paths-are-rendered-into-html-tags).

- Component inheritance:

    - When you subclass a component, the JS and CSS defined on parent's `Media` class is now inherited by the child component.
    - You can disable or customize Media inheritance by setting `extend` attribute on the `Component.Media` nested class. This work similarly to Django's [`Media.extend`](https://docs.djangoproject.com/en/5.2/topics/forms/media/#extend).
    - When child component defines either `template` or `template_file`, both of parent's `template` and `template_file` are ignored. The same applies to `js_file` and `css_file`.

- Autodiscovery now ignores files and directories that start with an underscore (`_`), except `__init__.py`

- The [Signals](https://docs.djangoproject.com/en/5.2/topics/signals/) emitted by or during the use of django-components are now documented, together the `template_rendered` signal.