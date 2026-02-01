import logging

from django.http import HttpResponse
from django.urls import include, path
from testserver.server_discovery import discover_server_functions
from testserver.views import (
    alpine_in_body_vars_not_available_before_view,
    alpine_in_body_view,
    alpine_in_body_view_2,
    alpine_in_head_view,
    check_js_order_in_js_view,
    check_js_order_in_media_view,
    check_js_order_vars_not_available_before_view,
    css_vars_multiple_instances_view,
    css_vars_sized_box_view,
    fragment_base_alpine_view,
    fragment_base_htmx_view,
    fragment_base_htmx_view__raw,
    fragment_base_js_view,
    fragment_view,
    multiple_components_view,
    single_component_view,
)

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
    # Test views
    path("single/", single_component_view, name="single"),
    path("multi/", multiple_components_view, name="multi"),
    path("js-order/js", check_js_order_in_js_view),
    path("js-order/media", check_js_order_in_media_view),
    path("js-order/invalid", check_js_order_vars_not_available_before_view),
    path("fragment/base/alpine", fragment_base_alpine_view),
    path("fragment/base/htmx", fragment_base_htmx_view),
    path("fragment/base/htmx_raw", fragment_base_htmx_view__raw),
    path("fragment/base/js", fragment_base_js_view),
    path("fragment/frag", fragment_view),
    path("alpine/head", alpine_in_head_view),
    path("alpine/body", alpine_in_body_view),
    path("alpine/body2", alpine_in_body_view_2),
    path("alpine/invalid", alpine_in_body_vars_not_available_before_view),
    path("css-vars/multiple", css_vars_multiple_instances_view),
    path("css-vars/sized", css_vars_sized_box_view),
    # Add discovered URL patterns from test files' server() functions
    *discovered_patterns,
]
