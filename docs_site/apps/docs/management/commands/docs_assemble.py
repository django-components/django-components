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

from apps.docs._vendor.mike_versions import Versions
from apps.docs.build.bootstrap import load_versions_config
from apps.docs.build.versioning import load_manifest, select_published_versions, write_manifest


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
        parser.add_argument(
            "--no-dev",
            action="store_true",
            help="Skip building the ephemeral /v/dev/ snapshot.",
        )
        parser.add_argument(
            "--dev-title",
            type=str,
            default="dev",
            help="Picker title for the dev version (default: 'dev'; CI passes 'dev (<sha>)').",
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
            window = load_versions_config(settings.VERSIONS_CONFIG).publish_window
            published = self._publish_versions(versions_root, site_dir / "v", window)
            note = f" (newest {window} of the committed tree)" if window and len(published) >= window else ""
            self.stdout.write(self.style.SUCCESS(f"Mounted {len(published)} version(s) under {site_dir / 'v'}{note}"))
        else:
            self.stdout.write(f"No versions tree at {versions_root}; assembled current version only.")

        # Build the ephemeral dev snapshot. Unlike releases, dev is NOT committed
        # (feature 10.7): it's rebuilt fresh into /v/dev/ on every deploy and
        # added to the *served* manifest so the picker lists it, while the
        # committed manifest stays release-only. This keeps master history free of
        # the per-push dev churn that committing dev/ would cause.
        if not options["no_dev"]:
            self._build_dev(site_dir, str(options["dev_title"]))

        # Now that /v/versions.json exists, mark the root pages' version picker so
        # its JS fetches the manifest. build_docs-only sites (local preview,
        # Lighthouse) skip this, so their picker stays static and never 404s on a
        # manifest that isn't there.
        if (site_dir / "v" / "versions.json").is_file():
            n = self._enable_root_version_picker(site_dir, settings.SITE_BASE_PATH)
            self.stdout.write(self.style.SUCCESS(f"Enabled the root version picker on {n} page(s)"))

        self.stdout.write(self.style.SUCCESS(f"Assembled deploy artifact at {site_dir}"))

    def _enable_root_version_picker(self, site_dir: Path, base: str) -> int:
        """
        Add ``data-versions-root`` to the root pages' version picker so site.js
        fetches the manifest there (the current docs at the root have no ``/v/``
        segment to derive it from). Only docs_assemble does this - it's the only
        builder that produces ``/v/versions.json`` - so a plain ``build_docs`` site
        leaves the picker static and never fetches a 404. The ``/v/<version>/``
        pages derive the path from their own URL, so they're skipped.
        """
        needle = "data-version-picker"
        replacement = f'data-version-picker data-versions-root="{base}/v/"'
        v_dir = site_dir / "v"
        changed = 0
        for html in site_dir.rglob("*.html"):
            if v_dir in html.parents:
                continue
            text = html.read_text(encoding="utf-8")
            if needle in text and "data-versions-root" not in text:
                html.write_text(text.replace(needle, replacement), encoding="utf-8")
                changed += 1
        return changed

    def _publish_versions(self, versions_root: Path, dest_v: Path, window: int) -> list[str]:
        """
        Copy the published subset of committed versions into ``dest_v`` and write a
        trimmed served manifest. The committed tree is never modified; ``window``
        only bounds what the deploy mounts (GitHub Pages' 1 GB cap). Returns the
        published version list.
        """
        manifest = load_manifest(versions_root)
        published = select_published_versions(manifest, window)
        published_set = set(published)

        trimmed = Versions()
        for info in manifest:
            version = str(info.version)
            if version not in published_set:
                continue
            shutil.copytree(versions_root / version, dest_v / version, dirs_exist_ok=True)
            trimmed.add(version, title=info.title, aliases=list(info.aliases))
            # Copy each alias dir (e.g. latest/) whose target version is published.
            for alias in info.aliases:
                alias_dir = versions_root / alias
                if alias_dir.is_dir():
                    shutil.copytree(alias_dir, dest_v / alias, dirs_exist_ok=True)
        write_manifest(dest_v, trimmed)
        return published

    def _build_dev(self, site_dir: Path, dev_title: str) -> None:
        dest_v = site_dir / "v"
        dev_dir = dest_v / "dev"
        if dev_dir.exists():
            shutil.rmtree(dev_dir)
        # Version-mode build into /v/dev/ without touching any committed manifest
        # (update_manifest=False). Version mode already skips the root-only SEO /
        # social / llms / collectstatic steps; --no-search keeps it light.
        call_command(
            "build_docs",
            docs_version="dev",
            title=dev_title,
            output=str(dev_dir),
            update_manifest=False,
            no_search=True,
            no_companions=True,
        )
        # Add dev to the SERVED manifest only (the committed one is release-only).
        served = load_manifest(dest_v)
        served.add("dev", title=dev_title)
        write_manifest(dest_v, served)
        # /v/dev/ is bleeding-edge and mirrors the root content, so keep it out of
        # search. The root robots.txt is built from the committed (dev-less)
        # manifest, so add the dev disallow here.
        self._disallow_dev_in_robots(site_dir)
        self.stdout.write(self.style.SUCCESS(f"Built ephemeral dev snapshot at {dev_dir} (not committed)"))

    def _disallow_dev_in_robots(self, site_dir: Path) -> None:
        robots = site_dir / "robots.txt"
        if not robots.is_file():
            return
        text = robots.read_text(encoding="utf-8")
        if "Disallow: /v/dev/" in text:
            return
        # Insert right after the initial "Allow: /" so dev sits with the other
        # version disallows under the "User-agent: *" group.
        text = text.replace("Allow: /\n", "Allow: /\nDisallow: /v/dev/\n", 1)
        robots.write_text(text, encoding="utf-8")
