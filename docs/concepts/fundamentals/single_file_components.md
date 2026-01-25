Components can be defined in a single file, inlining the HTML, JS and CSS within the Python code.

## Writing single file components

To do this, you can use the
[`template`](../../reference/api.md#django_components.Component.template),
[`js`](../../reference/api.md#django_components.Component.js),
and [`css`](../../reference/api.md#django_components.Component.css)
class attributes instead of the
[`template_file`](../../reference/api.md#django_components.Component.template_file),
[`js_file`](../../reference/api.md#django_components.Component.js_file),
and [`css_file`](../../reference/api.md#django_components.Component.css_file).

For example, here's the calendar component from
the [Getting started](../../getting_started/your_first_component.md) tutorial:

```py title="calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"
```

And here is the same component, rewritten in a single file:

```djc_py title="[project root]/components/calendar.py"
from django_components import Component, register, types

@register("calendar")
class Calendar(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs["date"],
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

You can mix and match, so you can have a component with inlined HTML,
while the JS and CSS are in separate files:

```djc_py title="[project root]/components/calendar.py"
from django_components import Component, register, types

@register("calendar")
class Calendar(Component):
    js_file = "calendar.js"
    css_file = "calendar.css"

    template: types.django_html = """
        <div class="calendar">
            Today's date is <span>{{ date }}</span>
        </div>
    """
```

## Syntax highlighting

If you "inline" the HTML, JS and CSS code into the Python class, you should set up
syntax highlighting to let your code editor know that the inlined code is HTML, JS and CSS.

In the examples above, we've annotated the
[`template`](../../reference/api.md#django_components.Component.template),
[`js`](../../reference/api.md#django_components.Component.js),
and [`css`](../../reference/api.md#django_components.Component.css)
attributes with
the `types.django_html`, `types.js` and `types.css` types. These are used for syntax highlighting in VSCode.

!!! warning

    Autocompletion / intellisense does not work in the inlined code.

    Help us add support for intellisense in the inlined code! Start a conversation in the
    [GitHub Discussions](https://github.com/django-components/django-components/discussions).

### VSCode

1. First install [Python Inline Source Syntax Highlighting](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) extension, it will give you syntax highlighting for the template, CSS, and JS.

2. Next, in your component, set typings of
[`Component.template`](../../reference/api.md#django_components.Component.template),
[`Component.js`](../../reference/api.md#django_components.Component.js),
[`Component.css`](../../reference/api.md#django_components.Component.css)
to `types.django_html`, `types.css`, and `types.js` respectively. The extension will recognize these and will activate syntax highlighting.

```djc_py title="[project root]/components/calendar.py"
from django_components import Component, register, types

@register("calendar")
class Calendar(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs["date"],
        }

    template: types.django_html = """
        <div class="calendar-component">
            Today's date is <span>{{ date }}</span>
        </div>
    """

    css: types.css = """
        .calendar-component {
            width: 200px;
            background: pink;
        }
        .calendar-component span {
            font-weight: bold;
        }
    """

    js: types.js = """
        (function(){
            if (document.querySelector(".calendar-component")) {
                document.querySelector(".calendar-component").onclick = function(){ alert("Clicked calendar!"); };
            }
        })()
    """
```

### Pycharm (or other Jetbrains IDEs)

With PyCharm (or any other editor from Jetbrains), you don't need to use `types.django_html`, `types.css`, `types.js` since Pycharm uses [language injections](https://www.jetbrains.com/help/pycharm/using-language-injections.html).

You only need to write the comments `# language=<lang>` above the variables.

```djc_py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs["date"],
        }

    # language=HTML
    template= """
        <div class="calendar-component">
            Today's date is <span>{{ date }}</span>
        </div>
    """

    # language=CSS
    css = """
        .calendar-component {
            width: 200px;
            background: pink;
        }
        .calendar-component span {
            font-weight: bold;
        }
    """

    # language=JS
    js = """
        (function(){
            if (document.querySelector(".calendar-component")) {
                document.querySelector(".calendar-component").onclick = function(){ alert("Clicked calendar!"); };
            }
        })()
    """
```

### Markdown code blocks with Pygments

[Pygments](https://pygments.org/) is a syntax highlighting library written in Python. It's also what's used by this documentation site ([mkdocs-material](https://squidfunk.github.io/mkdocs-material/)) to highlight code blocks.

To write code blocks with syntax highlighting, you need to install the [`pygments-djc`](https://pypi.org/project/pygments-djc/) package.

```bash
pip install pygments-djc
```

And then initialize it by importing `pygments_djc` somewhere in your project:

```python
import pygments_djc
```

Now you can use the `djc_py` code block to write code blocks with syntax highlighting for components.

```txt
\```djc_py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template = """
        <div class="calendar-component">
            Today's date is <span>{{ date }}</span>
        </div>
    """

    css = """
        .calendar-component {
            width: 200px;
            background: pink;
        }
        .calendar-component span {
            font-weight: bold;
        }
    """
\```
```

Will be rendered as below. Notice that the CSS and HTML are highlighted correctly:

```djc_py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template= """
        <div class="calendar-component">
            Today's date is <span>{{ date }}</span>
        </div>
    """

    css = """
        .calendar-component {
            width: 200px;
            background: pink;
        }
        .calendar-component span {
            font-weight: bold;
        }
    """
```
