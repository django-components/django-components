# ruff: noqa: T201

import functools
import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.async_api import async_playwright

TEST_SERVER_PORT = "8000"
TEST_SERVER_URL = f"http://127.0.0.1:{TEST_SERVER_PORT}"


# NOTE: Ideally we'd use Django's setUpClass and tearDownClass methods
#       to instantiate the browser instance only once. But didn't have luck with that.
#       So instead we have to create a browser instance for each test.
#
#       Additionally, Django's documentation is lacking on async setUp and tearDown,
#       so instead we use a decorator to run async code before/after each test.
def with_playwright(test_func):
    """Decorator that sets up and tears down Playwright browser instance."""

    @functools.wraps(test_func)
    async def wrapper(self, *args, **kwargs):
        # Setup
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

        # Test
        await test_func(self, *args, **kwargs)

        # Teardown
        await self.browser.close()
        await self.playwright.stop()

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
