# ruff: noqa: T201

import functools
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypeAlias

import pytest
import requests
from playwright.async_api import Browser, Playwright

TEST_SERVER_PORT = "8000"
TEST_SERVER_URL = f"http://127.0.0.1:{TEST_SERVER_PORT}"


BROWSER_NAMES = ["chromium", "firefox", "webkit"]
BrowserType: TypeAlias = Literal["chromium", "firefox", "webkit"]


async def _launch_browser(playwright: Playwright, browser_name: BrowserType) -> Browser:
    if browser_name == "chromium":
        browser = await playwright.chromium.launch()
    elif browser_name == "firefox":
        browser = await playwright.firefox.launch()
    elif browser_name == "webkit":
        browser = await playwright.webkit.launch()
    else:
        raise ValueError(f"Unknown browser: {browser_name}")
    return browser


def with_playwright(test_func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that provides Playwright browser instance as a pytest fixture.

    Tests decorated with this will automatically run across all major browsers:
    Chromium, Firefox, and WebKit.

    The browser instance is reused across all tests (session-scoped) for better performance.
    """

    # NOTE: Using `browser` and `browser_name` as fixtures means that the test will be run
    #       once per browser type (chromium, firefox, webkit).
    @functools.wraps(test_func)
    @pytest.mark.asyncio(scope="session")  # Needed to run the test in async mode
    async def wrapper(self: Any, browser: Browser, browser_name: BrowserType, *args: Any, **kwargs: Any) -> Any:
        # Test
        await test_func(self, *args, browser=browser, browser_name=browser_name, **kwargs)

    return wrapper


def run_django_dev_server():
    """Fixture to run Django development server in the background."""
    # Get the path where testserver is defined, so the command doesn't depend
    # on user's current working directory.
    testserver_dir = (Path(__file__).parent / "testserver").resolve()

    # Start the Django dev server in the background
    print("Starting Django dev server...")
    proc = subprocess.Popen(
        # NOTE: Use `sys.executable` so this works both for Unix and Windows OS
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{TEST_SERVER_PORT}", "--noreload"],
        cwd=testserver_dir,
    )

    # Wait for the server to start by polling
    start_time = time.time()
    while time.time() - start_time < 30:  # timeout after 30 seconds
        try:
            response = requests.get(f"http://127.0.0.1:{TEST_SERVER_PORT}/poll")  # noqa: S113
            if response.status_code == 200:
                print("Django dev server is up and running.")
                break
        except requests.RequestException:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("Django server failed to start within the timeout period")

    yield  # Hand control back to the test session

    # Teardown: Kill the server process after the tests
    proc.terminate()
    proc.wait()

    print("Django dev server stopped.")
