---
title: Management Commands
---

# Management Commands

django-components ships several Django management commands.

## `startcomponent`

Scaffold a new component directory:

```bash
python manage.py startcomponent my_widget
```

Creates:

```text
components/my_widget/
    my_widget.py
    my_widget.html
    my_widget.css
    my_widget.js
```

## `lintcomponents`

Check all registered components for common issues:

```bash
python manage.py lintcomponents
```
