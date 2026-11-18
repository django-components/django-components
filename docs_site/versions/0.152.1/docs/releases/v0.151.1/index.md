---
title: v0.151.1 (2026-06-25)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.151.1/
description: "- A multiline string value in a component tag no longer raises SyntaxError"
---

# v0.151.1 (2026-06-25)

#### Fix

- **A multiline string value in a component tag no longer raises `SyntaxError`**

    Passing a quoted string that spans multiple lines as a component input
    (for example an Alpine.js or hyperscript handler) raised
    `SyntaxError: unterminated string literal`:


    ```django
    {% component "button"
        _="on click
            set replyForm to closest <form />"
    %}{% endcomponent %}
    ```


    This affected plain strings only (those without `{{ }}` expressions) and
    was a regression introduced in `djc-core` v1.3.0. Such values render
    correctly again.

    This fix requires `djc-core>=1.3.1`, which is now the minimum version.