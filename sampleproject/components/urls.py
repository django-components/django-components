from django.urls import path

from components.calendar.calendar import Calendar, CalendarRelative
from components.fragment import FragAlpine, FragJs, FragmentBaseAlpine, FragmentBaseHtmx, FragmentBaseJs
from components.greeting import Greeting
from components.nested.calendar.calendar import CalendarNested
from components.recursive import Recursive

urlpatterns = [
    path("greeting/", Greeting.as_view(), name="greeting"),
    path("calendar/", Calendar.as_view(), name="calendar"),
    path("calendar-relative/", CalendarRelative.as_view(), name="calendar-relative"),
    path("calendar-nested/", CalendarNested.as_view(), name="calendar-nested"),
    path("recursive/", Recursive.as_view(), name="recursive"),
    path("fragment/base/alpine", FragmentBaseAlpine.as_view()),
    path("fragment/base/htmx", FragmentBaseHtmx.as_view()),
    path("fragment/base/js", FragmentBaseJs.as_view()),
    path("fragment/frag/alpine", FragAlpine.as_view()),
    path("fragment/frag/js", FragJs.as_view()),
]
