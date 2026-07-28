"""
Glue between Django settings and the (settings-agnostic) guardrail harness.

Assembles a GuardContext - content/examples/static dirs, the nav file, the
example registry, and a SiteIndex built from the given output directory - so the
management commands can run the full guard suite with one call.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from apps.docs.build.guards import GuardContext
from apps.docs.build.site_index import SiteIndex
from apps.docs.examples import get_example_registry


def _static_dir() -> Path:
    dirs = getattr(settings, "STATICFILES_DIRS", None)
    if dirs:
        return Path(dirs[0])
    return Path(settings.BASE_DIR) / "static"


def make_context(build_dir: Path, *, content_dir: Path | None = None) -> GuardContext:
    """Build a GuardContext for the guardrail suite over a built site."""
    content = content_dir or settings.CONTENT_DIR
    return GuardContext(
        content_dir=content,
        examples_dir=settings.EXAMPLES_DIR,
        nav_path=content / "_nav.yml",
        static_dir=_static_dir(),
        site_index=SiteIndex(build_dir),
        example_registry=get_example_registry(),
    )


def make_versions_context(versions_root: Path | None = None) -> GuardContext:
    """
    Build a GuardContext for the version guards (VERSION_GUARDS).

    Only `versions_root` is meaningful here; the content/static fields are filled
    from settings to satisfy the dataclass but go unused by the version guards.
    """
    content = settings.CONTENT_DIR
    return GuardContext(
        content_dir=content,
        examples_dir=settings.EXAMPLES_DIR,
        nav_path=content / "_nav.yml",
        static_dir=_static_dir(),
        versions_root=versions_root or settings.VERSIONS_DIR,
    )
