Next we will add third-party JavaScript and CSS dependencies to our component.

Your components may depend on third-party packages or styling, or other shared logic.
To load these additional dependencies, you can use a nested [`Media` class](../reference/api.md#django_components.Component.Media).

This `Media` class behaves similarly to [Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#assets-as-a-static-definition),
with a few differences:

1. Our Media class accepts various formats for the JS and CSS files: either a single file, a list, or (CSS-only) a dictonary (see below).
2. Individual JS / CSS files can be any of `str`, `bytes`, `Path`, [`SafeString`](https://dev.to/doridoro/django-safestring-afj), [`Script`](../reference/api.md#django_components.Script), [`Style`](../reference/api.md#django_components.Style), or a function.
3. Individual JS / CSS files can be glob patterns, e.g. `*.js` or `styles/**/*.css`.
4. If you set [`Media.extend`](../reference/api.md#django_components.ComponentMediaInput.extend) to a list,
   it should be a list of [`Component`](../reference/api.md#django_components.Component) classes.

[Learn more](../concepts/fundamentals/secondary_js_css_files.md) about using Media.

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"

    class Media:   # <--- new
        js = [
            "path/to/shared.js",
            "path/to/*.js",  # Or as a glob
            "https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js",  # AlpineJS
        ]
        css = [
            "path/to/shared.css",
            "path/to/*.css",  # Or as a glob
            "https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css",  # Tailwind
        ]

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": "1970-01-01",
        }
```

!!! note

    Same as with the "primary" JS and CSS, the file paths files can be either:

    1. Relative to the Python component file (as seen above),
    2. Relative to any of the component directories as defined by
    [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
    and/or [`COMPONENTS.app_dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
    (e.g. `[your apps]/components` dir and `[project root]/components`)

!!! info

    The `Media` nested class is shaped based on [Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/).

    As such, django-components allows multiple formats to define the nested Media class:

    ```py
    # Single files
    class Media:
        js = "calendar.js"
        css = "calendar.css"

    # Lists of files
    class Media:
        js = ["calendar.js", "calendar2.js"]
        css = ["calendar.css", "calendar2.css"]

    # Dictionary of media types for CSS
    class Media:
        js = ["calendar.js", "calendar2.js"]
        css = {
          "all": ["calendar.css", "calendar2.css"],
        }
    ```

    If you define a list of JS files, they will be executed one-by-one, left-to-right.

#### Rules of execution of scripts in `Media.js`

The scripts defined in `Media.js` still follow the rules outlined above:

1. JS is executed in the order in which the components are found in the HTML.
2. JS will be executed only once, even if there is multiple instances of the same component.

Additionally to `Media.js` applies that:

1. JS in `Media.js` is executed **before** the component's primary JS.
2. JS in `Media.js` is executed **in the same order** as it was defined.
3. If there is multiple components that specify the same JS path or URL in `Media.js`,
   this JS will be still loaded and executed only once.

Putting all of this together, our `Calendar` component above would render HTML like so:

```html
<html>
  <head>
    ...
    <!-- CSS from Media.css -->
    <link href="/static/path/to/shared.css" media="all" rel="stylesheet" />
    <link
      href="https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css"
      media="all"
      rel="stylesheet"
    />
    <!-- CSS from Component.css_file -->
    <style>
      .calendar {
        width: 200px;
        background: pink;
      }
      .calendar span {
        font-weight: bold;
      }
    </style>
  </head>
  <body>
    ...
    <!-- JS from Media.js -->
    <script src="/static/path/to/shared.js"></script>
    <script src="https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js"></script>
    <!-- JS from Component.js_file -->
    <script>
      (function () {
        document.querySelector(".calendar").onclick = () => {
          alert("Clicked calendar!");
        };
      })();
    </script>
  </body>
</html>
```

---

Now that we have a fully-defined component, [next let's use it in a Django template ➡️](./components_in_templates.md).
