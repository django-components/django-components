# Component Analytics

Use the [`Component.on_render_after()`](../../reference/api.md#django_components.Component.on_render_after) hook to track component analytics, such as capturing errors for a service like Sentry or other monitoring.

![Analytics example](./images/analytics.png)

## Error tracking components

You can create a wrapper component that uses the [`Component.on_render_after()`](../../reference/api.md#django_components.Component.on_render_after) hook to inspect the `error` object. If an error occurred during the rendering of its children, you can capture and send it to your monitoring service.

```django
{% component "sentry_error_tracker" %}
    {% component "api_widget" simulate_error=True / %}
{% endcomponent %}
```

The same hook can be used to track both successes and failures, allowing you to monitor the reliability of a component.

```django
{% component "success_rate_tracker" %}
    {% component "api_widget" simulate_error=False / %}
{% endcomponent %}
```

## Error tracking extension

Capturing analytics through components is simple, but limiting:

- You can't access metadata nor state of the component that errored
- Component will capture at most one error
- You must remember to call the component that captures the analytics

Instead, you can define the analytics logic as an [extension](../../concepts/advanced/extensions.md). This will allow us to capture all errors, without polluting the UI.

To do that, we can use the [`on_component_rendered()`](../../reference/extension_hooks.md#django_components.extension.ComponentExtension.on_component_rendered) hook to capture all errors.

```python
from django_components.extension import ComponentExtension, OnComponentRenderedContext

class ErrorTrackingExtension(ComponentExtension):
    name = "sentry_error_tracker"

    def on_component_rendered(self, ctx: OnComponentRenderedContext):
        if ctx.error:
            print(f"SENTRY: Captured error in component {ctx.component.name}: {ctx.error}")
```

Don't forget to register the extension:

```python
COMPONENTS = {
    "extensions": [
        ErrorTrackingExtension,
    ],
}
```

## Definition

```djc_py
--8<-- "docs/examples/analytics/component.py"
```

## Example

To see the component in action, you can set up a view and a URL pattern as shown below.

### `views.py`

```djc_py
--8<-- "docs/examples/analytics/page.py"
```

### `urls.py`

```python
from django.urls import path

from examples.pages.analytics import AnalyticsPage

urlpatterns = [
    path("examples/analytics", AnalyticsPage.as_view(), name="analytics"),
]
```
