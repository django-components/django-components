"""
Discovery for the URLs reference page (features 4.11, 4.29, 4.50).

Port of ``gen_reference_urls``: a flat bullet list of the URL patterns that
``django_components.urls`` contributes. There are no per-symbol entries to
introspect here (a URL route has no docstring), so the page is realized as
preface markdown with the list inlined - the "ReferenceURLPattern" renderer is
just a markdown bullet.

The list is read from ``dependencies.urlpatterns`` (the library's own core
routes) rather than the live ``django_components.urls.urlpatterns``. The latter
also picks up the per-component View endpoints that any loaded component with a
public ``View`` registers at import time - which, in this docs project, means all
the example components. Those are app-specific, not part of the library's URL API,
so they must not appear in the reference.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.urls import URLPattern, URLResolver

from apps.docs.reference.discovery.kinds import ReferencePage
from django_components.dependencies import urlpatterns as core_urlpatterns

_PREFACE = """\
Below are the URL patterns that `django_components.urls` adds.

Components that expose a public `View` additionally get their own endpoint (via
the view extension); retrieve it with [`get_component_url()`][get_component_url]
rather than hard-coding it.

See [Installation](../getting_started/installation.md#adding-support-for-js-and-css)
on how to add these URLs to your Django project.

Django components already prefixes all URLs with `components/`. So when you are
adding the URLs to `urlpatterns`, you can use an empty string as the first argument:

```python
from django.urls import include, path

urlpatterns = [
    ...
    path("", include("django_components.urls")),
]
```
"""


def discover() -> ReferencePage:
    """Build the URLs ``ReferencePage`` from the library's own (core) URL routes."""
    # `components/` is the prefix django_components.urls mounts these under.
    bullets = "\n".join(f"- `{path}`" for path in _list_urls(core_urlpatterns, prefix="components/"))
    preface = f"{_PREFACE}\n## List of URLs\n\n{bullets}"
    return ReferencePage(
        slug="urls",
        title="URLs",
        preface_md=preface,
        entries=(),
        description="API reference - URLs.",
    )


def _list_urls(patterns: Iterable[URLPattern | URLResolver], prefix: str = "") -> list[str]:
    """Recursively collect the full path string of every URL pattern (depth-first)."""
    collected: list[str] = []
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            collected.extend(_list_urls(pattern.url_patterns, prefix + str(pattern.pattern)))
        elif isinstance(pattern, URLPattern):
            collected.append(prefix + str(pattern.pattern))
    return collected
