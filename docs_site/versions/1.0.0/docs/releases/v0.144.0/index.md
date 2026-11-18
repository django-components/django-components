---
title: v0.144.0 (2026-01-18)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.144.0/
description: "- Component URLs can now be customized with route parameters."
---

# v0.144.0 (2026-01-18)

#### Feat

- Component URLs can now be customized with route parameters.

    - Each component class has its own URL that triggers the component's HTTP handlers.
    - By default, the route path is `components/{component.class_id}/`.
    - You can now customize the route path by overriding [`Component.View.get_route_path()`](https://django-components.github.io/django-components/0.144.0/reference/api#django_components.ComponentView.get_route_path).


    ```py
    from django_components import Component, get_component_url

    class UserProfile(Component):
        class View:
            @classmethod
            def get_route_path(cls):
                return f"users/<str:username>/<int:user_id>/"

            def get(self, request, username: str, user_id: int, **kwargs):
                return UserProfile.render_to_response()

    # Get the URL with route parameters filled
    url = get_component_url(
        UserProfile,
        kwargs={"username": "john", "user_id": 42},
    )
    # /components/ext/view/users/john/42/
    ```


#### Refactor

- [`get_component_url()`](https://django-components.github.io/django-components/0.144.0/reference/api#django_components.get_component_url) now accepts extra `args` and `kwargs` arguments.
These arguments are passed to Django's `reverse()` function.