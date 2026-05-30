from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from playwright.async_api import Playwright, async_playwright

from tests.e2e.utils import BROWSER_NAMES, BrowserType, _launch_browser, run_django_dev_server

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest


@pytest.fixture(scope="session")
def django_dev_server():
    """Fixture to run Django development server in the background."""
    yield from run_django_dev_server()


# Auto-tag every test in the four benchmark files with `@pytest.mark.benchmark_snapshot`.
# The marker is what the CI lane split keys off: the default tox env runs with
# `-m "not benchmark_snapshot"` and the dedicated `benchmark_snapshot` tox env runs
# with `-m benchmark_snapshot`. Doing the tagging here (instead of decorating each
# test) means new tests added to these files are picked up automatically and the
# "what counts as a benchmark" rule lives in one place.
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = item.path
        if path.name in {
            "test_benchmark_django.py",
            "test_benchmark_django_small.py",
            "test_benchmark_djc.py",
            "test_benchmark_djc_small.py",
        }:
            item.add_marker(pytest.mark.benchmark_snapshot)


@pytest_asyncio.fixture(scope="session")
async def playwright():
    """Session-scoped fixture to create a single Playwright instance for all tests."""
    pw = await async_playwright().start()
    yield pw
    await pw.stop()


@pytest.fixture(scope="session", params=BROWSER_NAMES, ids=BROWSER_NAMES)
def browser_name(request: "FixtureRequest") -> BrowserType:
    """
    Parametrized fixture that provides the browser name for the current test.

    This fixture is automatically parametrized with all browser types (chromium, firefox, webkit),
    causing tests to run once per browser type.
    """
    browser_name_value = request.param
    return browser_name_value


@pytest_asyncio.fixture(scope="session")
async def browser(playwright: Playwright, browser_name: BrowserType):
    """
    Session-scoped fixture that provides browser instances.

    This fixture depends on `browser_name` (which is parametrized), so it will create
    one browser instance per browser type that is reused across all tests.
    """
    browser = await _launch_browser(playwright, browser_name)
    yield browser
    await browser.close()
