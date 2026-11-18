---
title: v0.136 🚨📢 (2025-04-05)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.136/
description: "- Component input validation was moved to a separate extension djc-ext-pydantic."
---

# v0.136 🚨📢 (2025-04-05)

#### BREAKING CHANGES 🚨📢

- Component input validation was moved to a separate extension [`djc-ext-pydantic`](https://github.com/django-components/djc-ext-pydantic).

    If you relied on components raising errors when inputs were invalid, you need to install `djc-ext-pydantic` and add it to extensions:


    ```python
    # settings.py
    COMPONENTS = {
        "extensions": [
            "djc_pydantic.PydanticExtension",
        ],
    }
    ```


#### Fix

- Make it possible to resolve URLs added by extensions by their names