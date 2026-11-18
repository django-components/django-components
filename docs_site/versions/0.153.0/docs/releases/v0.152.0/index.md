---
title: v0.152.0
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.152.0/
description: "- New tag {% attrs %}, more powerful alternative to {% html_attrs %}"
---

# v0.152.0

#### Feature

- **New tag `{% attrs %}`, more powerful alternative to `{% html_attrs %}`**

    The new `{% attrs %}` tag accepts dicts, optionally lists or nested lists of dicts.


    ```django
    {% attrs some_dict {"data-extra": 123} %}
    ```


    Merging: Old `{% html_attrs %}` merged all attributes. `{% attrs %}` merges only
    `class` and `style`. For other attributes, the last one wins. This is now aligned with [Vue's behavior](https://vuejs.org/guide/essentials/class-and-style.html).

    `class` and `style` still accept strings, dicts, and lists:


    ```django
    {% attrs {
        "class": ["rounded", {"shadow": True}],
        "style": ["color: red;", {"color": "blue"}],
    } %}
    ```


    Rendered directly, the result is an escaped, space-delimited HTML attribute string:


    ```django
    <div {% attrs {"id": "1"} {"data-extra": 123} %}></div>
              ↓
    <div id="1" data-extra="123"></div>
    ```


    When `{% attrs %}` is the only tag in component's input, the component receives the dictionary without serialization:
    

    ```django
    {% component "table"
        table_attrs="{% attrs [base_attrs, {'class': 'compact'}] %}"
    / %}
    ```


    Use the `compose_attrs()` helper in Python.

    The existing `{% html_attrs %}` tag and `merge_attributes()` helper keep their old behavior.
    
    `format_attributes()` and the new attrs tag now reject invalid runtime HTML attribute names.

    See [#1703](https://github.com/django-components/django-components/issues/1703).