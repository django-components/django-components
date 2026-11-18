---
title: v0.22 (2022-07-26)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.22/
description: "- All files inside components subdirectores are autoimported to simplify setup."
---

# v0.22 (2022-07-26)

#### Feat

- All files inside components subdirectores are autoimported to simplify setup.

    An existing project might start to get `AlreadyRegistered` errors because of this. To solve this, either remove your custom loading of components, or set `"autodiscover": False` in `settings.COMPONENTS`.