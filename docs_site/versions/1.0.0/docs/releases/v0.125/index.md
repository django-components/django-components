---
title: v0.125 (2025-01-22)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.125/
description: "⚠️ Attention ⚠️ - We migrated from EmilStenstrom/django-components to django-components/django-components."
---

# v0.125 (2025-01-22)

⚠️ Attention ⚠️ - We migrated from `EmilStenstrom/django-components` to `django-components/django-components`.

**Repo name and documentation URL changed. Package name remains the same.**

If you see any broken links or other issues, please report them in [#922](https://github.com/django-components/django-components/issues/922).

#### Feat

- `@template_tag` and `BaseNode` - A decorator and a class that allow you to define
  custom template tags that will behave similarly to django-components' own template tags.

  Read more on [Template tags](https://django-components.github.io/django-components/0.125/concepts/advanced/template_tags/).

  Template tags defined with `@template_tag` and `BaseNode` will have the following features:

  - Accepting args, kwargs, and flags.

  - Allowing literal lists and dicts as inputs as:

     `key=[1, 2, 3]` or `key={"a": 1, "b": 2}`
  - Using template tags tag inputs as:

    `{% my_tag key="{% lorem 3 w %}" / %}`
  - Supporting the flat dictionary definition:

     `attr:key=value`
  - Spreading args and kwargs with `...`:

     `{% my_tag ...args ...kwargs / %}`
  - Being able to call the template tag as:

     `{% my_tag %} ... {% endmy_tag %}` or `{% my_tag / %}`


#### Refactor

- Refactored template tag input validation. When you now call template tags like
  `{% slot %}`, `{% fill %}`, `{% html_attrs %}`, and others, their inputs are now
  validated the same way as Python function inputs are.

    So, for example


    ```django
    {% slot "my_slot" name="content" / %}
    ```


    will raise an error, because the positional argument `name` is given twice.

    NOTE: Special kwargs whose keys are not valid Python variable names are not affected by this change.
    So when you define:


    ```django
    {% component data-id=123 / %}
    ```


    The `data-id` will still be accepted as a valid kwarg, assuming that your `get_context_data()`
    accepts `**kwargs`:


    ```py
    def get_context_data(self, **kwargs):
        return {
            "data_id": kwargs["data-id"],
        }
    ```
