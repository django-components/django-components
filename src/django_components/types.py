"""Helper types for IDEs."""

from typing_extensions import Annotated

css = Annotated[str, "css"]
django_html = Annotated[str, "django_html"]
js = Annotated[str, "js"]
