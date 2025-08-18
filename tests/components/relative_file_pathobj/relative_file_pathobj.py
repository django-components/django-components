from typing import Any, Dict

from django.templatetags.static import static
from django.utils.html import format_html, html_safe

from django_components import Component, register


# Format as mentioned in https://github.com/django-components/django-components/issues/522#issuecomment-2173577094
@html_safe
class PathObj:
    def __init__(self, static_path: str) -> None:
        self.static_path = static_path
        self.throw_on_calling_str = True

    def __str__(self):
        # This error will notify us when we've hit __str__ when we shouldn't have
        if self.throw_on_calling_str:
            raise RuntimeError("__str__ method of 'relative_file_pathobj_component' was triggered when not allow to")

        if self.static_path.endswith(".js"):
            return format_html('<script type="module" src="{}"></script>', static(self.static_path))
        return format_html('<link href="{}" rel="stylesheet">', static(self.static_path))


@register("relative_file_pathobj_component")
class RelativeFileWithPathObjComponent(Component):
    template_file = "relative_file_pathobj.html"

    class Media:
        js = PathObj("relative_file_pathobj.js")
        css = PathObj("relative_file_pathobj.css")

    def get_template_data(self, args, kwargs, slots, context) -> Dict[str, Any]:
        return {"variable": kwargs["variable"]}
