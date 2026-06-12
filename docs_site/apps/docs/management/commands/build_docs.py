"""
Build all docs pages to a versioned output directory.

Walks every .md file in the content directory, renders each through the
3-pass pipeline, and writes the result to output/<slug>/index.html.
Also emits .md companion files (raw expanded markdown for LLM consumption)
unless --no-companions is passed.

The actual rendering lives in apps/docs/build/builder.py so it can be shared
with the docs_build_check CI gate.

Usage:
    cd docs_site
    python manage.py build_docs                     # content/ -> ./site/ (gitignored)
    python manage.py build_docs -o /tmp/preview     # build to a custom directory
    python manage.py build_docs --docs-version 0.150.0 -o ../docs/v/0.150.0
"""

from __future__ import annotations

from pathlib import Path

import pygments_djc  # noqa: F401 -- register the djc_py Pygments lexer
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.builder import build_site


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

        output_dir = Path(str(options["output"])) if options["output"] else settings.SITE_DIR
        version = str(options["docs_version"]) if options["docs_version"] else None
        emit_companions = not options["no_companions"]

        self.stdout.write(f"Building pages from {content_dir} -> {output_dir}")
        try:
            outcome = build_site(
                content_dir=content_dir,
                output_dir=output_dir,
                version=version,
                emit_companions=emit_companions,
                changelog=settings.CHANGELOG_PATH,
            )
        except ValueError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        for result in outcome.render_errors:
            self.stderr.write(self.style.ERROR(f"  FAIL {result.source}: {result.message}"))
        if outcome.example_files:
            self.stdout.write(f"Pre-rendered {outcome.example_files} example files")

        suffix = " (with .md companions)" if emit_companions else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Built {outcome.built} pages{suffix} in {outcome.elapsed:.1f}s ({outcome.failed} errors)"
            )
        )
