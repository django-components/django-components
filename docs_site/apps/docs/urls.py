from django.urls import path, re_path

from . import views

urlpatterns = [
    # Serve example fragment responses live during dev (before the catch-all)
    path("examples/<str:name>/", views.serve_example, name="example_page"),
    path("examples/<str:name>/<str:variant>/", views.serve_example_fragment, name="example_fragment"),
    # Catch-all: any remaining path resolves to a content markdown page
    re_path(r"^(?P<url_path>.*)$", views.serve_page, name="docs_page"),
]
