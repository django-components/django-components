"""
Post-build link validator for the docs site.

Walks all .html files in the build output directory, extracts every <a href>,
and checks that:
  1. Internal links resolve to an existing built page
  2. #anchor fragments match an id= or name= attribute on the target page

This is the Phase 1 MVP of the guardrail system described in design spike 11.10.
The full SiteIndex-based guardrail harness replaces this in Phase 3b/5.

Usage:
    cd docs_site
    python manage.py docs_test                 # checks the default ./site/ build
    python manage.py docs_test /tmp/preview     # checks a custom build directory
    python manage.py docs_test --strict
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.docs.build.guards import check_example_contracts
from apps.docs.examples import get_example_registry

# Regex patterns for extracting links and anchor targets from built HTML
HREF_RE = re.compile(r'<a\s[^>]*href="([^"]*)"', re.IGNORECASE)
ID_RE = re.compile(r'\bid="([^"]*)"', re.IGNORECASE)
NAME_RE = re.compile(r'\bname="([^"]*)"', re.IGNORECASE)  # legacy anchors use name= not id=


class Command(BaseCommand):
    help = "Validate internal links and anchors in built docs."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "build_dir", type=str, nargs="?", default=None, help="Built docs directory (default: ./site/)"
        )
        parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings too")

    def handle(self, *args: object, **options: object) -> None:
        build_dir = Path(str(options["build_dir"])).resolve() if options["build_dir"] else settings.SITE_DIR.resolve()
        if not build_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"Build directory not found: {build_dir}"))
            return

        html_files = sorted(build_dir.rglob("*.html"))
        if not html_files:
            self.stderr.write(self.style.WARNING(f"No .html files found in {build_dir}"))
            return

        # Phase 1: build an index of every page and its anchor targets (id= and name= attrs)
        page_index: dict[str, set[str]] = {}
        for html_path in html_files:
            rel = str(html_path.relative_to(build_dir))
            content = html_path.read_text(encoding="utf-8")
            ids = set(ID_RE.findall(content))
            ids.update(NAME_RE.findall(content))  # include legacy <a name="..."> anchors
            page_index[rel] = ids

        existing_pages = set(page_index.keys())

        errors = 0
        warnings = 0

        # Phase 2: check every link in every page
        for html_path in html_files:
            rel = str(html_path.relative_to(build_dir))
            content = html_path.read_text(encoding="utf-8")
            hrefs = HREF_RE.findall(content)

            for raw_href in hrefs:
                href = unquote(raw_href)

                # Skip external links, mailto, javascript, and empty hrefs
                if not href or href.startswith(("http://", "https://", "mailto:", "javascript:", "#")):
                    if href.startswith("#"):
                        # Same-page anchor - check it resolves within this page
                        anchor = href[1:]
                        if anchor and anchor not in page_index.get(rel, set()):
                            self.stderr.write(self.style.ERROR(f"  {rel}: broken anchor #{anchor}"))
                            errors += 1
                    continue

                parsed = urlparse(href)
                target_path = parsed.path
                anchor = parsed.fragment

                # Resolve the target to a path relative to the build root
                if target_path.startswith("/"):
                    target_rel = target_path.lstrip("/")
                else:
                    # Resolve relative to the current page's directory within the build tree
                    page_dir = (build_dir / rel).parent
                    resolved_abs = (page_dir / target_path).resolve()
                    try:
                        target_rel = str(resolved_abs.relative_to(build_dir.resolve()))
                    except ValueError:
                        # Link points outside the built site
                        self.stderr.write(self.style.ERROR(f"  {rel}: link escapes site -> {href}"))
                        errors += 1
                        continue

                # Try to find the target page (handles clean URLs like /foo/ -> foo/index.html)
                resolved = _resolve_target(target_rel, existing_pages)
                if resolved is None:
                    self.stderr.write(self.style.ERROR(f"  {rel}: broken link -> {href}"))
                    errors += 1
                    continue

                # If the link has an anchor fragment, check it exists on the target page
                if anchor and anchor not in page_index.get(resolved, set()):
                    self.stderr.write(
                        self.style.WARNING(f"  {rel}: broken anchor {href} (page exists, anchor missing)")
                    )
                    warnings += 1

        # Example guardrails
        registry = get_example_registry()

        contract_errors = check_example_contracts(settings.CONTENT_DIR, settings.EXAMPLES_DIR, registry)
        for msg in contract_errors:
            self.stderr.write(self.style.ERROR(f"  example-contract: {msg}"))
        errors += len(contract_errors)

        total = len(html_files)
        self.stdout.write(f"Checked {total} pages: {errors} errors, {warnings} warnings")

        if errors or (options["strict"] and warnings):
            self.stderr.write(self.style.ERROR("FAIL"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("OK"))


def _resolve_target(target_rel: str, existing_pages: set[str]) -> str | None:
    """
    Try to resolve a relative link target to an existing built page.

    Handles clean-URL patterns: /foo/ -> foo/index.html, /foo -> foo.html or foo/index.html
    """
    if target_rel in existing_pages:
        return target_rel

    candidates = [
        target_rel + "/index.html",
        target_rel.rstrip("/") + "/index.html",
        target_rel + ".html",
    ]
    if target_rel.endswith("/"):
        candidates.append(target_rel + "index.html")

    for c in candidates:
        normalized = str(Path(c))
        if normalized in existing_pages:
            return normalized

    return None
