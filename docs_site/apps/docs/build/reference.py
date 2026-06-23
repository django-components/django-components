"""
API reference page generator: discovered ``ReferencePage``s -> markdown pages.

Mirrors ``build/release_notes.py``. Pages are generated into a throwaway staging
dir at build time and rendered through the same 3-pass pipeline as regular
content - nothing is committed under ``content/``. Each generated page is a thin
markdown wrapper: front-matter plus one ``{% docstring "path" %}`` per discovered
entry (the analog of the old mkdocstrings ``::: path`` directives). All the actual
rendering happens in Pass 1 via the per-kind reference components.

Spec: ``docs_site/design/DESIGN_spike_5.md`` sections 5 and 10 (Phase 4).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from apps.docs.reference.discovery.registry import discover_pages

if TYPE_CHECKING:
    from apps.docs.reference.discovery.kinds import ReferencePage


def _page_markdown(page: ReferencePage) -> str:
    """The markdown source for one generated reference page."""
    lines = ["---", f"title: {page.title}"]
    if page.description:
        # Quote so punctuation in the description can't break the YAML.
        desc = page.description.replace('"', '\\"')
        lines.append(f'description: "{desc}"')
    lines += ["---", "", f"# {page.title}", ""]

    if page.preface_md.strip():
        # `[X][Key]` cross-refs in the preface are resolved by the render pipeline
        # (resolve_crossrefs_in_prose), the same as for any content page.
        lines += [page.preface_md.strip(), ""]

    # The hooks_plus_objects layout splits entries into "Hooks" / "Objects"
    # sections (h2 headings), which also nest the entries in the right-rail TOC.
    section_for = _HOOKS_PLUS_OBJECTS_SECTIONS if page.layout == "hooks_plus_objects" else {}
    current_section: str | None = None

    for entry in page.entries:
        section = section_for.get(entry.kind)
        if section is not None and section != current_section:
            lines += [f"## {section}", ""]
            current_section = section
        lines.append(f'{{% docstring "{entry.dotted_path}" %}}')
        lines.append("")

    return "\n".join(lines) + "\n"


# kind -> section heading, for the hooks_plus_objects page layout.
_HOOKS_PLUS_OBJECTS_SECTIONS = {"extension_hook": "Hooks", "hook_context": "Objects"}


def generate_reference_pages(target_dir: Path) -> list[Path]:
    """Write ``docs/reference/<slug>.md`` for every discovered page into target_dir."""
    ref_dir = target_dir / "docs" / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for page in discover_pages():
        page_path = ref_dir / f"{page.slug}.md"
        page_path.write_text(_page_markdown(page), encoding="utf-8")
        written.append(page_path)
    return written


def write_objects_inv(output_dir: Path, *, version: str) -> None:
    """
    Emit ``objects.inv`` for our documented symbols (feature 4.22).

    Lets other docs sites cross-link into ours with the same ``[X][path]``
    convention we use internally - the inverse of consuming stdlib/Django
    inventories.
    """
    from apps.docs.reference.inventory import build_objects_inv  # noqa: PLC0415

    entries = [
        (entry.dotted_path, f"docs/reference/{page.slug}/#{entry.canonical_anchor}")
        for page in discover_pages()
        for entry in page.entries
    ]
    data = build_objects_inv(entries, project="django-components", version=version)
    (output_dir / "objects.inv").write_bytes(data)


# Dev-server cache: a staging dir holding the generated reference pages. Unlike
# release notes (keyed on CHANGELOG mtime), these depend on the whole source
# tree, so there's no single mtime to key on - regenerate once per process and
# rely on runserver's reload to refresh on code changes.
_staging_cache: Path | None = None


def get_reference_staging_dir() -> Path:
    """Generate (and cache) the reference pages for the dev server's live preview."""
    global _staging_cache  # noqa: PLW0603 -- module-level cache for the dev server
    if _staging_cache is not None and _staging_cache.is_dir():
        return _staging_cache

    # resolve() because gettempdir() may be a symlink (e.g. /var -> /private/var
    # on macOS), while url_to_md compares fully-resolved paths.
    staging = (Path(tempfile.gettempdir()) / "djc-docs-reference").resolve()
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    generate_reference_pages(staging)
    _staging_cache = staging
    return staging
