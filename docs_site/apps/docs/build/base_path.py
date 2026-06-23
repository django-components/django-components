"""
Base-path rewriting for subpath deploys (e.g. GitHub *project* Pages).

The site chrome emits root-absolute URLs (`/static`, `/docs`, `/v`, ...), which
assume the site is served at the domain root. For a deploy under a subpath like
`/django-components/`, those URLs must be prefixed with the base path. This
post-build pass rewrites root-absolute URL attributes in our own HTML output and
injects a `<meta name="djc-base-path">` tag so base-path-aware JS (search result
links) can resolve too.

It is a **no-op when no base path is configured** (`settings.SITE_BASE_PATH = ""`,
the default), so the normal root-served build is completely unaffected. Frozen
gh-pages imports are never passed through here - they use relative links and are
copied verbatim - so only the new builder's output is touched.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# URL-bearing attributes whose root-absolute values must move under the base path.
# Includes the example-interactivity attributes (htmx / Alpine / JS loaders) so
# the runnable examples keep loading their assets under the subpath.
_URL_ATTRS = (
    "href",
    "src",
    "action",
    "formaction",
    "poster",
    "data-pagefind-path",
    "data-js-url",
    "data-alpine-url",
    "hx-get",
    "hx-post",
    "hx-put",
    "hx-delete",
    "hx-patch",
)


def _compile(base: str) -> re.Pattern[str]:
    # Matches `attr=/x` or `attr="/x"` / `attr='/x'`, but NOT `//host`
    # (protocol-relative), NOT full URLs (they start with a scheme, not `/`), and
    # NOT a value already under the base path (idempotency guard).
    already = re.escape(base.lstrip("/"))
    attrs = "|".join(_URL_ATTRS)
    return re.compile(rf'(\b(?:{attrs})=)(["\']?)/(?!/)(?!{already}/)')


def apply_base_path(output_dir: Path, base: str) -> int:
    """
    Prefix root-absolute URL attributes in every ``*.html`` under ``output_dir``
    with ``base`` (e.g. ``/django-components``) and inject the base-path meta tag.
    Returns the number of files changed. No-op when ``base`` is empty.
    """
    if not base:
        return 0

    pattern = _compile(base)
    replacement = rf"\1\2{base}/"
    meta = f'<head><meta name="djc-base-path" content="{base}">'
    changed = 0
    for html in output_dir.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        new = pattern.sub(replacement, text)
        # So base-path-aware JS (e.g. pagefind result links) can read the prefix.
        if "djc-base-path" not in new:
            new = new.replace("<head>", meta, 1)
        if new != text:
            html.write_text(new, encoding="utf-8")
            changed += 1
    return changed
