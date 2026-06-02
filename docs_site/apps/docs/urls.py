from django.urls import re_path

from . import views

# Catch-all: any path not matched earlier resolves to a content markdown page.
# Must be included last in the project urlconf so explicit routes take precedence.
urlpatterns = [
    re_path(r"^(?P<url_path>.*)$", views.serve_page, name="docs_page"),
]
