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

    Use `CssScope` extension to automatically scope your CSS, so you won't have to worry
    about CSS class clashes.

This CSS will be inserted into the page as an inlined `<style>` tag, at the position defined by
[`{% component_css_dependencies %}`](../reference/template_tags.md#component_css_dependencies),
or at the end of the inside the `<head>` tag
(See [Default JS / CSS locations](../concepts/advanced/rendering_js_css.md#default-js-css-locations)).

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
[`{% component_js_dependencies %}`](../reference/template_tags.md#component_js_dependencies),
or at the end of the inside the `<body>` tag (See [Default JS / CSS locations](../concepts/advanced/rendering_js_css.md#default-js-css-locations)).

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

To link JS and CSS defined in other files, use [`js_file`](../reference/api.md#django_components.Component.js_file)
and [`css_file`](../reference/api.md#django_components.Component.css_file) attributes:

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
    [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
    and/or [`COMPONENTS.app_dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
    (e.g. `[your apps]/components` dir and `[project root]/components`)
    3. Relative to any of the directories defined by `STATICFILES_DIRS`.

!!! info title="Special role of `css` and `js`"

    The "primary" JS and CSS you that specify via `js/css` and `js_file/css_file` have special role in many of django-components' features:

    - CSS variables from Python are available
    - JS variables from Python are available
    - CSS scoping [a la Vue](https://vuejs.org/api/sfc-css-features.html#scoped-css)

    This is not true for JS and CSS defined in `Media.js/css`, where the linked JS / CSS are rendered as is.

### 5. CSS variables

You can pass dynamic data from your Python component to your CSS using CSS variables.
This is done using the [`get_css_data()`](../reference/api.md#django_components.Component.get_css_data) method.

The dictionary returned from `get_css_data()` will be converted to CSS variables where:

- Keys become CSS variable names (prefixed with `--`)
- Values are serialized to strings

Let's update our calendar component to support different themes:

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"

    class Kwargs:
        date: str = "1970-01-01"
        theme: str = "light"

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "date": kwargs.date,
        }

    # New!
    def get_css_data(self, args, kwargs: Kwargs, slots, context):
        themes = {
            "light": {
                "bg_color": "#ffffff",
                "text_color": "#333333",
            },
            "dark": {
                "bg_color": "#242424",
                "text_color": "#f1f1f1",
            },
        }
        return themes.get(kwargs.theme, themes["light"])
```

Now update your CSS to use these variables:

```css title="[project root]/components/calendar/calendar.css"
.calendar {
  width: 200px;
  background-color: var(--bg_color);
  color: var(--text_color);
}
.calendar span {
  font-weight: bold;
}
```

When you render the component, django-components will automatically:

1. Call `get_css_data()` to get the CSS variables
2. Generate a stylesheet with those variables scoped to this component instance
3. Link the stylesheet to the component

```django
{% component "calendar" date="2024-11-06" theme="dark" %}
{% endcomponent %}
```

This will render something like:

```html
<div class="calendar" data-djc-css-a1b2c3>
  Today's date is <span>2024-11-06</span>
</div>
```

With a corresponding stylesheet:

```css
[data-djc-css-a1b2c3] {
  --bg_color: #242424;
  --text_color: #f1f1f1;
}
```

[Learn more](../concepts/fundamentals/html_js_css_variables.md#css-variables) about CSS variables.

---

Next, [let's add third-party dependencies ➡️](adding_dependencies.md).
