"""
Entry dispatch: ``ReferenceEntry`` -> rendered HTML.

The ``{% docstring %}`` tag and the reference page builder hand an entry here;
this module dispatches on ``entry.kind`` to the matching Layer-2 component. An
unknown kind is an error, not a silent skip - a page that references a symbol we
can't render should fail the build loudly. Renderers are registered as their
components land (Chunk A ships only ``"class"`` -> ``ReferenceClass``).
"""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferenceEntry


def render_entry(entry: ReferenceEntry, *, current_url: str) -> str:
    """
    Render one reference entry to an HTML fragment.

    An unknown *kind* is a programming error and raises. A *rendering* failure
    (e.g. a public symbol griffe can't introspect, like a ``typing.Literal``
    alias that raises ``AliasResolutionError``) degrades to a minimal entry so
    one bad symbol doesn't sink the whole page - the heading + anchors still
    render, keeping inbound links alive.
    """
    renderer = _RENDERERS.get(entry.kind)
    if renderer is None:
        raise ValueError(
            f"No reference renderer for kind {entry.kind!r} (symbol {entry.dotted_path}). "
            f"Known kinds: {sorted(_RENDERERS)}."
        )
    try:
        return renderer(entry, current_url=current_url)
    except Exception as exc:
        print(f"reference: could not render {entry.dotted_path}: {type(exc).__name__}: {exc}")
        return _render_fallback(entry)


def _render_fallback(entry: ReferenceEntry) -> str:
    name = html.escape(entry.display_name)
    return (
        '<div class="doc doc-object">'
        f'<h2 id="{html.escape(entry.canonical_anchor)}" class="doc doc-heading">'
        f'<span id="{html.escape(entry.legacy_anchor)}" class="doc doc-legacy-anchor"></span>'
        f'<span class="doc doc-object-name">{name}</span>'
        f'<a class="headerlink" href="#{html.escape(entry.canonical_anchor)}" title="Permanent link">¤</a></h2>'
        f'<div class="doc doc-contents"><p class="doc-unresolved">'
        f"Reference for <code>{name}</code> could not be generated automatically.</p></div></div>"
    )


def _render_class(entry: ReferenceEntry, *, current_url: str) -> str:
    # Lazy import: defer pulling each (griffe-backed) component shell until a
    # render of that kind is requested, so a page with no classes never imports
    # ReferenceClass or its griffe machinery.
    from apps.docs.components.reference.reference_class import ReferenceClass  # noqa: PLC0415

    return ReferenceClass.render(kwargs={"entry": entry, "current_url": current_url})


def _render_management_command(entry: ReferenceEntry, *, current_url: str) -> str:
    from apps.docs.components.reference.reference_management_command import (  # noqa: PLC0415
        ReferenceManagementCommand,
    )

    return ReferenceManagementCommand.render(kwargs={"entry": entry, "current_url": current_url})


def _render_extension_hook(entry: ReferenceEntry, *, current_url: str) -> str:
    from apps.docs.components.reference.reference_extension_hook import (  # noqa: PLC0415
        ReferenceExtensionHook,
    )

    return ReferenceExtensionHook.render(kwargs={"entry": entry, "current_url": current_url})


def _render_hook_context(entry: ReferenceEntry, *, current_url: str) -> str:
    from apps.docs.components.reference.reference_hook_context import (  # noqa: PLC0415
        ReferenceHookContext,
    )

    return ReferenceHookContext.render(kwargs={"entry": entry, "current_url": current_url})


def _render_template_tag(entry: ReferenceEntry, *, current_url: str) -> str:
    from apps.docs.components.reference.reference_template_tag import (  # noqa: PLC0415
        ReferenceTemplateTag,
    )

    return ReferenceTemplateTag.render(kwargs={"entry": entry, "current_url": current_url})


def _render_setting(entry: ReferenceEntry, *, current_url: str) -> str:
    from apps.docs.components.reference.reference_setting import (  # noqa: PLC0415
        ReferenceSetting,
    )

    return ReferenceSetting.render(kwargs={"entry": entry, "current_url": current_url})


def _render_tag_formatter(entry: ReferenceEntry, *, current_url: str) -> str:
    from apps.docs.components.reference.reference_tag_formatter import (  # noqa: PLC0415
        ReferenceTagFormatter,
    )

    return ReferenceTagFormatter.render(kwargs={"entry": entry, "current_url": current_url})


def _render_component_class(entry: ReferenceEntry, *, current_url: str) -> str:
    from apps.docs.components.reference.reference_component_class import (  # noqa: PLC0415
        ReferenceComponentClass,
    )

    return ReferenceComponentClass.render(kwargs={"entry": entry, "current_url": current_url})


# kind -> renderer. Grows as later chunks add entry components.
_RENDERERS: dict[str, Callable[..., str]] = {
    "class": _render_class,
    "component_class": _render_component_class,
    "management_command": _render_management_command,
    "extension_hook": _render_extension_hook,
    "hook_context": _render_hook_context,
    "template_tag": _render_template_tag,
    "setting": _render_setting,
    "tag_formatter": _render_tag_formatter,
}
