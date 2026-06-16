"""
Build all docs pages to an output directory (the everyday `docs-build`).

Walks every .md file in the content directory, renders each through the
3-pass pipeline, and writes the result to output/<slug>/index.html.
Also emits .md companion files (raw expanded markdown for LLM consumption)
unless --no-companions is passed.

Two modes:

- **Preview** (no --docs-version, no --alias): builds into ./site/ (gitignored)
  for local inspection. Touches nothing under version control.
- **Version** (--docs-version X and/or --alias): builds a committed snapshot
  into docs_site/versions/X/, writes a _build_info.json stamp, updates the
  versions.json manifest, and materializes any --alias as redirect stubs. This
  is what CI runs on a release tag (e.g. --docs-version 0.151.0 --alias latest).

The actual rendering lives in apps/docs/build/builder.py so it can be shared
with the docs_build_check CI gate; the versioning side-effects live in
apps/docs/build/versioning.py.

Usage:
    cd docs_site
    python manage.py build_docs                                 # content/ -> ./site/ (preview)
    python manage.py build_docs -o /tmp/preview                 # preview to a custom dir
    python manage.py build_docs --docs-version 0.151.0 --alias latest   # commit a release snapshot
"""

from __future__ import annotations

from importlib.metadata import version as get_version
from pathlib import Path

import pygments_djc  # noqa: F401 -- register the djc_py Pygments lexer
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.builder import build_site
from apps.docs.build.pagefind import run_pagefind
from apps.docs.build.versioning import git_head_sha, materialize_alias, update_manifest, write_build_info


class Command(BaseCommand):
    help = "Build all docs pages through the pipeline."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--content", type=str, default=None, help="Content directory (default: settings.CONTENT_DIR)"
        )
        parser.add_argument(
            "--docs-version", type=str, default=None, help="Version string (default: from pyproject.toml)"
        )
        parser.add_argument(
            "--title", type=str, default=None, help="Manifest display title for this version (default: the version)"
        )
        parser.add_argument("-o", "--output", type=str, default=None, help="Output directory (default: ./site/)")
        parser.add_argument("--no-companions", action="store_true", help="Skip .md companion file generation")
        parser.add_argument("--no-search", action="store_true", help="Skip the Pagefind search-index build")
        parser.add_argument(
            "--alias",
            action="append",
            default=None,
            metavar="NAME",
            help="Alias (e.g. latest) pointed at this version; repeatable. Materialized as redirect stubs.",
        )
        parser.add_argument(
            "--no-manifest-update",
            dest="update_manifest",
            action="store_false",
            help="Don't rewrite versions.json (docs-build-all updates it once at the end).",
        )
        parser.set_defaults(update_manifest=True)

    def handle(self, *args: object, **options: object) -> None:
        content_dir = Path(str(options["content"])) if options["content"] else settings.CONTENT_DIR
        if not content_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"Content directory not found: {content_dir}"))
            return

        explicit_output = Path(str(options["output"])) if options["output"] else None
        requested_version = str(options["docs_version"]) if options["docs_version"] else None
        title = str(options["title"]) if options["title"] else None
        aliases = tuple(options["alias"] or ())
        emit_companions = not options["no_companions"]
        do_manifest_update = bool(options["update_manifest"])

        # Version mode: write a committed snapshot into the versions/ tree
        # (triggered by --docs-version or --alias, i.e. a release build).
        # Otherwise this is a plain preview build into ./site/.
        version_mode = bool(requested_version) or bool(aliases)
        version = requested_version or (get_version("django_components") if version_mode else None)

        if explicit_output is not None:
            # Explicit -o wins (e.g. docs-build-all targeting the main repo's
            # versions/ from inside a worktree). The manifest, if updated, is a
            # sibling of the version dir.
            output_dir = explicit_output
            versions_root = explicit_output.parent
        elif version_mode:
            output_dir = settings.VERSIONS_DIR / str(version)
            versions_root = settings.VERSIONS_DIR
        else:
            output_dir = settings.SITE_DIR
            versions_root = None

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

        # Versioning side-effects (only when writing into a versions/ tree):
        # stamp provenance, update the manifest, and materialize alias redirects.
        if version_mode and version is not None and versions_root is not None:
            write_build_info(
                output_dir,
                version=version,
                source_sha=git_head_sha(settings.REPO_ROOT),
                source_tag=version,
            )
            if do_manifest_update:
                update_manifest(versions_root, version, title=title, aliases=aliases)
                self.stdout.write(f"Updated manifest: {versions_root / 'versions.json'}")
            for alias in aliases:
                n = materialize_alias(versions_root, alias, version)
                self.stdout.write(f"Materialized alias '{alias}/' -> {version} ({n} redirects)")

        # Build the Pagefind search index over the freshly written HTML. Runs
        # after the page build because it scans the output HTML in place.
        if not options["no_search"]:
            self.stdout.write("Building search index (pagefind)...")
            pf = run_pagefind(output_dir)
            if pf.ok:
                self.stdout.write(self.style.SUCCESS(pf.message))
            else:
                self.stderr.write(self.style.ERROR(f"Search index failed: {pf.message}"))
                if pf.output:
                    self.stderr.write(pf.output)
