# Settings

You can configure django_components with a global `COMPONENTS` variable in your Django settings file, e.g. `settings.py`.
By default you don't need it set, there are resonable [defaults](#settings-defaults).

To configure the settings you can instantiate [`ComponentsSettings`](api.md#django_components.ComponentsSettings)
for validation and type hints. Or, for backwards compatibility, you can also use plain dictionary:

```python
# settings.py
from django_components import ComponentsSettings

COMPONENTS = ComponentsSettings(
    autodiscover=True,
    ...
)

# or

COMPONENTS = {
    "autodiscover": True,
    ...
}
```
