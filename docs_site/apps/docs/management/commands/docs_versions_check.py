"""
docs-versions-check: validate the committed docs_site/versions/ tree (5b.13-5b.15).

The inverse of docs-build: it doesn't build anything, it checks that the
on-disk version tree is internally consistent - manifest <-> filesystem parity,
alias redirects resolve, build stamps are sane, and every relative link across
the version subtrees resolves on disk. Runs the VERSION_GUARDS through the same
guard harness as docs_build_check (shared GuardResult / severity / report).

Use it locally (`python manage.py docs_versions_check`) and in CI on any change
that touches docs_site/versions/ or docs_versions.toml. Spec: DESIGN_spike_7.md
section 11.

Usage:
    cd docs_site
    python manage.py docs_versions_check               # strict; warnings fail too
    python manage.py docs_versions_check --no-strict    # only errors fail
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.guard_runner import make_versions_context
from apps.docs.build.guards import VERSION_GUARDS, format_report, run_guards


class Command(BaseCommand):
    help = "Validate the committed docs_site/versions/ tree (manifest, aliases, stamps, links)."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--versions-dir", type=str, default=None, help="Version tree to check (default: settings.VERSIONS_DIR)"
        )
        parser.add_argument(
            "--no-strict",
            dest="strict",
            action="store_false",
            help="Only errors fail (default: warnings fail too)",
        )
        parser.set_defaults(strict=True)

    def handle(self, *args: object, **options: object) -> None:
        versions_root = Path(str(options["versions_dir"])) if options["versions_dir"] else settings.VERSIONS_DIR
        strict = bool(options["strict"])

        if not versions_root.is_dir():
            # Nothing committed yet (pre-bootstrap) is a valid, passing state.
            self.stdout.write(f"No version tree at {versions_root} - nothing to check.")
            return

        ctx = make_versions_context(versions_root)
        results, ok = run_guards(ctx, strict=strict, guards=VERSION_GUARDS)
        self.stdout.write(format_report(results))

        if ok:
            self.stdout.write(self.style.SUCCESS("OK"))
        else:
            self.stderr.write(self.style.ERROR("FAIL"))
            raise SystemExit(1)
