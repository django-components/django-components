---
title: v0.142.0 (2025-10-05)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.142.0/
description: "⚠️ This version is broken, please update to v0.142.1 ⚠️"
---

# v0.142.0 (2025-10-05)

⚠️ This version is broken, please update to v0.142.1 ⚠️



#### Feat

- New built-in component [`ErrorFallback`](https://django-components.github.io/django-components/0.142.0/reference/components/)

    Use `ErrorFallback` to catch errors and display a fallback content instead.

    This is similar to React's [`ErrorBoundary`](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
    component.

    Either pass the fallback as a kwarg:


    ```django
    {% component "error_fallback" fallback="Oops, something went wrong" %}
        {% component "table" / %}
    {% endcomponent %}
    ```


    Or use the full `fallback` slot:


    ```django
    {% component "error_fallback" %}
        {% fill "content" %}
            {% component "table" / %}
        {% endfill %}
        {% fill "fallback" data="data" %}
            <p>Oops, something went wrong</p>
            {% button href="/report-error" %}
                Report error
            {% endbutton %}
        {% endfill %}
    {% endcomponent %}
    ```


- Wrap the template rendering in `Component.on_render()` in a lambda function.

    When you wrap the rendering call in a lambda function, and the rendering fails,
    the error will be yielded back in the `(None, Exception)` tuple.

    Before:


    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            try:
                intermediate = template.render(context)
                html, error = yield intermediate
            except Exception as e:
                html, error = None, e
    ```


    After:


    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            html, error = yield lambda: template.render(context)
    ```


- Multiple yields in `Component.on_render()` - You can now yield multiple times within the same `on_render` method for complex rendering scenarios.


    ```py
    class MyTable(Component):
        def on_render(self, context, template):
            # First yield
            with context.push({"mode": "header"}):
                header_html, header_error = yield lambda: template.render(context)

            # Second yield
            with context.push({"mode": "body"}):
                body_html, body_error = yield lambda: template.render(context)

            # Third yield
            footer_html, footer_error = yield "Footer content"

            # Process all results
            if header_error or body_error or footer_error:
                return "Error occurred during rendering"

            return f"{header_html}\n{body_html}\n{footer_html}"
    ```


    Each yield operation is independent and returns its own `(html, error)` tuple, allowing you to handle each rendering result separately.

#### Fix

- Improve formatting when an exception is raised while rendering components. Error messages with newlines should now be properly formatted.

- Add missing exports for `OnComponentRenderedContext`, `OnSlotRenderedContext`, `OnTemplateCompiledContext`, `OnTemplateLoadedContext`.

#### Refactor

- Changes to how `get_component_url()` handles query parameters:
    - `True` values are now converted to boolean flags (e.g. `?enabled` instead of `?enabled=True`).
    - `False` and `None` values are now filtered out.


    ```py
    url = get_component_url(
        MyComponent,
        query={"abc": 123, "enabled": True, "debug": False, "none_key": None},
    )
    # /components/ext/view/components/c1ab2c3?abc=123&enabled
    ```


#### Docs

- New [people page](https://django-components.github.io/django-components/docs/community/people/) to celebrate the contributors and authors!