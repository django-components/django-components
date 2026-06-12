"""
CI gate: build the docs to a throwaway dir and run every guardrail.

This is the PR check (spike 11.9 section 4). It builds the full site to a temp
directory (writing nothing permanent), then runs the guardrail harness over it
in strict mode by default - so a broken link, unclosed fence, or unknown
lexer fails the build. The temp dir is discarded on completion.

Template-render failures (a page that raises in the pipeline) are folded into
the report as `template_render` errors rather than crashing the command.

Usage:
    cd docs_site
    python manage.py docs_build_check            # strict; non-zero exit on any error/warning
    python manage.py docs_build_check --no-strict  # errors fail, warnings don't
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pygments_djc  # noqa: F401 -- register djc_py so the lexer-alias guard resolves it
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.builder import build_site
from apps.docs.build.guard_runner import make_context
from apps.docs.build.guards import format_report, run_guards


class Command(BaseCommand):
    help = "Build the docs to a temp dir and run the guardrail suite (CI gate)."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--content", type=str, default=None, help="Content dir (default: settings.CONTENT_DIR)")
        parser.add_argument("--docs-version", type=str, default=None, help="Version string (default: from package)")
        parser.add_argument(
            "--no-strict",
            dest="strict",
            action="store_false",
            help="Only errors fail (default: warnings fail too)",
        )
        parser.set_defaults(strict=True)

    def handle(self, *args: object, **options: object) -> None:
        content_dir = Path(str(options["content"])) if options["content"] else settings.CONTENT_DIR
        if not content_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"Content directory not found: {content_dir}"))
            raise SystemExit(1)

        version = str(options["docs_version"]) if options["docs_version"] else None
        strict = bool(options["strict"])

        with tempfile.TemporaryDirectory(prefix="docs-build-check-") as tmp:
            build_dir = Path(tmp) / "site"
            self.stdout.write(f"Building {content_dir} -> (temp) and running guardrails...")
            try:
                outcome = build_site(
                    content_dir=content_dir,
                    output_dir=build_dir,
                    version=version,
                    emit_companions=True,
                )
            except ValueError as e:
                self.stderr.write(self.style.ERROR(str(e)))
                raise SystemExit(1) from e

            self.stdout.write(f"Built {outcome.built} pages ({outcome.failed} render failures)")

            ctx = make_context(build_dir, content_dir=content_dir)
            results, ok = run_guards(ctx, strict=strict)
            # Fold template-render failures (captured during the build) into the report.
            results = outcome.render_errors + results
            if outcome.render_errors:
                ok = False

            self.stdout.write(format_report(results))

        if ok:
            self.stdout.write(self.style.SUCCESS("OK"))
        else:
            self.stderr.write(self.style.ERROR("FAIL"))
            raise SystemExit(1)
