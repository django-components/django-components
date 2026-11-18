---
title: v0.146.0 (2026-01-23)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.146.0/
description: "django-components is now tested across all major browsers - Chromium, Firefox, WebKit."
---

# v0.146.0 (2026-01-23)

`django-components` is now tested across all major browsers - Chromium, Firefox, WebKit.

#### Deprecations 🚨📢

- In browser, `django-components` injects `Components` global JavaScript object.

    This object has been renamed to `DjangoComponents` because `Components` global is used in Firefox ([#1544](https://github.com/django-components/django-components/issues/1544))

    For backwards compatibility, the old object name `Components` is still available, and will be removed in v1.0.

#### Feat

- **Python expressions in template tags.** Evaluate Python code directly in template by wrapping expressions in parentheses:


    ```django
    {% component "button"
      disabled=(not editable)
      variant=(user.is_admin and 'danger' or 'primary')
    / %}
    ```


    Python expressions provide a Vue/React-like experience for writing component templates.

    These allow you to perform simple transformations like:

    - Negating booleans
    - Conditional expressions
    - Method calls
    - Arithmetic operations
    - And more...

    Read more in the [Python expressions documentation](https://django-components.github.io/django-components/0.146.0/concepts/fundamentals/template_tag_syntax#python-expressions).

- **Literal lists and dictionaries in template tags.** Pass structured data directly in templates:


    ```django
    {% component "table"
        headers=["Name", "Age", "Email"]
        data=[
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Jane", "age": 25, "email": "jane@example.com"},
        ]
    / %}
    ```


    Lists and dictionaries can contain the same values as template tag attributes:

    - Strings, numbers, booleans, and `None`
    - Python expressions
    - Template variables
    - Nested lists and dictionaries
    - Nested templates with `{{ }}` and `{% %}` syntax

    Each value can have filters applied to it.

    Read more in the [Literal lists and dictionaries documentation](https://django-components.github.io/django-components/0.146.0/concepts/fundamentals/template_tag_syntax#literal-lists-and-dictionaries).

#### Fix

- There was bug where, when you defined `Kwargs`, `Args`, `Slots`, etc, as `@dataclass`,
  and one of its fields was a dataclass object again, the nested dataclass was incorrectly
  converted to a dictionary, instead of being left as a dataclass instance.

    Before:


    ```py
    from dataclasses import dataclass
    from django_components.util.misc import to_dict

    @dataclass
    class User:
        name: str

    class MyTable(Component):
        @dataclass
        class Kwargs:
            user: User
            count: int

        def get_template_data(self, args, kwargs: Kwargs, slots, context):
            # INCORRECT!!! Should be `User(name="John")`
            assert kwargs.user == { "name": "John" }
    ```


#### Refactor

- Component's JS, CSS, and HTML template are now loaded independently.

    This means that accessing `Component.js` or `Component.css` no longer triggers template resolution.

    This should improve server startup time as fewer files need to be loaded up front.