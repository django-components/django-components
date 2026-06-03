## Hot-reloading component files during development

When you edit a component's HTML template, JS, or CSS file while the dev server
is running, django_components automatically picks up the change on the next
request - no server restart needed.

This works out of the box with the default setting
[`reload_on_file_change`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.reload_on_file_change) `= "hot"`.

### How it works

When a file changes inside one of the
[`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
or
[`COMPONENTS.app_dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
directories, django_components clears its internal template/JS/CSS cache for
the affected components. The next render re-reads the file from disk.

The dev server itself keeps running - there is no restart, so the reload is
fast.

### Reload modes

The [`reload_on_file_change`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.reload_on_file_change)
setting accepts the following values:

| Value | Behavior |
|-------|----------|
| `True` or `"hot"` (default) | Clear the component cache on file change. No server restart. |
| `False` or `"off"` | No file watching. Changes require a manual server restart. |
| `"restart"` | Clear the cache **and** restart the dev server. Deprecated - use `"hot"` instead. |

!!! warning

    This setting should be used only in the dev environment!

### Example

```python
COMPONENTS = ComponentsSettings(
    reload_on_file_change="hot",  # This is the default
)
```

To disable file watching entirely:

```python
COMPONENTS = ComponentsSettings(
    reload_on_file_change="off",
)
```
