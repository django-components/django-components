Components can be defined in a single file, which is useful for small components. To do this, you can use the `template`, `js`, and `css` class attributes instead of the `template_file`, `js_file`,  and `css_file`.

For example, here's the calendar component from
the [Getting started](../../getting_started/your_first_component.md) tutorial,
defined in a single file:

```djc_py title="[project root]/components/calendar.py"
from django_components import Component, register, types

@register("calendar")
class Calendar(Component):
    def get_context_data(self, date):
        return {
            "date": date,
        }

    template: types.django_html = """
        <div class="calendar">
            Today's date is <span>{{ date }}</span>
        </div>
    """

    css: types.css = """
        .calendar {
            width: 200px;
            background: pink;
        }
        .calendar span {
            font-weight: bold;
        }
    """

    js: types.js = """
        (function(){
            if (document.querySelector(".calendar")) {
                document.querySelector(".calendar").onclick = () => {
                    alert("Clicked calendar!");
                };
            }
        })()
    """
```

This makes it easy to create small components without having to create a separate template, CSS, and JS file.

To add syntax highlighting to these snippets, head over to [Syntax highlighting](../../guides/setup/syntax_highlight.md).
