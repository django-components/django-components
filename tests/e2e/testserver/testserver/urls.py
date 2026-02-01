import logging

from django.http import HttpResponse
from django.urls import include, path
from testserver.server_discovery import discover_server_functions

logger = logging.getLogger(__name__)

# Discover and register endpoints needed for E2E tests.
#
# It's difficult to manually manage URLs, views, and components for E2E tests.
# So instead, we allow to define those directly within the test files that need them.
#
# Test files in `tests/` directory can define a `server()` function that returns
# a dictionary of `{url_path: view_function}`.
# `discover_server_functions()` scans `test_*.py` files for `server()`, imports each module,
# calls server(), and converts the returned dict into Django path() entries.
discovered_patterns = []
try:
    discovered_patterns = discover_server_functions()
except Exception:
    # Log error but don't crash server startup
    logger.exception("Error during server discovery")

urlpatterns = [
    path("", include("django_components.urls")),
    # Empty response with status 200 to notify other systems when the server has started
    path("poll/", lambda *_args, **_kwargs: HttpResponse("")),  # type: ignore[arg-type]
    # All test views come from test files' `server()` functions
    *discovered_patterns,
]
