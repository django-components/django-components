"""
Tests for the Phase 5c Chunk 3 AI index files (feature 5c.10).

Covers the llms.txt nav index and the llms-full.txt content concatenation in
apps/docs/build/llms.py, driven by a synthetic NavTree + `.md` companions.
"""

from __future__ import annotations

from pathlib import Path

from apps.docs.build.llms import write_llms_full_txt, write_llms_txt
from apps.docs.build.nav import NavGroup, NavItem, NavSection, NavTree
from apps.docs.build.pipeline import expand_snippets

SITE = "https://ex.com/base"


def _companion(output_dir: Path, url: str, *, title: str, description: str = "", body: str = "Body.") -> None:
    path = output_dir / url.strip("/") / "index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = ["---", f"title: {title}"]
    if description:
        fm.append(f"description: {description}")
    fm += ["---", "", body, ""]
    path.write_text("\n".join(fm), encoding="utf-8")


def _nav() -> NavTree:
    return NavTree(
        sections=[
            NavSection(label="Home", path="/"),
            NavSection(
                label="Getting Started",
                items=[NavItem(title="Installation", path="/docs/getting_started/installation/")],
            ),
            NavSection(
                label="Concepts",
                groups=[NavGroup(label="Fundamentals", items=[NavItem(title="Slots", path="/docs/concepts/slots/")])],
            ),
            NavSection(
                label="API Reference",
                path="/docs/reference/",
                items=[NavItem(title="Component", path="/docs/reference/api/")],
            ),
            NavSection(label="Release notes", path="/docs/releases/"),
        ]
    )


def _build(output_dir: Path) -> NavTree:
    _companion(output_dir, "/", title="Django Components", description="Reusable components.", body="Home body.")
    _companion(
        output_dir,
        "/docs/getting_started/installation/",
        title="Installation",
        description="Install it.",
        body="Run pip install.",
    )
    _companion(output_dir, "/docs/concepts/slots/", title="Slots", description="Named slots.")
    _companion(output_dir, "/docs/reference/", title="API Reference", description="The API.")
    _companion(output_dir, "/docs/reference/api/", title="Component", description="The base class.")
    _companion(output_dir, "/docs/releases/", title="Release notes", description="Changelog.")
    return _nav()


# -- llms.txt ------------------------------------------------------------------


def test_llms_txt_structure(tmp_path: Path) -> None:
    nav = _build(tmp_path)
    count = write_llms_txt(tmp_path, nav, site_url=SITE)
    txt = (tmp_path / "llms.txt").read_text()

    # Title + blockquote come from the home companion; Home is not a body section.
    assert txt.startswith("# Django Components\n\n> Reusable components.\n")
    assert "## Home" not in txt
    # Sections become H2 with bulleted links + descriptions.
    assert "## Getting Started" in txt
    assert f"- [Installation]({SITE}/docs/getting_started/installation/): Install it." in txt
    # Group items are flattened under their section.
    assert "## Concepts" in txt
    assert f"- [Slots]({SITE}/docs/concepts/slots/): Named slots." in txt
    # A section with a landing page emits an "overview" bullet first.
    assert f"- [API Reference overview]({SITE}/docs/reference/): The API." in txt
    assert f"- [Component]({SITE}/docs/reference/api/): The base class." in txt
    # Standalone sections (just a landing page) go under Optional.
    assert "## Optional" in txt
    assert f"- [Release notes]({SITE}/docs/releases/): Changelog." in txt
    assert count == 5  # installation, slots, api overview, component, releases


def test_llms_txt_omits_description_when_companion_missing(tmp_path: Path) -> None:
    nav = NavTree(sections=[NavSection(label="X", items=[NavItem(title="Gone", path="/docs/gone/")])])
    write_llms_txt(tmp_path, nav, site_url=SITE)
    txt = (tmp_path / "llms.txt").read_text()
    assert f"- [Gone]({SITE}/docs/gone/)" in txt
    assert "/docs/gone/):" not in txt  # no trailing ": description"


# -- llms-full.txt -------------------------------------------------------------


def test_llms_full_concatenates_bodies(tmp_path: Path) -> None:
    nav = _build(tmp_path)
    pages = write_llms_full_txt(tmp_path, nav, site_url=SITE)
    full = (tmp_path / "llms-full.txt").read_text()

    assert pages == 6  # home + installation + slots + api landing + component + releases
    # Each page block carries a heading + source URL + the front-matter-stripped body.
    assert (
        "# Installation\n\nSource: https://ex.com/base/docs/getting_started/installation/\n\nRun pip install." in full
    )
    assert "Home body." in full
    assert "---" in full  # page separator
    # Front-matter must not leak into the concatenation.
    assert "title: Installation" not in full


def test_llms_full_skips_pages_without_companion(tmp_path: Path) -> None:
    nav = NavTree(sections=[NavSection(label="X", items=[NavItem(title="Gone", path="/docs/gone/")])])
    assert write_llms_full_txt(tmp_path, nav, site_url=SITE) == 0
    assert not (tmp_path / "llms-full.txt").exists()


# -- snippet expansion (the companion / llms-full source) ----------------------


def test_expand_snippets_inlines_repo_file() -> None:
    # The companion .md and llms-full.txt must contain the included content, not
    # the raw `--8<--` directive (LICENSE exists at the repo root).
    out = expand_snippets('--8<-- "LICENSE"')
    assert "MIT License" in out
    assert "--8<--" not in out


def test_expand_snippets_fast_path_without_directive() -> None:
    assert expand_snippets("plain markdown, no includes") == "plain markdown, no includes"
