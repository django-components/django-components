"""
Run the guardrail suite over an already-built docs site.

Replaces the Phase-1 bespoke link/anchor checker with the unified guardrail
harness (SiteIndex + all source/post-build guards). Use this to validate a
build you already produced with `build_docs`; use `docs_build_check` to build
to a throwaway dir and validate in one step (the CI gate).

Usage:
    cd docs_site
    python manage.py docs_test                  # checks the default ./site/ build
    python manage.py docs_test /tmp/preview     # checks a custom build directory
    python manage.py docs_test --strict         # warnings fail too
"""

from __future__ import annotations

from pathlib import Path

import pygments_djc  # noqa: F401 -- register djc_py so the lexer-alias guard resolves it
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.guard_runner import make_context
from apps.docs.build.guards import format_report, run_guards


class Command(BaseCommand):
    help = "Run the docs guardrail suite over a built site."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "build_dir", type=str, nargs="?", default=None, help="Built docs directory (default: ./site/)"
        )
        parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings too")

    def handle(self, *args: object, **options: object) -> None:
        build_dir = Path(str(options["build_dir"])).resolve() if options["build_dir"] else settings.SITE_DIR.resolve()
        if not build_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"Build directory not found: {build_dir}"))
            raise SystemExit(1)

        ctx = make_context(build_dir)
        strict = bool(options["strict"])
        results, ok = run_guards(ctx, strict=strict)

        self.stdout.write(format_report(results))
        if ok:
            self.stdout.write(self.style.SUCCESS("OK"))
        else:
            self.stderr.write(self.style.ERROR("FAIL"))
            raise SystemExit(1)
