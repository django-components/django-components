"""
Build a single markdown page through the 3-pass pipeline.

Usage:
    cd docs_site
    python manage.py build_one ../docs/getting_started/your_first_component.md -o site/test.html
    python manage.py build_one content/test/pipeline_test.md -o /tmp/test.html
"""

from __future__ import annotations

from importlib.metadata import version as get_version
from pathlib import Path

import pygments_djc  # noqa: F401 -- register the djc_py Pygments lexer
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.pipeline import render_page


class Command(BaseCommand):
    help = "Render a single markdown page through the docs pipeline."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("source", type=str, help="Path to the markdown file (relative to repo root)")
        parser.add_argument("-o", "--output", type=str, default=None, help="Output HTML file path")
        parser.add_argument("--no-layout", action="store_true", help="Skip Pass 3 (DocPage layout wrap)")

    def handle(self, *args: object, **options: object) -> None:
        source_path = Path(str(options["source"]))
        if not source_path.exists():
            self.stderr.write(self.style.ERROR(f"Source file not found: {source_path}"))
            return

        source = source_path.read_text(encoding="utf-8")
        ctx = {"version": get_version("django_components")}

        result = render_page(
            source,
            context=ctx,
            source_path=source_path,
            content_dir=settings.CONTENT_DIR,
            wrap_in_layout=not options["no_layout"],
        )

        output_path = Path(str(options["output"])) if options["output"] else None
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.html, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote {output_path} ({len(result.html)} bytes)"))
        else:
            self.stdout.write(result.html)

        self.stdout.write(f"Title: {result.meta.title}")
        self.stdout.write(f"Description: {result.meta.description[:80]}{'...' if len(result.meta.description) > 80 else ''}")
        self.stdout.write(f"TOC entries: {len(result.toc_tokens)}")
