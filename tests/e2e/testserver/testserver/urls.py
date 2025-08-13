from django.http import HttpResponse
from django.urls import include, path
from testserver.views import (
    alpine_in_body_vars_not_available_before_view,
    alpine_in_body_view,
    alpine_in_body_view_2,
    alpine_in_head_view,
    check_js_order_in_js_view,
    check_js_order_in_media_view,
    check_js_order_vars_not_available_before_view,
    fragment_base_alpine_view,
    fragment_base_htmx_view,
    fragment_base_htmx_view__raw,
    fragment_base_js_view,
    fragment_view,
    multiple_components_view,
    single_component_view,
)

urlpatterns = [
    path("", include("django_components.urls")),
    # Empty response with status 200 to notify other systems when the server has started
    path("poll/", lambda *args, **kwargs: HttpResponse("")),
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
]
