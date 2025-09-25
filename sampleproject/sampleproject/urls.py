from django.urls import include, path

urlpatterns = [
    path("", include("calendarapp.urls")),
    path("", include("components.urls")),
    path("", include("examples.urls")),
    path("", include("django_components.urls")),
]
