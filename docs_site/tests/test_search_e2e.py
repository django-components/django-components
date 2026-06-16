"""
End-to-end browser tests for the Phase 5a search experience.

Builds a tiny static site (a few DocPage-rendered pages), runs Pagefind over
it, copies in the site's static assets, serves it from a background HTTP
server, and drives the search UI in headless Chromium. This is the only test
that exercises the real search.js behavior against a real Pagefind index;
the markup contract is covered by the fast unit tests in test_search.py.

Marked `e2e` and skipped automatically when the Playwright browser binary is
not installed, so the default `pytest tests/` run stays green without browsers
(install with `uv run playwright install chromium`).
"""

from __future__ import annotations

import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING

import pytest
from apps.docs.build.builder import generate_not_found
from apps.docs.build.pagefind import run_pagefind
from apps.docs.components.doc_page.doc_page import DocPage
from django.conf import settings

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.e2e

playwright = pytest.importorskip("playwright.sync_api")


# A handful of pages with predictable, distinct searchable terms.
PAGES = {
    "search-components": (
        "Components",
        "<h1>Components</h1><p>A component is a reusable unit. Components compose "
        "into larger components, and a component renders HTML.</p>",
    ),
    "search-slots": (
        "Slots",
        "<h1>Slots</h1><p>A slot is a placeholder. You fill a slot with content. Slots make components flexible.</p>",
    ),
    "search-install": (
        "Installation",
        "<h1>Installation</h1><p>Install django-components with pip. Installation "
        "takes one command and a settings change.</p>",
    ),
}


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Build + index a tiny site, serve it, and yield its base URL."""
    out = tmp_path_factory.mktemp("search-e2e-site")

    for slug, (title, body) in PAGES.items():
        html = DocPage.render(kwargs={"content_html": body, "title": title})
        page_dir = out / slug
        page_dir.mkdir(parents=True)
        (page_dir / "index.html").write_text(html, encoding="utf-8")

    # The custom 404 (its search button is covered below).
    generate_not_found(out, nav_tree=None, version="test")

    # Search assets (search.js/css, site.js/css, tokens) live under static/.
    shutil.copytree(settings.STATICFILES_DIRS[0], out / "static")

    outcome = run_pagefind(out)
    if not outcome.ok:
        pytest.skip(f"pagefind unavailable: {outcome.message}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(out)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()


@pytest.fixture(scope="module")
def browser() -> Iterator[object]:
    with playwright.sync_playwright() as p:
        try:
            instance = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium not available: {exc}")
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def page(browser: object, site_url: str):  # type: ignore[no-untyped-def]
    ctx = browser.new_context()  # type: ignore[attr-defined]
    pg = ctx.new_page()
    # Track uncaught JS exceptions only. Network 404s (e.g. Chromium's automatic
    # /favicon.ico probe) surface as console "error" messages but aren't a
    # failure signal for our code; a thrown exception is.
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"{site_url}/search-components/", wait_until="networkidle")
    # With a module-scoped browser, a freshly opened context doesn't hold input
    # focus, so keyboard.press would target nothing. Bring it to front.
    pg.bring_to_front()
    pg.js_errors = errors  # type: ignore[attr-defined]
    yield pg
    ctx.close()


def test_trigger_opens_and_esc_closes(page) -> None:  # type: ignore[no-untyped-def]
    trigger = page.query_selector(".djc-search-trigger")
    assert trigger.get_attribute("aria-expanded") == "false"
    assert page.query_selector(".djc-search__overlay").get_attribute("hidden") is not None

    trigger.click()
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    assert trigger.get_attribute("aria-expanded") == "true"
    assert page.evaluate("document.activeElement.classList.contains('djc-search__input')")

    page.keyboard.press("Escape")
    page.wait_for_selector(".djc-search__overlay", state="hidden")
    # Focus is restored to the trigger.
    assert page.evaluate("document.activeElement.classList.contains('djc-search-trigger')")
    assert not page.js_errors


def test_keyboard_shortcuts_open_modal(page) -> None:  # type: ignore[no-untyped-def]
    # Click neutral page content so keyboard events have a focused target
    # (a freshly opened context otherwise has no in-page focus).
    page.click("article.prose h1")

    # Ctrl+K opens
    page.keyboard.press("Control+k")
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    page.keyboard.press("Escape")
    page.wait_for_selector(".djc-search__overlay", state="hidden")

    # "/" opens when not typing in a field
    page.keyboard.press("/")
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    assert not page.js_errors


def test_query_renders_highlighted_results(page) -> None:  # type: ignore[no-untyped-def]
    page.query_selector(".djc-search-trigger").click()
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    page.fill(".djc-search__input", "component")
    page.wait_for_selector(".djc-search__result")
    assert len(page.query_selector_all(".djc-search__result")) > 0
    assert len(page.query_selector_all(".djc-search__result-excerpt mark")) > 0
    assert not page.js_errors


def test_no_results_state(page) -> None:  # type: ignore[no-untyped-def]
    page.query_selector(".djc-search-trigger").click()
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    page.fill(".djc-search__input", "zzzqqqnotarealword")
    page.wait_for_selector("[data-search-noresults]:not([hidden])")
    assert not page.js_errors


def test_result_click_navigates_with_highlight(page) -> None:  # type: ignore[no-untyped-def]
    page.query_selector(".djc-search-trigger").click()
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    # Search a term that lives on a different page, then open that result.
    page.fill(".djc-search__input", "installation")
    page.wait_for_selector(".djc-search__result")
    href = page.query_selector(".djc-search__result").get_attribute("href")
    assert "h=installation" in href, f"result link should carry ?h=: {href}"

    page.query_selector(".djc-search__result").click()
    page.wait_for_load_state("networkidle")
    # The destination page highlights the matched term in its article.
    page.wait_for_selector("article.prose mark.djc-highlight")
    assert "install" in page.query_selector("mark.djc-highlight").inner_text().lower()


def test_404_search_button_opens_modal(page, site_url: str) -> None:  # type: ignore[no-untyped-def]
    page.goto(f"{site_url}/404.html", wait_until="networkidle")
    assert "Page not found" in page.inner_text("h1")
    page.click(".djc-notfound__search")
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    assert not page.js_errors


def test_q_deep_link_opens_prefilled(page, site_url: str) -> None:  # type: ignore[no-untyped-def]
    page.goto(f"{site_url}/search-components/?q=slot", wait_until="networkidle")
    # The modal auto-opens and runs the query from the URL.
    page.wait_for_selector(".djc-search__overlay:not([hidden])")
    assert page.input_value(".djc-search__input") == "slot"
    page.wait_for_selector(".djc-search__result")
    assert not page.js_errors
