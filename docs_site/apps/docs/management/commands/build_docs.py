"""
Build all docs pages to a versioned output directory.

Walks every .md file in the content directory, renders each through the
3-pass pipeline, and writes the result to output/<slug>/index.html.
Also emits .md companion files (raw expanded markdown for LLM consumption)
unless --no-companions is passed.

Usage:
    cd docs_site
    python manage.py build_docs                     # content/ -> ./site/ (gitignored)
    python manage.py build_docs -o /tmp/preview     # build to a custom directory
    python manage.py build_docs --docs-version 0.150.0 -o ../docs/v/0.150.0
"""

from __future__ import annotations

import shutil
import time
from importlib.metadata import version as get_version
from pathlib import Path

import pygments_djc  # noqa: F401 -- register the djc_py Pygments lexer
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.paths import md_companion_path, md_to_html_path, md_to_url
from apps.docs.build.pipeline import render_page


class Command(BaseCommand):
    help = "Build all docs pages through the pipeline."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--content", type=str, default=None, help="Content directory (default: settings.CONTENT_DIR)"
        )
        parser.add_argument(
            "--docs-version", type=str, default=None, help="Version string (default: from pyproject.toml)"
        )
        parser.add_argument("-o", "--output", type=str, default=None, help="Output directory (default: ./site/)")
        parser.add_argument("--no-companions", action="store_true", help="Skip .md companion file generation")

    def handle(self, *args: object, **options: object) -> None:
        content_dir = Path(str(options["content"])) if options["content"] else settings.CONTENT_DIR
        if not content_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"Content directory not found: {content_dir}"))
            return

        ver = str(options["docs_version"]) if options["docs_version"] else get_version("django_components")

        # Default output is the gitignored ./site/ dir (mirrors mkdocs' site_dir).
        # The release workflow passes --output ../docs/v/<version>/ for the committed deploy.
        if options["output"]:
            output_dir = Path(str(options["output"]))
        else:
            output_dir = settings.SITE_DIR

        # Base URL for canonical links and .md companion headers
        site_url = f"{settings.SITE_URL}/v/{ver}"
        emit_companions = not options["no_companions"]

        md_files = sorted(content_dir.rglob("*.md"))
        if not md_files:
            self.stderr.write(self.style.WARNING(f"No .md files found in {content_dir}"))
            return

        # Clear the output dir so stale files don't accumulate (mkdocs does the same).
        # Guard against clearing something important if a bad --output is passed.
        resolved_out = output_dir.resolve()
        unsafe = {settings.REPO_ROOT.resolve(), content_dir.resolve(), Path(resolved_out.anchor)}
        if resolved_out in unsafe:
            self.stderr.write(self.style.ERROR(f"Refusing to clear output dir: {resolved_out}"))
            return
        if output_dir.exists():
            shutil.rmtree(output_dir)

        self.stdout.write(f"Building {len(md_files)} pages from {content_dir} -> {output_dir}")
        t0 = time.monotonic()
        built = 0
        errors = 0

        for md_path in md_files:
            rel = md_path.relative_to(content_dir)
            out_path = md_to_html_path(output_dir, rel)
            page_url = md_to_url(rel)
            canonical = f"{site_url}/{page_url}" if site_url else ""

            # Build context available to Django template tags in Pass 1
            ctx: dict = {
                "version": ver,
                "canonical": canonical,
                "site_url": site_url,
            }

            try:
                source = md_path.read_text(encoding="utf-8")
                result = render_page(
                    source,
                    context=ctx,
                    source_path=md_path,
                    content_dir=content_dir,
                )

                # Ensure canonical is set even if front-matter didn't provide one
                if not result.meta.canonical and canonical:
                    result.meta.canonical = canonical

                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(result.html, encoding="utf-8")

                # .md companion: raw expanded markdown for LLM/AI agent consumption
                # (see design doc spike 11.12 section 3.B.2)
                if emit_companions:
                    companion_path = md_companion_path(output_dir, rel)
                    _write_companion(companion_path, result.meta, result.expanded_markdown, canonical)

                built += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  FAIL {rel}: {e}"))
                errors += 1

        elapsed = time.monotonic() - t0
        suffix = " (with .md companions)" if emit_companions else ""
        self.stdout.write(self.style.SUCCESS(f"Built {built} pages{suffix} in {elapsed:.1f}s ({errors} errors)"))


def _write_companion(path: Path, meta, expanded_markdown: str, canonical: str) -> None:
    """
    Write a .md companion file with minimal front-matter + expanded markdown.

    The companion contains the post-Django-expansion markdown (all template tags
    resolved) but not the HTML conversion. LLMs prefer this over reverse-engineering
    markdown from rendered HTML.
    """
    header_lines = ["---"]
    if meta.title:
        header_lines.append(f"title: {meta.title}")
    if canonical:
        header_lines.append(f"url: {canonical}")
    if meta.description:
        desc = meta.description.replace('"', '\\"')
        header_lines.append(f'description: "{desc}"')
    header_lines.append("---")
    header_lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(header_lines) + expanded_markdown, encoding="utf-8")
