---
title: v0.128 (2025-02-04)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.128/
description: "- Configurable cache - Set COMPONENTS.cache to change where and how django-components caches JS and CSS files. (#946)"
---

# v0.128 (2025-02-04)

#### Feat

- Configurable cache - Set [`COMPONENTS.cache`](https://django-components.github.io/django-components/0.128/reference/settings/#django_components.app_settings.ComponentsSettings.cache) to change where and how django-components caches JS and CSS files. ([#946](https://github.com/django-components/django-components/pull/946))

    Read more on [Caching](https://django-components.github.io/django-components/0.128/guides/setup/caching).

- Highlight coponents and slots in the UI - We've added two boolean settings [`COMPONENTS.debug_highlight_components`](https://django-components.github.io/django-components/0.128/reference/settings/#django_components.app_settings.ComponentsSettings.debug_highlight_components) and [`COMPONENTS.debug_highlight_slots`](https://django-components.github.io/django-components/0.128/reference/settings/#django_components.app_settings.ComponentsSettings.debug_highlight_slots), which can be independently set to `True`. First will wrap components in a blue border, the second will wrap slots in a red border. ([#942](https://github.com/django-components/django-components/pull/942))

    Read more on [Troubleshooting](https://django-components.github.io/django-components/0.128/guides/other/troubleshooting/#component-and-slot-highlighting).

#### Refactor

- Removed use of eval for node validation ([#944](https://github.com/django-components/django-components/pull/944))

#### Perf

- Components can now be infinitely nested. ([#936](https://github.com/django-components/django-components/pull/936))

- Component input validation is now 6-7x faster on CPython and PyPy. This previously made up 10-30% of the total render time. ([#945](https://github.com/django-components/django-components/pull/945))