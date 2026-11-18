---
title: v0.142.3 (2025-10-17)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.142.3/
description: "- Fixed compatibility with older versions of django-template-partials. django-components now works with django-template-partials v23.3 and later. (See..."
---

# v0.142.3 (2025-10-17)

#### Fix

- Fixed compatibility with older versions of django-template-partials. django-components now works with django-template-partials v23.3 and later. (See [#1455](https://github.com/django-components/django-components/issues/1455))

#### Refactor

- `Component.View.public = True` is now optional.

    Before, to create component endpoints, you had to set both:

    1. HTTP handlers on `Component.View`
    2. `Component.View.public = True`.

    Now, you can set only the HTTP handlers, and the component will be automatically exposed
    when any of the HTTP handlers are defined.

    You can still explicitly expose/hide the component with `Component.View.public = True/False`.

    Before:


    ```py
    class MyTable(Component):
        class View:
            public = True

            def get(self, request):
                return self.render_to_response()

    url = get_component_url(MyTable)
    ```


    After:


    ```py
    class MyTable(Component):
        class View:
            def get(self, request):
                return self.render_to_response()

    url = get_component_url(MyTable)
    ```
