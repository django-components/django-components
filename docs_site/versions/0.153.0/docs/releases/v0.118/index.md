---
title: v0.118 (2024-12-10)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.118/
description: "- Add support for context_processors and RenderContext inside component templates"
---

# v0.118 (2024-12-10)

#### Feat

- Add support for `context_processors` and `RenderContext` inside component templates

   `Component.render()` and `Component.render_to_response()` now accept an extra kwarg `request`.


    ```py
    def my_view(request)
        return MyTable.render_to_response(
            request=request
        )
    ```


   - When you pass in `request`, the component will use `RenderContext` instead of `Context`.
    Thus the context processors will be applied to the context.

   - NOTE: When you pass in both `request` and `context` to `Component.render()`, and `context` is already an instance of `Context`, the `request` kwarg will be ignored.