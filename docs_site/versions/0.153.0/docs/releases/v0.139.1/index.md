---
title: v0.139.1 (2025-04-20)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.139.1/
description: "- Fix compatibility of component caching with {% extend %} block (#1135)"
---

# v0.139.1 (2025-04-20)

#### Fix

- Fix compatibility of component caching with `{% extend %}` block ([#1135](https://github.com/django-components/django-components/issues/1135))

#### Refactor

- Component ID is now prefixed with `c`, e.g. `c123456`.

- When typing a Component, you can now specify as few or as many parameters as you want.


    ```py
    Component[Args]
    Component[Args, Kwargs]
    Component[Args, Kwargs, Slots]
    Component[Args, Kwargs, Slots, Data]
    Component[Args, Kwargs, Slots, Data, JsData]
    Component[Args, Kwargs, Slots, Data, JsData, CssData]
    ```


    All omitted parameters will default to `Any`.

- Added `typing_extensions` to the project as a dependency

- Multiple extensions with the same name (case-insensitive) now raise an error

- Extension names (case-insensitive) also MUST NOT conflict with existing Component class API.

    So if you name an extension `render`, it will conflict with the `render()` method of the `Component` class,
    and thus raise an error.