"""
Build the docs site and serve it the way it is deployed.

Unlike `docs_serve` (which renders pages on the fly and has no search index),
this command produces the real static build - including the Pagefind search
index and the collected `/static/` assets - and serves it over plain HTTP. Use
it to test anything that only works against the built site, above all search.

Usage:
    cd docs_site
    python manage.py docs_serve_built                 # build, then serve at :8000
    python manage.py docs_serve_built --port 9000
    python manage.py docs_serve_built --no-build      # serve the existing ./site/
"""

from __future__ import annotations

import functools
import shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Build the docs site (with the Pagefind search index) and serve it like production."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
        parser.add_argument("-p", "--port", type=int, default=8000, help="Bind port (default: 8000)")
        parser.add_argument("--no-build", action="store_true", help="Serve the existing ./site/ without rebuilding")

    def handle(self, *args: object, **options: object) -> None:
        site_dir = settings.SITE_DIR

        if not options["no_build"]:
            # build_docs writes ./site/ and runs Pagefind over it.
            call_command("build_docs")
            # Collect /static/ into the built site so asset URLs resolve exactly
            # as they do in production (build_docs deliberately doesn't do this).
            # collectstatic writes to settings.STATIC_ROOT (the staticfiles
            # storage caches that path, so it can't be retargeted at runtime);
            # copy the result into the build, then drop the intermediate.
            self.stdout.write("Collecting static files into the build...")
            call_command("collectstatic", "--no-input", "--clear", verbosity=0)
            static_root = Path(settings.STATIC_ROOT)
            shutil.copytree(static_root, site_dir / "static", dirs_exist_ok=True)
            shutil.rmtree(static_root, ignore_errors=True)

        if not site_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"No build found at {site_dir}. Run without --no-build first."))
            return

        host = str(options["host"])
        port = int(options["port"])  # type: ignore[call-overload]
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site_dir))
        server = ThreadingHTTPServer((host, port), handler)
        self.stdout.write(self.style.SUCCESS(f"Serving built site at http://{host}:{port}/docs/  (Ctrl-C to stop)"))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nStopped.")
        finally:
            server.server_close()
