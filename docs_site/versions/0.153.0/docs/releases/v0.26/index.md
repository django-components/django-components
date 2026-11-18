---
title: v0.26 🚨📢 (2023-03-14)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.26/
description: "- Changed the syntax for {% slot %} tags. From now on, we separate defining a slot ({% slot %}) from filling a slot with content ({% fill %}). This..."
---

# v0.26 🚨📢 (2023-03-14)

#### BREAKING CHANGES

- Changed the syntax for `{% slot %}` tags. From now on, we separate defining a slot (`{% slot %}`) from filling a slot with content (`{% fill %}`). This means you will likely need to change a lot of slot tags to fill.

    We understand this is annoying, but it's the only way we can get support for nested slots that fill in other slots, which is a very nice feature to have access to. Hoping that this will feel worth it!