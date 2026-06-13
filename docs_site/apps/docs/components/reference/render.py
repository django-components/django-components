"""
Entry dispatch: ``ReferenceEntry`` -> rendered HTML.

The ``{% docstring %}`` tag and the reference page builder hand an entry here;
this module dispatches on ``entry.kind`` to the matching Layer-2 component. An
unknown kind is an error, not a silent skip - a page that references a symbol we
can't render should fail the build loudly. Renderers are registered as their
components land (Chunk A ships only ``"class"`` -> ``ReferenceClass``).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.docs.discovery.kinds import ReferenceEntry


def render_entry(entry: ReferenceEntry, *, current_url: str) -> str:
    """Render one reference entry to an HTML fragment."""
    renderer = _RENDERERS.get(entry.kind)
    if renderer is None:
        raise ValueError(
            f"No reference renderer for kind {entry.kind!r} (symbol {entry.dotted_path}). "
            f"Known kinds: {sorted(_RENDERERS)}."
        )
    return renderer(entry, current_url=current_url)


def _render_class(entry: ReferenceEntry, *, current_url: str) -> str:
    # Imported lazily so importing this module doesn't pull in griffe / the
    # component at Django startup (autodiscovery imports every module here).
    from apps.docs.components.reference.entries.reference_class.reference_class import ReferenceClass  # noqa: PLC0415

    return ReferenceClass.render(kwargs={"entry": entry, "current_url": current_url})


# kind -> renderer. Grows as later chunks add entry components.
_RENDERERS: dict[str, Callable[..., str]] = {
    "class": _render_class,
}
