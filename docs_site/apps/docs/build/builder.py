"""
Reusable site builder.

Renders every markdown page in a content directory through the 3-pass pipeline
and pre-renders examples, writing the result to an output directory. Shared by
the `build_docs` command (writes to ./site/) and `docs_build_check` (writes to
a throwaway temp dir, then runs the guardrails over it).

A page that fails to render is captured as a `template_render` guard ERROR
(feature 3b.8) instead of aborting the whole build, so the guard report can
list every broken page at once.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from importlib.metadata import version as get_version
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

from apps.docs.build.examples import pre_render_examples
from apps.docs.build.guards import GuardResult
from apps.docs.build.nav import load_nav
from apps.docs.build.paths import md_companion_path, md_to_html_path, md_to_url
from apps.docs.build.pipeline import render_page
from apps.docs.examples import get_example_registry

if TYPE_CHECKING:
    from apps.docs.examples import ExampleInfo


@dataclass
class BuildOutcome:
    output_dir: Path
    built: int = 0
    failed: int = 0
    elapsed: float = 0.0
    example_files: int = 0
    # template_render guard results for pages that raised during rendering.
    render_errors: list[GuardResult] = field(default_factory=list)
    example_registry: dict[str, ExampleInfo] = field(default_factory=dict)


def _is_unsafe_output(output_dir: Path, content_dir: Path) -> bool:
    resolved = output_dir.resolve()
    unsafe = {settings.REPO_ROOT.resolve(), content_dir.resolve(), Path(resolved.anchor)}
    return resolved in unsafe


def build_site(
    *,
    content_dir: Path,
    output_dir: Path,
    version: str | None = None,
    emit_companions: bool = True,
) -> BuildOutcome:
    """
    Build every page in `content_dir` into `output_dir`.

    Raises ValueError if `output_dir` looks unsafe to clear (repo root, the
    content dir itself, or a filesystem root).
    """
    ver = version or get_version("django_components")
    site_url = f"{settings.SITE_URL}/v/{ver}"

    if _is_unsafe_output(output_dir, content_dir):
        raise ValueError(f"Refusing to clear unsafe output dir: {output_dir.resolve()}")

    example_registry = get_example_registry()
    nav_tree = load_nav(content_dir / "_nav.yml")
    md_files = sorted(p for p in content_dir.rglob("*.md") if p.name != "_nav.yml")

    if output_dir.exists():
        shutil.rmtree(output_dir)

    outcome = BuildOutcome(output_dir=output_dir, example_registry=example_registry)
    t0 = time.monotonic()

    for md_path in md_files:
        rel = md_path.relative_to(content_dir)
        out_path = md_to_html_path(output_dir, rel)
        page_url = md_to_url(rel)
        canonical = f"{site_url}/{page_url}" if site_url else ""
        ctx = {"version": ver, "canonical": canonical, "site_url": site_url}

        try:
            source = md_path.read_text(encoding="utf-8")
            result = render_page(
                source,
                context=ctx,
                source_path=md_path,
                content_dir=content_dir,
                nav_tree=nav_tree,
                current_path=page_url,
            )
            if not result.meta.canonical and canonical:
                result.meta.canonical = canonical

            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(result.html, encoding="utf-8")

            if emit_companions:
                companion = md_companion_path(output_dir, rel)
                _write_companion(companion, result.meta, result.expanded_markdown, canonical)

            outcome.built += 1
        except Exception as e:
            outcome.failed += 1
            outcome.render_errors.append(
                GuardResult.error(
                    guard="template_render",
                    message=f"Page failed to render: {type(e).__name__}: {e}",
                    source=str(rel),
                )
            )

    if example_registry:
        ex_rendered, ex_errors = pre_render_examples(output_dir, example_registry)
        outcome.example_files = ex_rendered
        outcome.failed += ex_errors

    outcome.elapsed = time.monotonic() - t0
    return outcome


def _write_companion(path: Path, meta: object, expanded_markdown: str, canonical: str) -> None:
    """Write a `.md` companion file (front-matter + expanded markdown) for LLMs."""
    header_lines = ["---"]
    title = getattr(meta, "title", "")
    description = getattr(meta, "description", "")
    if title:
        header_lines.append(f"title: {title}")
    if canonical:
        header_lines.append(f"url: {canonical}")
    if description:
        desc = description.replace('"', '\\"')
        header_lines.append(f'description: "{desc}"')
    header_lines.append("---")
    header_lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(header_lines) + expanded_markdown, encoding="utf-8")
