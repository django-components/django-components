"""
docs-assemble: produce the full multi-version deploy artifact in ``site/`` (6.4).

The everyday ``build_docs`` writes only the current version. At deploy we also
need every committed historical snapshot mounted alongside it. This command
assembles the complete tree GitHub Pages serves:

    site/
        index.html, docs/, static/, sitemap.xml, robots.txt, ...   <- current version
        v/
            versions.json                                          <- the manifest
            <version>/ ...                                         <- each committed version
            latest/ ...                                            <- the `latest` alias redirects

It (1) runs ``build_docs`` for the current version into the site root (so it
serves at ``/`` and ``/docs/``, with ``/static``, the Pagefind index, the SEO
files, and the benchmark passthrough), then (2) copies ``docs_site/versions/*``
into ``site/v/``. The current-version build's robots.txt disallows the older
``/v/<version>/`` dirs (see ``seo.write_robots``), so the frozen gh-pages
imports stay out of search while their pinned URLs keep resolving.

CI runs this and publishes ``site/`` to GitHub Pages - this is the cutover
deploy that replaces the old mkdocs build. ``site/`` is gitignored; nothing
here is committed.

Usage:
    cd docs_site
    python manage.py docs_assemble                  # build current + assemble versions -> site/
    python manage.py docs_assemble --no-build       # assemble versions into an existing ./site/
    python manage.py docs_assemble -o /path/to/out  # assemble into a custom dir
"""

from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Assemble the full multi-version deploy artifact (current version + docs_site/versions/*) into site/."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "-o",
            "--output",
            type=str,
            default=None,
            help="Output dir for the assembled site (default: settings.SITE_DIR).",
        )
        parser.add_argument(
            "--no-build",
            action="store_true",
            help="Skip the current-version build; only copy versions/* into an existing site/.",
        )

    def handle(self, *args: object, **options: object) -> None:
        site_dir = Path(str(options["output"])) if options["output"] else settings.SITE_DIR
        versions_root: Path = settings.VERSIONS_DIR

        if not options["no_build"]:
            # Preview mode (no --docs-version): writes the current version to the
            # site root with /static, Pagefind, SEO files, and passthroughs.
            call_command("build_docs", output=str(site_dir))

        if not site_dir.is_dir():
            raise CommandError(f"No build at {site_dir}. Run without --no-build first.")

        # Mount every committed snapshot (version dirs + the latest alias +
        # versions.json) under /v/. Frozen imports carry their own assets; new
        # snapshots reference the shared /static at the root.
        if versions_root.is_dir():
            dest_v = site_dir / "v"
            shutil.copytree(versions_root, dest_v, dirs_exist_ok=True)
            n_versions = sum(1 for d in dest_v.iterdir() if d.is_dir() and (d / "_build_info.json").is_file())
            self.stdout.write(self.style.SUCCESS(f"Mounted {n_versions} version(s) under {dest_v}"))
        else:
            self.stdout.write(f"No versions tree at {versions_root}; assembled current version only.")

        self.stdout.write(self.style.SUCCESS(f"Assembled deploy artifact at {site_dir}"))
