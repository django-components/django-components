Next we will add CSS and JavaScript to our template.

!!! info

    In django-components, using JS and CSS is as simple as defining them on the Component class.
    You don't have to insert the `<script>` and `<link>` tags into the HTML manually.

    Behind the scenes, django-components keeps track of which components use which JS and CSS
    files. Thus, when a component is rendered on the page, the page will contain only the JS
    and CSS used by the components, and nothing more!

### 1. Update project structure

Start by creating empty `calendar.js` and `calendar.css` files:

```
sampleproject/
├── calendarapp/
├── components/
│   └── calendar/
│       ├── calendar.py
│       ├── calendar.js       🆕
│       ├── calendar.css      🆕
│       └── calendar.html
├── sampleproject/
├── manage.py
└── requirements.txt
```

### 2. Write CSS

Inside `calendar.css`, write:

```css title="[project root]/components/calendar/calendar.css"
.calendar {
  width: 200px;
  background: pink;
}
.calendar span {
  font-weight: bold;
}
```

Be sure to prefix your rules with unique CSS class like `calendar`, so the CSS doesn't clash with other rules.

<!-- TODO: UPDATE AFTER SCOPED CSS ADDED -->

!!! note

    Soon, django-components will automatically scope your CSS by default, so you won't have to worry
    about CSS class clashes.

This CSS will be inserted into the page as an inlined `<style>` tag, at the position defined by
[`{% component_css_dependencies %}`](../../reference/template_tags#component_css_dependencies),
or at the end of the inside the `<head>` tag
(See [Default JS / CSS locations](../../concepts/advanced/rendering_js_css#default-js-css-locations)).

So in your HTML, you may see something like this:

```html
<html>
  <head>
    ...
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
  </body>
</html>
```

### 3. Write JS

Next we write a JavaScript file that specifies how to interact with this component.

You are free to use any javascript framework you want.

```js title="[project root]/components/calendar/calendar.js"
(function () {
  document.querySelector(".calendar").onclick = () => {
    alert("Clicked calendar!");
  };
})();
```

A good way to make sure the JS of this component doesn't clash with other components is to define all JS code inside
an [anonymous self-invoking function](https://developer.mozilla.org/en-US/docs/Glossary/IIFE) (`(() => { ... })()`).
This makes all variables defined only be defined inside this component and not affect other components.

<!-- TODO: UPDATE AFTER FUNCTIONS WRAPPED -->

!!! note

    Soon, django-components will automatically wrap your JS in a self-invoking function by default
    (except for JS defined with `<script type="module">`).

Similarly to CSS, JS will be inserted into the page as an inlined `<script>` tag, at the position defined by
[`{% component_js_dependencies %}`](../../reference/template_tags#component_js_dependencies),
or at the end of the inside the `<body>` tag (See [Default JS / CSS locations](../../concepts/advanced/rendering_js_css#default-js-css-locations)).

So in your HTML, you may see something like this:

```html
<html>
  <head>
    ...
  </head>
  <body>
    ...
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

#### Rules of JS execution

1. **JS is executed in the order in which the components are found in the HTML**

    By default, the JS is inserted as a **synchronous** script (`<script> ... </script>`)

    So if you define multiple components on the same page, their JS will be
    executed in the order in which the components are found in the HTML.

    So if we have a template like so:

    ```htmldjango
    <html>
      <head>
        ...
      </head>
      <body>
        {% component "calendar" / %}
        {% component "table" / %}
      </body>
    </html>
    ```

    Then the JS file of the component `calendar` will be executed first, and the JS file
    of component `table` will be executed second.

2. **JS will be executed only once, even if there is multiple instances of the same component**

    In this case, the JS of `calendar` will STILL execute first (because it was found first),
    and will STILL execute only once, even though it's present twice:

    ```htmldjango
    <html>
      <head>
        ...
      </head>
      <body>
        {% component "calendar" / %}
        {% component "table" / %}
        {% component "calendar" / %}
      </body>
    </html>
    ```

### 4. Link JS and CSS to a component

Finally, we return to our Python component in `calendar.py` to tie this together.

To link JS and CSS defined in other files, use [`js_file`](../../reference/api#django_components.Component.js_file)
and [`css_file`](../../reference/api#django_components.Component.css_file) attributes:

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"   # <--- new
    css_file = "calendar.css"   # <--- new

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": "1970-01-01",
        }
```

And that's it! If you were to embed this component in an HTML, django-components will
automatically embed the associated JS and CSS.

!!! note

    Similarly to the template file, the JS and CSS file paths can be either:

    1. Relative to the Python component file (as seen above),
    2. Relative to any of the component directories as defined by
    [`COMPONENTS.dirs`](../../reference/settings#django_components.app_settings.ComponentsSettings.dirs)
    and/or [`COMPONENTS.app_dirs`](../../reference/settings#django_components.app_settings.ComponentsSettings.app_dirs)
    (e.g. `[your apps]/components` dir and `[project root]/components`)
    3. Relative to any of the directories defined by `STATICFILES_DIRS`.

<!-- TODO: UPDATE AFTER AT LEAST ONE IMPLEMENTED
!!! info

    Special role of `css` and `js`:

    The "primary" JS and CSS you that specify via `js/css` and `js_file/css_file` have special role in many of django-components'
    features:
    - CSS scoping [a la Vue](https://vuejs.org/api/sfc-css-features.html#scoped-css)
    - CSS variables from Python are available
    - JS variables from Python are available
    - JS can pass a callback to special JS method `$onLoad()`, which will be called every time
      a component is rendered on the page.

    This is not true for JS and CSS defined in `Media.js/css`, where the linked JS / CSS are rendered as is.
-->

### 5. Link additional JS and CSS to a component

Your components may depend on third-party packages or styling, or other shared logic.
To load these additional dependencies, you can use a nested [`Media` class](../../reference/api#django_components.Component.Media).

This `Media` class behaves similarly to [Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#assets-as-a-static-definition),
with a few differences:

1. Our Media class accepts various formats for the JS and CSS files: either a single file, a list, or (CSS-only) a dictonary (see below).
2. Individual JS / CSS files can be any of `str`, `bytes`, `Path`, [`SafeString`](https://dev.to/doridoro/django-safestring-afj), or a function.
3. Individual JS / CSS files can be glob patterns, e.g. `*.js` or `styles/**/*.css`.
4. If you set [`Media.extend`](../../reference/api/#django_components.ComponentMediaInput.extend) to a list,
   it should be a list of [`Component`](../../reference/api/#django_components.Component) classes.

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
    [`COMPONENTS.dirs`](../../reference/settings#django_components.app_settings.ComponentsSettings.dirs)
    and/or [`COMPONENTS.app_dirs`](../../reference/settings#django_components.app_settings.ComponentsSettings.app_dirs)
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
