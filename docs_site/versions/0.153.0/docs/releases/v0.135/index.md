---
title: v0.135 (2025-03-31)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.135/
description: "- Add defaults for the component inputs with the Component.Defaults nested class. Defaults
  are applied if the argument is not given, or if it set to..."
---

# v0.135 (2025-03-31)

#### Feat

- Add defaults for the component inputs with the `Component.Defaults` nested class. Defaults
  are applied if the argument is not given, or if it set to `None`.

  For lists, dictionaries, or other objects, wrap the value in `Default()` class to mark it as a factory
  function:


    ```python
    from django_components import Default

    class Table(Component):
        class Defaults:
            position = "left"
            width = "200px"
            options = Default(lambda: ["left", "right", "center"])

        def get_context_data(self, position, width, options):
            return {
                "position": position,
                "width": width,
                "options": options,
            }

    # `position` is used as given, `"right"`
    # `width` uses default because it's `None`
    # `options` uses default because it's missing
    Table.render(
        kwargs={
            "position": "right",
            "width": None,
        }
    )
    ```


- `{% html_attrs %}` now offers a Vue-like granular control over `class` and `style` HTML attributes,
where each class name or style property can be managed separately.


    ```django
    {% html_attrs
        class="foo bar"
        class={"baz": True, "foo": False}
        class="extra"
    %}
    ```



    ```django
    {% html_attrs
        style="text-align: center; background-color: blue;"
        style={"background-color": "green", "color": None, "width": False}
        style="position: absolute; height: 12px;"
    %}
    ```


    Read more on [HTML attributes](https://django-components.github.io/django-components/0.135/concepts/fundamentals/html_attributes/).

#### Fix

- Fix compat with Windows when reading component files ([#1074](https://github.com/django-components/django-components/issues/1074))
- Fix resolution of component media files edge case ([#1073](https://github.com/django-components/django-components/issues/1073))