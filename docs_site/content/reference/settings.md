---
title: Settings
---

# Settings

All available settings for the `COMPONENTS` configuration object.

| Setting | Type | Default | Description |
|---|---|---|---|
| `autodiscover` | `bool` | `True` | Scan `INSTALLED_APPS` for components on startup |
| `dirs` | `list[str]` | `[]` | Extra directories to scan |
| `tag_formatter` | `str` | `"django_components..."` | Tag parsing strategy |
| `reload_on_file_change` | `bool` | `True` | Hot-reload in dev mode |
