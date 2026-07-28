from django.urls import include, path

urlpatterns: list = [
    path("", include("django_components.urls")),
    # Docs catch-all - must stay last so the above routes win
    path("", include("apps.docs.urls")),
]
