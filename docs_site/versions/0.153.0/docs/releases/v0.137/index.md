---
title: v0.137 (2025-04-09)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.137/
description: "- Each Component class now has a class_id attribute, which is unique to the component subclass."
---

# v0.137 (2025-04-09)

#### Feat

- Each Component class now has a `class_id` attribute, which is unique to the component subclass.

    NOTE: This is different from `Component.id`, which is unique to each rendered instance.

    To look up a component class by its `class_id`, use `get_component_by_class_id()`.

- It's now easier to create URLs for component views.

    Before, you had to call `Component.as_view()` and pass that to `urlpatterns`.

    Now this can be done for you if you set `Component.Url.public` to `True`:


    ```py
    class MyComponent(Component):
        class Url:
            public = True
        ...
    ```


    Then, to get the URL for the component, use `get_component_url()`:


    ```py
    from django_components import get_component_url

    url = get_component_url(MyComponent)
    ```


    This way you don't have to mix your app URLs with component URLs.

    Read more on [Component views and URLs](https://django-components.github.io/django-components/0.137/concepts/fundamentals/component_views_urls/).

- Per-component caching - Set `Component.Cache.enabled` to `True` to enable caching for a component.

    Component caching allows you to store the rendered output of a component. Next time the component is rendered
    with the same input, the cached output is returned instead of re-rendering the component.


    ```py
    class TestComponent(Component):
        template = "Hello"

        class Cache:
            enabled = True
            ttl = 0.1  # .1 seconds TTL
            cache_name = "custom_cache"

            # Custom hash method for args and kwargs
            # NOTE: The default implementation simply serializes the input into a string.
            #       As such, it might not be suitable for complex objects like Models.
            def hash(self, *args, **kwargs):
                return f"{json.dumps(args)}:{json.dumps(kwargs)}"

    ```


    Read more on [Component caching](https://django-components.github.io/django-components/0.137/concepts/advanced/component_caching/).

- `@djc_test` can now be called without first calling `django.setup()`, in which case it does it for you.

- Expose `ComponentInput` class, which is a typing for `Component.input`.

#### Deprecation

- Currently, view request handlers such as `get()` and `post()` methods can be defined
  directly on the `Component` class:


    ```py
    class MyComponent(Component):
        def get(self, request):
            return self.render_to_response()
    ```


    Or, nested within the `Component.View` class:


    ```py
    class MyComponent(Component):
        class View:
            def get(self, request):
                return self.render_to_response()
    ```


    In v1, these methods should be defined only on the `Component.View` class instead.

#### Refactor

- `Component.get_context_data()` can now omit a return statement or return `None`.