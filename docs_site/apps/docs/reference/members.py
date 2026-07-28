"""
Render a class's members for ``ReferenceClass`` (group_by_category).

Members are bucketed into Attributes / Methods / Classes and rendered each as a
small sub-entry: an ``<h4>`` heading (with the new ``Class.member`` anchor and
the legacy ``django_components.Class.member`` alias), a symbol badge, a signature
(for callables) or a typed line (for attributes), and the member's docstring.

Member headings are ``<h4>`` and carry no ``doc-heading`` class, so the TOC merge
(which only lifts ``doc-heading`` h2/h3) leaves them out of the right rail - they
stay reachable by anchor without flooding the flat TOC with every method.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from apps.docs.reference.annotation import render_annotation
from apps.docs.reference.badges import symbol_badge
from apps.docs.reference.docstring import render_docstring_html
from apps.docs.reference.signatures import render_signature

if TYPE_CHECKING:
    from collections.abc import Callable

    import griffe


def _resolve_member(member: object) -> griffe.Object | None:
    """
    Follow an alias to its target, skipping members that can't be resolved.

    Re-exported stdlib symbols raise ``AliasResolutionError`` mid-walk (spike 5
    section 2); those aren't part of our API surface, so we drop them.
    """
    if not getattr(member, "is_alias", False):
        return member  # type: ignore[return-value]
    try:
        return member.final_target  # type: ignore[attr-defined,no-any-return]
    except Exception:
        return None


def iter_public_members(obj: griffe.Object) -> list[tuple[str, griffe.Object]]:
    """
    Public ``(name, resolved-target)`` members, in declaration order.

    The single source of truth for which members a class exposes - used both to
    render the member sections and to build the cross-ref index (so a member's
    ``[X][Class.member]`` link and its rendered ``Class.member`` anchor can never
    disagree).
    """
    out: list[tuple[str, griffe.Object]] = []
    for name, member in obj.members.items():
        if name.startswith("_"):
            continue
        target = _resolve_member(member)
        if target is None:
            continue
        out.append((name, target))
    return out


def public_member_names(obj: griffe.Object) -> list[str]:
    """The names from :func:`iter_public_members` (what the index keys off)."""
    return [name for name, _ in iter_public_members(obj)]


def render_members(
    obj: griffe.Object,
    *,
    parent_name: str,
    parent_path: str,
    current_url: str,
    resolve: Callable[[str, str], str | None],
) -> str:
    """Render ``obj``'s public members, grouped by category."""
    attributes: list[tuple[str, griffe.Object]] = []
    methods: list[tuple[str, griffe.Object]] = []
    classes: list[tuple[str, griffe.Object]] = []

    for name, target in iter_public_members(obj):
        kind = getattr(target.kind, "value", "")
        if kind == "function":
            methods.append((name, target))
        elif kind == "class":
            classes.append((name, target))
        else:  # attribute / property / class-attribute
            attributes.append((name, target))

    sections: list[str] = []
    for label, group in (("Attributes", attributes), ("Methods", methods), ("Classes", classes)):
        if not group:
            continue
        items = "".join(
            _render_member(
                name,
                member,
                parent_name=parent_name,
                parent_path=parent_path,
                current_url=current_url,
                resolve=resolve,
            )
            for name, member in group
        )
        sections.append(f'<h3 class="doc-group-label">{label}</h3>{items}')

    if not sections:
        return ""
    return f'<div class="doc-members">{"".join(sections)}</div>'


def _render_member(
    name: str,
    member: griffe.Object,
    *,
    parent_name: str,
    parent_path: str,
    current_url: str,
    resolve: Callable[[str, str], str | None],
) -> str:
    canonical = f"{parent_name}.{name}"  # e.g. Component.render
    legacy = f"{parent_path}.{name}"  # e.g. django_components.Component.render
    kind = getattr(member.kind, "value", "")
    labels: set[str] = getattr(member, "labels", set())
    annotation = getattr(member, "annotation", None)

    if kind == "function":
        css_kind = "method"
    elif kind == "class":
        css_kind = "class"
    else:
        css_kind = "attribute"

    if kind == "function":
        signature = render_signature(member, display_name=name, resolve=resolve)
    elif annotation is not None:
        type_html = render_annotation(annotation, resolve)
        signature = (
            f'<div class="doc-signature highlight"><pre><code>{html.escape(name)}: {type_html}</code></pre></div>'
        )
    else:
        signature = ""

    # base_level=4: a member heading is an <h4>, so its docstring headings nest below.
    body, _unresolved = render_docstring_html(member, current_url=current_url, resolve=resolve, base_level=4)

    label_note = ""
    if "classmethod" in labels:
        label_note = '<span class="doc-label">classmethod</span>'
    elif "property" in labels:
        label_note = '<span class="doc-label">property</span>'

    return (
        '<div class="doc doc-member">'
        f'<h4 id="{html.escape(canonical)}" class="doc-member-heading">'
        f'<span id="{html.escape(legacy)}"></span>'
        f'{symbol_badge(css_kind)}<span class="doc-object-name">{html.escape(name)}</span>{label_note}'
        f'<a class="headerlink" href="#{html.escape(canonical)}" title="Permanent link">¤</a>'
        "</h4>"
        f'<div class="doc-contents">{signature}{body}</div>'
        "</div>"
    )
