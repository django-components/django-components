---
title: Installation
---

# Installation

Install django-components with your package manager of choice:

=== "uv"
    ```bash
    uv pip install django-components
    ```

=== "pip"
    ```bash
    pip install django-components
    ```

## Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    "django_components",
    ...
]
```

## Verify

```bash
python -c "import django_components; print(django_components.__version__)"
```

That's it. You're ready to create your first component.
