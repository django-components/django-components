from typing import NamedTuple

from django_components import Component, register


@register("calendar")
class Calendar(Component):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    #
    # `template_file` can be relative to dir where `calendar.py` is, or relative to COMPONENTS.dirs
    template_file = "calendar/calendar.html"

    css_file = "calendar/calendar.css"
    js_file = "calendar/calendar.js"

    # This component takes one parameter, a date string to show in the template
    class Kwargs(NamedTuple):
        date: str

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "date": kwargs.date,
        }

    class View:
        def get(self, request, *args, **kwargs):
            return Calendar.render_to_response(
                request=request,
                kwargs={
                    "date": request.GET.get("date", ""),
                },
                deps_strategy="append",
            )


@register("calendar_relative")
class CalendarRelative(Component):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    #
    # `template_file` can be relative to dir where `calendar.py` is, or relative to COMPONENTS.dirs
    template_file = "calendar.html"

    css_file = "calendar.css"
    js_file = "calendar.js"

    # This component takes one parameter, a date string to show in the template
    class Kwargs(NamedTuple):
        date: str

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "date": kwargs.date,
        }

    class View:
        def get(self, request, *args, **kwargs):
            return CalendarRelative.render_to_response(
                request=request,
                kwargs={
                    "date": request.GET.get("date", ""),
                },
                deps_strategy="append",
            )
