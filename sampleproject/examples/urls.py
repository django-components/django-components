from django.urls import path

from examples.pages.form import FormPage
from examples.pages.tabs import TabsPage

urlpatterns = [
    path("examples/tabs", TabsPage.as_view(), name="tabs"),
    path("examples/form", FormPage.as_view(), name="form"),
]
