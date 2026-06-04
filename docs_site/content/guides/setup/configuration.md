---
title: Configuration
---

# Configuration

django-components is configured via `COMPONENTS` in your Django settings:

```python
from django_components import ComponentsSettings

COMPONENTS = ComponentsSettings(
    autodiscover=True,
    dirs=["components"],
)
```

## Key settings

| Setting | Default | Description |
|---|---|---|
| `autodiscover` | `True` | Auto-discover components in `INSTALLED_APPS` |
| `dirs` | `[]` | Additional directories to scan for components |
| `tag_formatter` | `"django_components.component_formatter"` | How `{% component %}` tags are parsed |

## Template loaders

Add the django-components template loader to your settings:

```python
TEMPLATES = [
    {
        "OPTIONS": {
            "loaders": [
                "django_components.template_loader.Loader",
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]
```

!!! note
    The component loader must come before Django's default loaders so component
    templates are found first.
