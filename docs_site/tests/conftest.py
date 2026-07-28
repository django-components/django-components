"""
Pytest bootstrap for the docs-site build tests.

These tests live outside the package's main `tests/` suite (they exercise the
internal docs builder, a separate Django project). Run them with:

    cd docs_site && uv run pytest tests/

This conftest puts `docs_site/` on sys.path and configures Django so the tests
can import `apps.docs.build.*`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

DOCS_SITE = Path(__file__).resolve().parent.parent
if str(DOCS_SITE) not in sys.path:
    sys.path.insert(0, str(DOCS_SITE))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docs_site.settings")

import django  # noqa: E402

django.setup()
