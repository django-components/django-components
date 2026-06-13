"""
The griffe loader for the API reference.

Loads ``django_components`` once with griffe (with our two extensions applied)
and resolves public dotted paths to griffe objects. ``force_inspection=True`` is
used because several documented attributes are set at runtime by metaclasses
(e.g. ``BaseNode._signature``, ``ComponentNode.allowed_flags``) and are invisible
to static analysis - confirmed needed in spike 5 section 2.

Django must be configured before this runs (griffe imports the package), which it
always is inside the build command / dev server.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import griffe
from django.conf import settings

from apps.docs.griffe_extensions import build_extensions

PACKAGE = "django_components"


@lru_cache(maxsize=1)
def load_package() -> griffe.Module:
    """Load (and cache) the ``django_components`` griffe module with extensions applied."""
    # Search src/ explicitly so we document the in-repo source, matching the old
    # mkdocs `paths: [src]`. This also makes griffe's file paths point at the
    # working tree rather than some other installed copy.
    search_paths = [str(Path(settings.REPO_ROOT) / "src")]
    pkg = griffe.load(
        PACKAGE,
        force_inspection=True,
        extensions=build_extensions(),
        search_paths=search_paths,
    )
    # griffe.load() is typed as returning Object | Alias; loading a package by
    # name always yields a Module. Assert it so callers get the precise type.
    if not isinstance(pkg, griffe.Module):
        raise TypeError(f"Expected a module for {PACKAGE!r}, got {type(pkg).__name__}")
    return pkg


def resolve(dotted_path: str) -> griffe.Object:
    """
    Resolve a public dotted path (e.g. ``"django_components.AlreadyRegistered"``)
    to its griffe object, following top-level re-export aliases to the object
    that actually defines the symbol.

    Raises:
        KeyError: if the path is not found in the loaded package.

    """
    pkg = load_package()

    relative = dotted_path.removeprefix(PACKAGE + ".")
    obj: griffe.Object | griffe.Alias = pkg if relative in ("", PACKAGE) else pkg[relative]

    # Top-level exports are aliases; the bases / source / members live on the
    # defining object, so follow the alias chain to its end.
    if isinstance(obj, griffe.Alias):
        return obj.final_target
    return obj
