---
title: v0.90 (2024-08-18)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.90/
description: "- All tags (component, slot, fill, ...) now support \"self-closing\" or \"inline\" form, where you can omit the closing tag:"
---

# v0.90 (2024-08-18)

#### Feat

- All tags (`component`, `slot`, `fill`, ...) now support "self-closing" or "inline" form, where you can omit the closing tag:


    ```django
    {# Before #}
    {% component "button" %}{% endcomponent %}
    {# After #}
    {% component "button" / %}
    ```


- All tags now support the "dictionary key" or "aggregate" syntax (`kwarg:key=val`):


    ```django
    {% component "button" attrs:class="hidden" %}
    ```


- You can change how the components are written in the template with [TagFormatter](https://github.com/django-components/django-components#customizing-component-tags-with-tagformatter).

    The default is `django_components.component_formatter`:


    ```django
    {% component "button" href="..." disabled %}
        Click me!
    {% endcomponent %}
    ```


    While `django_components.component_shorthand_formatter` allows you to write components like so:


    ```django
    {% button href="..." disabled %}
        Click me!
    {% endbutton %}
    ```
