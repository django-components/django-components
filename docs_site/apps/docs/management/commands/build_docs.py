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

from apps.docs.build.builder import build_site, collect_static, copy_passthroughs
from apps.docs.build.llms import generate_llms_files
from apps.docs.build.minify import minify_site
from apps.docs.build.nav import load_nav
from apps.docs.build.pagefind import run_pagefind
from apps.docs.build.seo import generate_seo_files
from apps.docs.build.social_cards import generate_social_cards
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
            "--no-seo", action="store_true", help="Skip the sitemap.xml / robots.txt / indexing.json generation"
        )
        parser.add_argument("--no-llms", action="store_true", help="Skip the llms.txt / llms-full.txt generation")
        parser.add_argument(
            "--no-social-cards", action="store_true", help="Skip per-page social card (OG image) generation"
        )
        parser.add_argument("--no-minify", action="store_true", help="Skip the post-build HTML minification pass")
        parser.add_argument(
            "--no-collectstatic",
            dest="collectstatic",
            action="store_false",
            help="Don't copy /static into the output (smaller build, but not directly serveable on its own)",
        )
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
        parser.set_defaults(update_manifest=True, collectstatic=True)

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
                # Versioned snapshots self-canonical to /v/<ver>/; the current-version
                # build canonicals to the latest (root) URL. See build_site docstring.
                versioned_canonical=version_mode,
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

        # Copy /static into the output so it serves under a plain static server
        # (pages reference absolute /static/... paths). On by default; skipped for
        # version snapshots - the deploy mounts one shared /static at the root, so
        # per-version dirs don't each duplicate it - and under --no-collectstatic.
        if options["collectstatic"] and not version_mode:
            static_dir = collect_static(output_dir)
            self.stdout.write(self.style.SUCCESS(f"Collected static into {static_dir}"))

            # Pre-built static dirs (the asv benchmark report) copied verbatim at
            # their mount path. Like collect_static, this is root-assembly only -
            # mounted once at the root, not duplicated into per-version snapshots.
            for mount_path, n in copy_passthroughs(output_dir, settings.STATIC_PASSTHROUGHS):
                self.stdout.write(self.style.SUCCESS(f"Copied passthrough '/{mount_path}/' ({n} files)"))

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

        # SEO crawl + index files (sitemap.xml, robots.txt, meta/indexing.json).
        # Only for the current-version build (preview mode): it IS the deployed
        # site root (current version at /), where these belong. Per-version
        # snapshots don't get their own root sitemap; assembling them is Phase 6
        # (feature 6.4). Runs before pagefind so its SiteIndex sees only doc pages.
        if not options["no_seo"] and not version_mode:
            from datetime import datetime, timezone  # noqa: PLC0415

            seo = generate_seo_files(
                output_dir,
                version=version or get_version("django_components"),
                generated_at=datetime.now(timezone.utc),
                versions_root=settings.VERSIONS_DIR,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Wrote SEO files: sitemap ({seo.sitemap_urls} urls), "
                    f"indexing.json ({seo.indexed_pages} pages), "
                    f"robots.txt ({seo.disallowed_versions} version disallows)"
                )
            )

        # AI index files (llms.txt + llms-full.txt). Current-version build only,
        # same as the SEO files. Reads the .md companions, so it's effectively a
        # no-op for llms-full.txt under --no-companions.
        if not options["no_llms"] and not version_mode:
            nav_tree = load_nav(content_dir / "_nav.yml")
            n_links, n_pages = generate_llms_files(content_dir, output_dir, nav_tree, site_url=settings.SITE_URL)
            self.stdout.write(
                self.style.SUCCESS(f"Wrote AI index: llms.txt ({n_links} links), llms-full.txt ({n_pages} pages)")
            )

        # Per-page social cards (OG image PNGs). Current-version build only.
        # Rewrites each page's og:image to its generated card; degrades to the
        # default image if Playwright/Chromium isn't available (never breaks a build).
        if not options["no_social_cards"] and not version_mode:
            cards = generate_social_cards(output_dir, content_dir, site_url=settings.SITE_URL, log=self.stdout.write)
            if cards.skipped_reason:
                self.stdout.write(f"Social cards skipped ({cards.skipped_reason}); pages keep the default OG image")
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Social cards: {cards.placed} placed "
                        f"({cards.rendered} rendered, {cards.cached} cached) of {cards.eligible} pages"
                    )
                )

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

        # Note: there is deliberately NO HTML-sanitization pass here. The §4.7
        # "sanitize" sketch (feature 5c.15) was dropped by design: all rendered
        # content is maintainer-committed (markdown, docstrings, CHANGELOG,
        # examples), so there's no untrusted-input XSS sink, and a bleach pass
        # would only strip our own scripts / JSON-LD / SVG / example iframes.

        # Minify the HTML last, after every other step has finished writing it.
        if not options["no_minify"]:
            mn = minify_site(output_dir, log=self.stdout.write)
            if mn.skipped_reason:
                self.stdout.write(f"Minify skipped ({mn.skipped_reason})")
            elif mn.before:
                saved = 100 * (mn.before - mn.after) / mn.before
                self.stdout.write(self.style.SUCCESS(f"Minified {mn.files} HTML files ({saved:.1f}% smaller)"))
