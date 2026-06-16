"""
docs-preview: build a few fake versions locally and serve them, to exercise the
version picker (latest / dev / specific-version switching) without needing real
historical builds.

Real historical versions can't be rebuilt yet (older tags predate the docs
builder - see docs-build-all), so this fakes a version tree from the *current*
content: it builds the current source under several version labels into
``site/v/<version>/`` (so each page's picker + footer carry the right version),
points the ``latest`` alias at the newest release, adds a ``dev`` build, symlinks
``/static`` to the live source (so CSS/JS edits show on a browser refresh), and
serves it like the deployed site.

``site/`` is gitignored, so nothing here is committed. Content is identical
across versions (the current source relabeled); tell them apart by the picker,
the footer version, and the URL.

Usage:
    cd docs_site
    python manage.py docs_preview                       # demo set, serve at :8137
    python manage.py docs_preview --versions 0.151.0 0.150.0 0.149.0 --latest 0.151.0
    python manage.py docs_preview --no-build            # serve the existing site/
    python manage.py docs_preview --no-serve            # build the tree, don't serve
"""

from __future__ import annotations

import functools
import shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version as get_version
from pathlib import Path
from typing import cast

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.docs._vendor.mike_versions import Versions
from apps.docs.build.versioning import render_redirect

DEV = "dev"
DEFAULT_PORT = 8137


def _decrement_minor(version: str) -> str | None:
    """A plausible older version string (one minor down), or None if not derivable."""
    parts = version.split(".")
    if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) > 0:
        return f"{parts[0]}.{int(parts[1]) - 1}.0"
    return None


class Command(BaseCommand):
    help = "Build a few fake versions and serve them to test the version picker."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--versions",
            nargs="+",
            default=None,
            metavar="V",
            help="Versions to fake (default: current pyproject version + one older + dev)",
        )
        parser.add_argument(
            "--latest", type=str, default=None, help="Version the latest alias points at (default: newest non-dev)"
        )
        parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
        parser.add_argument(
            "-p", "--port", type=int, default=DEFAULT_PORT, help=f"Bind port (default: {DEFAULT_PORT})"
        )
        parser.add_argument("--no-build", action="store_true", help="Serve the existing site/ without rebuilding")
        parser.add_argument("--no-serve", action="store_true", help="Build the preview tree but don't serve it")

    def handle(self, *args: object, **options: object) -> None:
        site_dir: Path = settings.SITE_DIR
        versions_root = site_dir / "v"

        if not options["no_build"]:
            requested = cast("list[str] | None", options["versions"])
            versions = requested or self._default_versions()
            latest = str(options["latest"]) if options["latest"] else self._pick_latest(versions)
            self._build(site_dir, versions, latest)
            self._link_static(site_dir)

        if not versions_root.is_dir():
            raise CommandError(f"No preview tree at {versions_root}. Run without --no-build first.")

        if options["no_serve"]:
            self.stdout.write(self.style.SUCCESS(f"Preview built at {versions_root} (not serving)."))
            return

        self._serve(site_dir, versions_root, str(options["host"]), int(options["port"]))  # type: ignore[call-overload]

    def _default_versions(self) -> list[str]:
        current = get_version("django_components")
        older = _decrement_minor(current)
        return [v for v in (current, older) if v] + [DEV]

    def _pick_latest(self, versions: list[str]) -> str | None:
        """The newest non-dev version (by LooseVersion), or None if only dev."""
        releases = [v for v in versions if v != DEV]
        if not releases:
            return None
        collection = Versions()
        for v in releases:
            collection.add(v)
        return str(next(iter(collection)).version)

    def _build(self, site_dir: Path, versions: list[str], latest: str | None) -> None:
        # Fresh tree each run: clear the (gitignored) site/ dir so no stale page
        # lingers at `/`, then build each version under site/v/.
        if site_dir.exists():
            shutil.rmtree(site_dir)
        versions_root = site_dir / "v"
        for version in versions:
            self.stdout.write(f"Building {version}...")
            # Reuse the real build_docs version-mode: writes site/v/<version>/,
            # accumulates versions.json, and materializes the latest alias.
            call_command(
                "build_docs",
                docs_version=version,
                output=str(versions_root / version),
                alias=["latest"] if version == latest else None,
                title="dev (local)" if version == DEV else None,
                no_search=True,
                no_companions=True,
            )
        # Redirect `/` to a real versioned page: the picker only populates under
        # /v/<version>/, so the site root must not be a dead end.
        target = latest or versions[0]
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "index.html").write_text(render_redirect(f"v/{target}/index.html"), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Built {len(versions)} version(s); / and latest -> {target}"))

    def _link_static(self, site_dir: Path) -> None:
        """Symlink site/static -> the live static source, for refresh-only CSS/JS iteration."""
        dirs = getattr(settings, "STATICFILES_DIRS", None)
        source = Path(dirs[0]) if dirs else Path(settings.BASE_DIR) / "static"
        link = site_dir / "static"
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.is_dir():
            shutil.rmtree(link)
        link.symlink_to(source)

    def _serve(self, site_dir: Path, versions_root: Path, host: str, port: int) -> None:
        names = sorted(p.name for p in versions_root.iterdir() if p.is_dir())
        base = f"http://{host}:{port}"
        self.stdout.write(self.style.SUCCESS(f"Serving preview at {base}/  (Ctrl-C to stop)"))
        self.stdout.write(f"  {base}/  -> redirects to the latest version")
        for name in names:
            self.stdout.write(f"  {base}/v/{name}/")
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site_dir))
        server = ThreadingHTTPServer((host, port), handler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nStopped.")
        finally:
            server.server_close()
