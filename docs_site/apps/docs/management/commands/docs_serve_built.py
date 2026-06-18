"""
Build the docs site and serve it the way it is deployed.

Unlike `docs_serve` (which renders pages live and has no search index), this
produces the real static build - Pagefind search index + collected `/static/` -
and serves it over plain HTTP. Use it to test anything that only works against
the built site (search, the post-build artifacts, etc.).

Pass `--versions` to additionally fake a multi-version tree under `site/v/<ver>/`
so the version picker (latest / dev / specific-version switching) can be tested
without real historical builds - older tags predate the docs builder, so this
relabels the *current* content under several version labels. Tell the fakes
apart by the picker, the footer version, and the URL; content is identical.

`site/` is gitignored, so nothing here is committed.

Usage:
    cd docs_site
    python manage.py docs_serve_built                  # build current -> site/, serve at :8000
    python manage.py docs_serve_built --port 9000
    python manage.py docs_serve_built --no-build       # serve the existing ./site/
    python manage.py docs_serve_built --versions       # fake a demo version tree, then serve
    python manage.py docs_serve_built --versions 0.151.0 0.150.0 dev --latest 0.151.0
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


def _decrement_minor(version: str) -> str | None:
    """A plausible older version string (one minor down), or None if not derivable."""
    parts = version.split(".")
    if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) > 0:
        return f"{parts[0]}.{int(parts[1]) - 1}.0"
    return None


class Command(BaseCommand):
    help = "Build the docs site (with the Pagefind index) and serve it like production."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
        parser.add_argument("-p", "--port", type=int, default=8000, help="Bind port (default: 8000)")
        parser.add_argument("--no-build", action="store_true", help="Serve the existing ./site/ without rebuilding")
        parser.add_argument("--no-serve", action="store_true", help="Build but don't serve")
        parser.add_argument(
            "--versions",
            nargs="*",
            default=None,
            metavar="V",
            help="Fake a version tree under site/v/ for picker testing (no values = demo set: current + older + dev)",
        )
        parser.add_argument(
            "--latest", type=str, default=None, help="Version the latest alias points at (default: newest non-dev)"
        )

    def handle(self, *args: object, **options: object) -> None:
        site_dir: Path = settings.SITE_DIR
        versions = cast("list[str] | None", options["versions"])

        if not options["no_build"]:
            if versions is None:
                # Plain built site: build_docs writes ./site/ (current version at
                # the root) + Pagefind, and collects /static by default.
                call_command("build_docs")
            else:
                self._build_version_tree(site_dir, versions or self._default_versions(), options["latest"])

        if not site_dir.is_dir():
            raise CommandError(f"No build at {site_dir}. Run without --no-build first.")

        if options["no_serve"]:
            self.stdout.write(self.style.SUCCESS(f"Built at {site_dir} (not serving)."))
            return

        port = int(cast("int", options["port"]))
        self._serve(site_dir, str(options["host"]), port, versioned=versions is not None)

    # -- version-tree mode -----------------------------------------------------

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

    def _build_version_tree(self, site_dir: Path, versions: list[str], latest_opt: object) -> None:
        latest = str(latest_opt) if latest_opt else self._pick_latest(versions)
        # Fresh tree each run: clear the (gitignored) site/ so no stale page lingers.
        if site_dir.exists():
            shutil.rmtree(site_dir)
        versions_root = site_dir / "v"
        for version in versions:
            self.stdout.write(f"Building {version}...")
            # Real build_docs version-mode: writes site/v/<version>/, accumulates
            # versions.json, and materializes the latest alias.
            call_command(
                "build_docs",
                docs_version=version,
                output=str(versions_root / version),
                alias=["latest"] if version == latest else None,
                title="dev (local)" if version == DEV else None,
                no_search=True,
                no_companions=True,
            )
        # The picker only populates under /v/<version>/, so redirect the root to a
        # real versioned page rather than leaving it a dead end.
        target = latest or versions[0]
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "index.html").write_text(render_redirect(f"v/{target}/index.html"), encoding="utf-8")
        # Version builds skip /static (the deploy mounts one shared copy at root);
        # symlink it to the live source so CSS/JS edits show on a browser refresh.
        self._link_static(site_dir)
        self.stdout.write(self.style.SUCCESS(f"Built {len(versions)} version(s); / and latest -> {target}"))

    def _link_static(self, site_dir: Path) -> None:
        dirs = getattr(settings, "STATICFILES_DIRS", None)
        source = Path(dirs[0]) if dirs else Path(settings.BASE_DIR) / "static"
        link = site_dir / "static"
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.is_dir():
            shutil.rmtree(link)
        link.symlink_to(source)

    # -- serving ---------------------------------------------------------------

    def _serve(self, site_dir: Path, host: str, port: int, *, versioned: bool) -> None:
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site_dir))
        server = ThreadingHTTPServer((host, port), handler)
        base = f"http://{host}:{port}"
        landing = "/" if versioned else "/docs/"
        self.stdout.write(self.style.SUCCESS(f"Serving built site at {base}{landing}  (Ctrl-C to stop)"))
        if versioned:
            for name in sorted(p.name for p in (site_dir / "v").iterdir() if p.is_dir()):
                self.stdout.write(f"  {base}/v/{name}/")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nStopped.")
        finally:
            server.server_close()
