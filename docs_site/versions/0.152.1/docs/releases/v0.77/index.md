---
title: v0.77 🚨📢 (2024-05-23)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.77/
description: "- The syntax for accessing default slot content has changed from"
---

# v0.77 🚨📢 (2024-05-23)

#### BREAKING

- The syntax for accessing default slot content has changed from


    ```django
    {% fill "my_slot" as "alias" %}
        {{ alias.default }}
    {% endfill %}

    ```


    to


    ```django
    {% fill "my_slot" default="alias" %}
        {{ alias }}
    {% endfill %}
    ```
