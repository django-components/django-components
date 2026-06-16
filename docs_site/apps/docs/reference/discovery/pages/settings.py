"""
Discovery for the Settings reference page (features 4.7, 4.34).

Each ``ComponentsSettings`` field is one entry (rendered by ``ReferenceSetting``).
The page also carries a defaults panel - a code block of all settings and their
default values, lifted from the ``--snippet:defaults--`` region of
``app_settings.py`` and cleaned up (comments stripped, ``Dynamic(lambda: x)``
unwrapped to ``x``). The panel goes in the preface so it renders ahead of the
per-setting entries.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings as django_settings
from django_components.app_settings import ComponentsSettings

from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage

_CLASS = "django_components.app_settings.ComponentsSettings"
_INTRO = (
    "Configure django-components through the `COMPONENTS` dict (or a "
    "[`ComponentsSettings`][ComponentsSettings] instance) in your Django settings. "
    "Every field below is one such setting."
)
_COMMENT_RE = re.compile(r"#\s+(?:type:|noqa)")
# Default values wrap dynamic ones as `Dynamic(lambda: x)`; show just `x` in docs.
_DYNAMIC_RE = re.compile(r"Dynamic\(lambda: (?P<code>.+)\)")


def discover() -> ReferencePage:
    """Build the Settings ``ReferencePage`` (defaults panel + per-field entries)."""
    entries = [
        ReferenceEntry(kind="setting", dotted_path=f"{_CLASS}.{field}", display_name=field)
        for field in ComponentsSettings._fields
    ]
    return ReferencePage(
        slug="settings",
        title="Settings",
        preface_md=f"{_INTRO}\n\n{_defaults_panel()}",
        entries=tuple(entries),
        layout="settings",
        description="API reference - the django-components settings.",
    )


def _defaults_panel() -> str:
    source = (Path(django_settings.REPO_ROOT) / "src" / "django_components" / "app_settings.py").read_text(
        encoding="utf-8"
    )
    snippet = source.split("--snippet:defaults--")[1].split("--endsnippet:defaults--")[0]
    cleaned = []
    for line in snippet.split("\n")[1:-1]:  # drop the marker-comment lines at both ends
        without_comment = _COMMENT_RE.split(line)[0].rstrip()
        cleaned.append(_DYNAMIC_RE.sub(r"\g<code>", without_comment))
    code = "\n".join(cleaned)
    return f"## Settings defaults\n\nAn overview of all settings and their default values:\n\n```py\n{code}\n```"
