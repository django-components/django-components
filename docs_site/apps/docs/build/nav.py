"""
Navigation YAML loader and validator.

Loads a single _nav.yml file and produces a typed navigation tree that the
sidebar, breadcrumbs, and prev/next components consume. Replaces the
mkdocs-awesome-nav plugin.

Spec: docs_site/design/DESIGN_spike_11.md section 3.2,
      docs_site/design/DESIGN_spike_9.md section 2.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class NavItem:
    title: str
    path: str
    active: bool = False


@dataclass
class NavGroup:
    label: str
    items: list[NavItem] = field(default_factory=list)
    expanded: bool = False


@dataclass
class NavSection:
    label: str
    path: str = ""
    items: list[NavItem] = field(default_factory=list)
    groups: list[NavGroup] = field(default_factory=list)


@dataclass
class NavTree:
    sections: list[NavSection] = field(default_factory=list)

    def flat_pages(self) -> list[NavItem]:
        """Return all nav items in document order (for prev/next navigation)."""
        pages: list[NavItem] = []
        for section in self.sections:
            if section.path:
                pages.append(NavItem(title=section.label, path=section.path))
            if section.items:
                pages.extend(section.items)
            for group in section.groups:
                pages.extend(group.items)
        return pages

    def find_breadcrumbs(self, current_path: str) -> list[tuple[str, str]]:
        """
        Return breadcrumb trail for the given path as (label, path) pairs.

        The last entry is the current page (path="" to indicate non-link).
        """
        normalized = current_path.strip("/")
        if not normalized:
            normalized = ""

        for section in self.sections:
            if section.path and section.path.strip("/") == normalized:
                return [(section.label, "")]

            for item in section.items:
                if item.path.strip("/") == normalized:
                    return [(section.label, section.path or ""), (item.title, "")]

            for group in section.groups:
                for item in group.items:
                    if item.path.strip("/") == normalized:
                        return [
                            (section.label, section.path or ""),
                            (group.label, ""),
                            (item.title, ""),
                        ]
        return []

    def find_title(self, current_path: str) -> str:
        """
        Return the nav title for a path, or "" if the page isn't in the nav.

        Used as the page-title fallback for pages without front-matter or an
        H1 - the old mkdocs site got those titles from awesome-nav the same way.
        """
        normalized = current_path.strip("/")
        for section in self.sections:
            if section.path and section.path.strip("/") == normalized:
                return section.label
            for item in section.items:
                if item.path.strip("/") == normalized:
                    return item.title
            for group in section.groups:
                for item in group.items:
                    if item.path.strip("/") == normalized:
                        return item.title
        return ""

    def find_prev_next(self, current_path: str) -> tuple[NavItem | None, NavItem | None]:
        """Return (prev, next) NavItems relative to the current path."""
        pages = self.flat_pages()
        normalized = current_path.strip("/")

        for i, page in enumerate(pages):
            if page.path.strip("/") == normalized:
                prev_item = pages[i - 1] if i > 0 else None
                next_item = pages[i + 1] if i < len(pages) - 1 else None
                return prev_item, next_item
        return None, None

    def set_active(self, current_path: str) -> None:
        """Mark the active item and expand its containing group."""
        normalized = current_path.strip("/")

        for section in self.sections:
            for item in section.items:
                item.active = item.path.strip("/") == normalized

            for group in section.groups:
                group_has_active = False
                for item in group.items:
                    item.active = item.path.strip("/") == normalized
                    if item.active:
                        group_has_active = True
                group.expanded = group_has_active


def load_nav(nav_path: Path) -> NavTree:
    """Load and validate a _nav.yml file into a NavTree."""
    if not nav_path.is_file():
        return NavTree()

    with nav_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "sections" not in raw:
        return NavTree()

    sections: list[NavSection] = []
    for raw_section in raw["sections"]:
        section = _parse_section(raw_section)
        sections.append(section)

    return NavTree(sections=sections)


def _parse_section(raw: dict) -> NavSection:
    label = raw.get("label", "")
    path = raw.get("path", "")

    items: list[NavItem] = []
    groups: list[NavGroup] = []

    if "items" in raw and "groups" in raw:
        raise ValueError(f"Nav section '{label}' has both 'items' and 'groups'; pick one")

    if "items" in raw:
        for raw_item in raw["items"]:
            items.append(NavItem(title=raw_item["title"], path=raw_item["path"]))

    if "groups" in raw:
        for raw_group in raw["groups"]:
            group_items = [NavItem(title=ri["title"], path=ri["path"]) for ri in raw_group.get("items", [])]
            groups.append(NavGroup(label=raw_group["label"], items=group_items))

    return NavSection(label=label, path=path, items=items, groups=groups)
