"""
Dev server for the docs site.

Usage:
    cd docs_site
    python manage.py docs_serve
    python manage.py docs_serve 0.0.0.0:8080
"""

from __future__ import annotations

import pygments_djc  # noqa: F401 -- register the djc_py Pygments lexer
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the docs development server (wraps runserver)."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("addrport", nargs="?", default="127.0.0.1:8000", help="Address:port to bind")

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write(self.style.SUCCESS("Starting docs dev server..."))
        call_command("runserver", str(options["addrport"]))
