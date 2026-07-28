"""
The griffe loader for the API reference.

Loads ``django_components`` once with griffe (with our two extensions applied)
and resolves public dotted paths to griffe objects.

Uses static analysis (not ``force_inspection``): static walks the filesystem, so
it discovers every submodule and can resolve the public re-export aliases
(``ComponentCache`` -> ``extensions.cache.ComponentCache``, etc.). Inspection mode
only discovers submodules a package exposes as attributes, which silently drops
the extension submodules and leaves those exports unresolvable.

The one thing static can't see is metaclass-set attributes (``BaseNode._signature``,
``ComponentNode.allowed_flags`` - spike 5 section 2). Those are only needed by the
template-tags page, which will load those specific symbols with inspection when it
lands; the API + exceptions pages don't need them.

Django must be configured before this runs (griffe imports the package), which it
always is inside the build command / dev server.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import griffe
from django.conf import settings

from apps.docs.griffe_extensions import build_extensions

PACKAGE = "django_components"


@lru_cache(maxsize=1)
def load_package() -> griffe.Module:
    """Load (and cache) the ``django_components`` griffe module with extensions applied."""
    # Quiet griffe's per-docstring "could not parse" warnings; malformed Google
    # sections in a docstring are a content issue, not a build failure, and they
    # would otherwise flood the build output once over the whole API surface.
    logging.getLogger("griffe").setLevel(logging.ERROR)
    # Search src/ explicitly so we document the in-repo source, matching the old
    # mkdocs `paths: [src]`. This also makes griffe's file paths point at the
    # working tree rather than some other installed copy.
    search_paths = [str(Path(settings.REPO_ROOT) / "src")]
    pkg = griffe.load(
        PACKAGE,
        extensions=build_extensions(),
        search_paths=search_paths,
        # Resolve re-export aliases at load time so resolve() can follow them.
        resolve_aliases=True,
        resolve_implicit=True,
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
