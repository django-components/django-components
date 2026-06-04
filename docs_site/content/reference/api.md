---
title: API Reference
---

# API Reference

This page will be auto-generated from Python docstrings in Phase 4.
For now it's a placeholder demonstrating a flat (1-level) nav section.

## Component

The base class for all components.

```python
from django_components import Component, register

@register("my_component")
class MyComponent(Component):
    template = "<div>Hello {{ name }}</div>"
```

## ComponentRegistry

Manages component registration and lookup.

## ComponentsSettings

Configuration dataclass for the `COMPONENTS` Django setting.
