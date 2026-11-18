---
title: v0.143.1 (2025-11-09)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.143.1/
description: "- Make django-component's position in Django's INSTALLED_APPS more lenient by not calling Django's URLResolver.populate() if URLResolver hasn't been..."
---

# v0.143.1 (2025-11-09)

#### Fix

- Make django-component's position in Django's `INSTALLED_APPS` more lenient by not calling Django's `URLResolver._populate()` if `URLResolver` hasn't been resolved before ([See thread](https://discord.com/channels/1417824875023700000/1417825089675853906/1437034834118840411)).

#### Refactor

- Components now raise error if template data overwrites variables from `context_processors` ([#1482](https://github.com/django-components/django-components/issues/1482))