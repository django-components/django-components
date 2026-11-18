---
title: v0.130 (2025-02-20)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.130/
description: "- Access the HttpRequest object under Component.request."
---

# v0.130 (2025-02-20)

#### Feat

- Access the HttpRequest object under `Component.request`.

    To pass the request object to a component, either:
    - Render a template or component with `RequestContext`,
    - Or set the `request` kwarg to `Component.render()` or `Component.render_to_response()`.

    Read more on [HttpRequest](https://django-components.github.io/django-components/0.130/concepts/fundamentals/http_request/).

- Access the context processors data under `Component.context_processors_data`.

    Context processors data is available only when the component has access to the `request` object,
    either by:
    - Passing the request to `Component.render()` or `Component.render_to_response()`,
    - Or by rendering a template or component with `RequestContext`,
    - Or being nested in another component that has access to the request object.

    The data from context processors is automatically available within the component's template.

    Read more on [HttpRequest](https://django-components.github.io/django-components/0.130/concepts/fundamentals/http_request/).