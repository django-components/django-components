from django.urls import path

from calendarapp.views import calendar

urlpatterns = [
    path("", calendar, name="calendar"),
]
