## Overview

Each component can have single "primary" HTML, CSS and JS file associated with them.

Each of these can be either defined inline, or in a separate file:

- HTML files are defined using [`Component.template`](../../reference/api.md#django_components.Component.template) or [`Component.template_file`](../../reference/api.md#django_components.Component.template_file)
- CSS files are defined using [`Component.css`](../../reference/api.md#django_components.Component.css) or [`Component.css_file`](../../reference/api.md#django_components.Component.css_file)
- JS files are defined using [`Component.js`](../../reference/api.md#django_components.Component.js) or [`Component.js_file`](../../reference/api.md#django_components.Component.js_file)

```py
@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    css_file = "calendar.css"
    js_file = "calendar.js"
```

or

```djc_py
@register("calendar")
class Calendar(Component):
    template = """
        <div class="welcome">
            Hi there!
        </div>
    """
    css = """
        .welcome {
            color: red;
        }
    """
    js = """
        console.log("Hello, world!");
    """
```

These "primary" files will have special behavior. For example, each will receive variables from the component's data methods.
Read more about each file type below:

- [HTML](#html)
- [CSS](#css)
- [JS](#js)

In addition, you can define extra "secondary" CSS / JS files using the nested [`Component.Media`](../../reference/api.md#django_components.Component.Media) class,
by setting [`Component.Media.js`](../../reference/api.md#django_components.ComponentMediaInput.js) and [`Component.Media.css`](../../reference/api.md#django_components.ComponentMediaInput.css).

Single component can have many secondary files. There is no special behavior for them.

You can use these for third-party libraries, or for shared CSS / JS files.

Read more about [Secondary JS / CSS files](secondary_js_css_files.md).

!!! warning

    You **cannot** use both inlined code **and** separate file for a single language type (HTML, CSS, JS).

    However, you can freely mix these for different languages:

    ```djc_py
    class MyTable(Component):
        template: types.django_html = """
          <div class="welcome">
            Hi there!
          </div>
        """
        js_file = "my_table.js"
        css_file = "my_table.css"
    ```

## HTML

Components use Django's template system to define their HTML.
This means that you can use [Django's template syntax](https://docs.djangoproject.com/en/5.2/ref/templates/language/) to define your HTML.

Inside the template, you can access the data returned from the [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data) method.

You can define the HTML directly in your Python code using the [`template`](../../reference/api.md#django_components.Component.template) attribute:

```djc_py
class Button(Component):
    template = """
        <button class="btn">
            {% if icon %}
                <i class="{{ icon }}"></i>
            {% endif %}
            {{ text }}
        </button>
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "text": kwargs.get("text", "Click me"),
            "icon": kwargs.get("icon", None),
        }
```

Or you can define the HTML in a separate file and reference it using [`template_file`](../../reference/api.md#django_components.Component.template_file):

```python
class Button(Component):
    template_file = "button.html"

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "text": kwargs.get("text", "Click me"),
            "icon": kwargs.get("icon", None),
        }
```

```django title="button.html"
<button class="btn">
    {% if icon %}
        <i class="{{ icon }}"></i>
    {% endif %}
    {{ text }}
</button>
```

### Dynamic templates

Each component has only a single template associated with it.

However, whether it's for A/B testing or for preserving public API
when sharing your components, sometimes you may need to render different templates
based on the input to your component.

You can use [`Component.on_render()`](../../reference/api.md#django_components.Component.on_render)
to dynamically override what template gets rendered.

By default, the component's template is rendered as-is.

```py
class Table(Component):
    def on_render(self, context: Context, template: Template | None):
        if template is not None:
            return template.render(context)
```

If you want to render a different template in its place,
we recommended you to:

1. Wrap the substitute templates as new Components
2. Then render those Components inside [`Component.on_render()`](../../reference/api.md#django_components.Component.on_render):

```py
class TableNew(Component):
    template_file = "table_new.html"

class TableOld(Component):
    template_file = "table_old.html"

class Table(Component):
    def on_render(self, context, template):
        if self.kwargs.get("feat_table_new_ui"):
            return TableNew.render(
                args=self.args,
                kwargs=self.kwargs,
                slots=self.slots,
            )
        else:
            return TableOld.render(
                args=self.args,
                kwargs=self.kwargs,
                slots=self.slots,
            )
```

!!! warning

    If you do not wrap the templates as Components,
    there is a risk that some [extensions](../advanced/extensions.md) will not work as expected.

    ```py
    new_template = Template("""
        {% load django_components %}
        <div>
            {% slot "content" %}
                Other template
            {% endslot %}
        </div>
    """)

    class Table(Component):
        def on_render(self, context, template):
            if self.kwargs.get("feat_table_new_ui"):
                return new_template.render(context)
            else:
                return template.render(context)
    ```

### Template-less components

Since you can use [`Component.on_render()`](../../reference/api.md#django_components.Component.on_render)
to render *other* components, there is no need to define a template for the component.

So even an empty component like this is valid:

```py
class MyComponent(Component):
    pass
```

These "template-less" components can be useful as base classes for other components, or as mixins.

### HTML processing

Django Components expects the rendered template to be a valid HTML. This is needed to enable features like [CSS / JS variables](html_js_css_variables.md).

Here is how the HTML is post-processed:

1. **Insert component ID**: Each root element in the rendered HTML automatically receives a `data-djc-id-cxxxxxx` attribute containing a unique component instance ID.

    ```html
    <!-- Output HTML -->
    <div class="card" data-djc-id-c1a2b3c>
        ...
    </div>
    <div class="backdrop" data-djc-id-c1a2b3c>
        ...
    </div>
    ```

2. **Insert CSS ID**: If the component defines CSS variables through [`get_css_data()`](../../reference/api.md#django_components.Component.get_css_data), the root elements also receive a `data-djc-css-xxxxxx` attribute. This attribute links the element to its specific CSS variables.

    ```html
    <!-- Output HTML -->
    <div class="card" data-djc-id-c1a2b3c data-djc-css-d4e5f6>
        <!-- Component content -->
    </div>
    ```

3. **Insert JS and CSS**: After the HTML is rendered, Django Components handles inserting JS and CSS dependencies into the page based on the [dependencies rendering strategy](rendering_components.md#dependencies-rendering) (document, fragment, or inline).

    For example, if your component contains the
    [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies)
    or
    [`{% component_css_dependencies %}`](../../reference/template_tags.md#component_css_dependencies)
    tags, or the `<head>` and `<body>` elements, the JS and CSS scripts will be inserted into the HTML.

    For more information on how JS and CSS dependencies are rendered, see [Rendering JS / CSS](../advanced/rendering_js_css.md).

## JS

The component's JS script is executed in the browser:

- It is executed AFTER the "secondary" JS files from [`Component.Media.js`](../../reference/api.md#django_components.ComponentMediaInput.js) are loaded.
- The script is only executed once, even if there are multiple instances of the component on the page.
- Component JS scripts are executed in the order how they appeared in the template / HTML (top to bottom).

You can define the JS directly in your Python code using the [`js`](../../reference/api.md#django_components.Component.js) attribute:

```djc_py
class Button(Component):
    js = """
        console.log("Hello, world!");
    """

    def get_js_data(self, args, kwargs, slots, context):
        return {
            "text": kwargs.get("text", "Click me"),
        }
```

Or you can define the JS in a separate file and reference it using [`js_file`](../../reference/api.md#django_components.Component.js_file):

```python
class Button(Component):
    js_file = "button.js"

    def get_js_data(self, args, kwargs, slots, context):
        return {
            "text": kwargs.get("text", "Click me"),
        }
```

```django title="button.js"
console.log("Hello, world!");
```

## CSS

You can define the CSS directly in your Python code using the [`css`](../../reference/api.md#django_components.Component.css) attribute:

```djc_py
class Button(Component):
    css = """
        .btn {
            width: 100px;
            color: var(--color);
        }
    """

    def get_css_data(self, args, kwargs, slots, context):
        return {
            "color": kwargs.get("color", "red"),
        }
```

Or you can define the CSS in a separate file and reference it using [`css_file`](../../reference/api.md#django_components.Component.css_file):

```python
class Button(Component):
    css_file = "button.css"

    def get_css_data(self, args, kwargs, slots, context):
        return {
            "text": kwargs.get("text", "Click me"),
        }
```

```django title="button.css"
.btn {
    color: red;
}
```

## File paths

Compared to the [secondary JS / CSS files](secondary_js_css_files.md), the definition of file paths for the main HTML / JS / CSS files is quite simple - just strings, without any lists, objects, or globs.

However, similar to the secondary JS / CSS files, you can specify the file paths [relative to the component's directory](secondary_js_css_files.md/#relative-to-component).

So if you have a directory with following files:

```
[project root]/components/calendar/
├── calendar.html
├── calendar.css
├── calendar.js
└── calendar.py
```

You can define the component like this:

```py title="[project root]/components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    css_file = "calendar.css"
    js_file = "calendar.js"
```

Assuming that
[`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
contains path `[project root]/components`, the example above is the same as writing out:

```py title="[project root]/components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar/template.html"
    css_file = "calendar/style.css"
    js_file = "calendar/script.js"
```

If the path cannot be resolved relative to the component, django-components will attempt
to resolve the path relative to the component directories, as set in
[`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
or
[`COMPONENTS.app_dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs).

Read more about [file path resolution](secondary_js_css_files.md/#relative-to-component).

## Access component definition

Component's HTML / CSS / JS is resolved and loaded lazily.

This means that, when you specify any of
[`template_file`](../../reference/api.md#django_components.Component.template_file),
[`js_file`](../../reference/api.md#django_components.Component.js_file),
[`css_file`](../../reference/api.md#django_components.Component.css_file),
or [`Media.js/css`](../../reference/api.md#django_components.Component.Media),
these file paths will be resolved only once you either:

1. Access any of the following attributes on the component:

    - [`media`](../../reference/api.md#django_components.Component.media),
     [`template`](../../reference/api.md#django_components.Component.template),
     [`template_file`](../../reference/api.md#django_components.Component.template_file),
     [`js`](../../reference/api.md#django_components.Component.js),
     [`js_file`](../../reference/api.md#django_components.Component.js_file),
     [`css`](../../reference/api.md#django_components.Component.css),
     [`css_file`](../../reference/api.md#django_components.Component.css_file)

2. Render the component.

Once the component's media files have been loaded once, they will remain in-memory
on the Component class:

- HTML from [`Component.template_file`](../../reference/api.md#django_components.Component.template_file)
  will be available under [`Component.template`](../../reference/api.md#django_components.Component.template)
- CSS from [`Component.css_file`](../../reference/api.md#django_components.Component.css_file)
  will be available under [`Component.css`](../../reference/api.md#django_components.Component.css)
- JS from [`Component.js_file`](../../reference/api.md#django_components.Component.js_file)
  will be available under [`Component.js`](../../reference/api.md#django_components.Component.js)

Thus, whether you define HTML via
[`Component.template_file`](../../reference/api.md#django_components.Component.template_file)
or [`Component.template`](../../reference/api.md#django_components.Component.template),
you can always access the HTML content under [`Component.template`](../../reference/api.md#django_components.Component.template).
And the same applies for JS and CSS.

**Example:**

```py
# When we create Calendar component, the files like `calendar/template.html`
# are not yet loaded!
@register("calendar")
class Calendar(Component):
    template_file = "calendar/template.html"
    css_file = "calendar/style.css"
    js_file = "calendar/script.js"

    class Media:
        css = "calendar/style1.css"
        js = "calendar/script2.js"

# It's only at this moment that django-components reads the files like `calendar/template.html`
print(Calendar.css)
# Output:
# .calendar {
#   width: 200px;
#   background: pink;
# }
```

!!! warning

    **Do NOT modify HTML / CSS / JS after it has been loaded**

    django-components assumes that the component's media files like `js_file` or `Media.js/css` are static.

    If you need to dynamically change these media files, consider instead defining multiple Components.

    Modifying these files AFTER the component has been loaded at best does nothing. However, this is
    an untested behavior, which may lead to unexpected errors.
