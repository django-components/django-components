---
title: v0.145.0 (2026-01-21)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.145.0/
description: "Rendering components is now ~20% faster, thanks to:"
---

# v0.145.0 (2026-01-21)

#### Perf

Rendering components is now ~20% faster, thanks to:

- using Rust-based template tag parsing
- skipping input validation in favour of on-exception handling

#### Feat

- `BaseNode` class now has the `filters` and `tags` attributes. These dictionaries keep track of what filters and tags can be used within the `{% %}` tag.

    Extensions can use these attributes to add custom filters and tags to the tag.

- When creating custom template tags with `BaseNode` class or `@template_tag` decorator, you now get an error when
  the tag name is the same as one of the flags:


    ```py
    class SlotNode(BaseNode):
        tag = "slot"
        allowed_flags = ["slot"]  # Raises!
    ```


#### Refactor

- In template, when a component tag has a positional argument
  after a keyword argument it now raises `SyntaxError` instead of `TypeError`.


    ```django
    {% mytag 'John' msg='Hello' 123 %}
    ```


- When a component tag receives multiple kwargs with the same name, it no longer raises `TypeError`.

  Instead, the later kwargs overwrite the earlier ones.


    ```django
    {% mytag 'John' x=123 x=456 %}
    ```


- All template tags (`{% component %}`, `{% slot %}`, etc.) now include the exact tag (as found in the template) in the error message when an error occurs:


    ```py
    TypeError: Error in mytag: missing 1 required keyword-only arguments: 'msg'
        1 | {% mytag 'John' %}
            ^^^^^^^^^^^^^^^^^^
    ```
