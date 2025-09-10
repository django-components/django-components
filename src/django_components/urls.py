from django.urls import include, path

from django_components.dependencies import urlpatterns as dependencies_urlpatterns
from django_components.extension import urlpatterns as extension_urlpatterns

urlpatterns = [
    path(
        "components/",
        include(
            [
                *dependencies_urlpatterns,
                *extension_urlpatterns,
            ],
        ),
    ),
]

__all__ = ["urlpatterns"]
