As you could have seen in [the tutorial](../../getting_started/adding_js_and_css.md), there's multiple ways how you can associate
HTML / JS / CSS with a component:

- You can set [`Component.template`](../../reference/api.md#django_components.Component.template),
  [`Component.css`](../../reference/api.md#django_components.Component.css) and
  [`Component.js`](../../reference/api.md#django_components.Component.js) to define the main HTML / CSS / JS for a component
  as inlined code.
- You can set [`Component.template_file`](../../reference/api.md#django_components.Component.template_file),
  [`Component.css_file`](../../reference/api.md#django_components.Component.css_file) and
  [`Component.js_file`](../../reference/api.md#django_components.Component.js_file) to define the main HTML / CSS / JS
  for a component in separate files.
- You can link additional CSS / JS files using
  [`Component.Media.js`](../../reference/api.md#django_components.ComponentMediaInput.js)
  and [`Component.Media.css`](../../reference/api.md#django_components.ComponentMediaInput.css).

!!! warning

    You **cannot** use both inlined code **and** separate file for a single language type:

    - You can only either set `Component.template` or `Component.template_file`
    - You can only either set `Component.css` or `Component.css_file`
    - You can only either set `Component.js` or `Component.js_file`

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

!!! note

    django-component's management of files is inspired by [Django's `Media` class](https://docs.djangoproject.com/en/5.0/topics/forms/media/).

    To be familiar with how Django handles static files, we recommend reading also:

    - [How to manage static files (e.g. images, JavaScript, CSS)](https://docs.djangoproject.com/en/5.0/howto/static-files/)

## Defining file paths relative to component

As seen in the [getting started example](../../getting_started/your_first_component.md), to associate HTML / JS / CSS
files with a component, you can set them as
[`Component.template_file`](../../reference/api.md#django_components.Component.template_file),
[`Component.js_file`](../../reference/api.md#django_components.Component.js_file)
and
[`Component.css_file`](../../reference/api.md#django_components.Component.css_file) respectively:

```py title="[project root]/components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "template.html"
    css_file = "style.css"
    js_file = "script.js"
```

In the example above, we defined the files relative to the directory where the component file is defined.

Alternatively, you can specify the file paths relative to the directories set in
[`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
or
[`COMPONENTS.app_dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs).

If you specify the paths relative to component's directory, django-componenents does the conversion automatically
for you.

Thus, assuming that
[`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
contains path `[project root]/components`, the example above is the same as writing:

```py title="[project root]/components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar/template.html"
    css_file = "calendar/style.css"
    js_file = "calendar/script.js"
```

!!! important

    **File path resolution in-depth**

    At component class creation, django-components checks all file paths defined on the component (e.g. `Component.template_file`).

    For each file path, it checks if the file path is relative to the component's directory.
    And such file exists, the component's file path is re-written to be defined relative to a first matching directory
    in [`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
    or
    [`COMPONENTS.app_dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs).

    **Example:**

    ```py title="[root]/components/mytable/mytable.py"
    class MyTable(Component):
        template_file = "mytable.html"
    ```

    1. Component `MyTable` is defined in file `[root]/components/mytable/mytable.py`.
    2. The component's directory is thus `[root]/components/mytable/`.
    3. Because `MyTable.template_file` is `mytable.html`, django-components tries to
        resolve it as `[root]/components/mytable/mytable.html`.
    4. django-components checks the filesystem. If there's no such file, nothing happens.
    5. If there IS such file, django-components tries to rewrite the path.
    6. django-components searches `COMPONENTS.dirs` and `COMPONENTS.app_dirs` for a first
        directory that contains `[root]/components/mytable/mytable.html`.
    7. It comes across `[root]/components/`, which DOES contain the path to `mytable.html`.
    8. Thus, it rewrites `template_file` from `mytable.html` to `mytable/mytable.html`.

    NOTE: In case of ambiguity, the preference goes to resolving the files relative to the component's directory.

## Defining additional JS and CSS files

Each component can have only a single template, and single main JS and CSS. However, you can define additional JS or CSS
using the nested [`Component.Media` class](../../../reference/api#django_components.Component.Media).

This `Media` class behaves similarly to
[Django's Media class](https://docs.djangoproject.com/en/5.1/topics/forms/media/#assets-as-a-static-definition):

- Paths are generally handled as static file paths, and resolved URLs are rendered to HTML with
  `media_class.render_js()` or `media_class.render_css()`.
- A path that starts with `http`, `https`, or `/` is considered a URL, skipping the static file resolution.
  This path is still rendered to HTML with `media_class.render_js()` or `media_class.render_css()`.
- A [`SafeString`](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.safestring.SafeString),
  or a function (with `__html__` method) is considered an already-formatted HTML tag, skipping both static file
  resolution and rendering with `media_class.render_js()` or `media_class.render_css()`.
- You can set [`extend`](../../../reference/api#django_components.ComponentMediaInput.extend) to configure
    whether to inherit JS / CSS from parent components. See
    [Controlling Media Inheritance](../../fundamentals/defining_js_css_html_files/#controlling-media-inheritance).

However, there's a few differences from Django's Media class:

1. Our Media class accepts various formats for the JS and CSS files: either a single file, a list,
   or (CSS-only) a dictonary (See [`ComponentMediaInput`](../../../reference/api#django_components.ComponentMediaInput)).
2. Individual JS / CSS files can be any of `str`, `bytes`, `Path`,
   [`SafeString`](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.safestring.SafeString), or a function
   (See [`ComponentMediaInputPath`](../../../reference/api#django_components.ComponentMediaInputPath)).

```py
class MyTable(Component):
    class Media:
        js = [
            "path/to/script.js",
            "https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js",  # AlpineJS
        ]
        css = {
            "all": [
                "path/to/style.css",
                "https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css",  # TailwindCSS
            ],
            "print": ["path/to/style2.css"],
        }
```

## Configuring CSS Media Types

You can define which stylesheets will be associated with which
[CSS Media types](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_media_queries/Using_media_queries#targeting_media_types). You do so by defining CSS files as a dictionary.

See the corresponding [Django Documentation](https://docs.djangoproject.com/en/5.0/topics/forms/media/#css).

Again, you can set either a single file or a list of files per media type:

```py
class MyComponent(Component):
    class Media:
        css = {
            "all": "path/to/style1.css",
            "print": ["path/to/style2.css", "path/to/style3.css"],
        }
```

!!! note

    When you define CSS as a string or a list, the `all` media type is implied.

    So these two examples are the same:

    ```py
    class MyComponent(Component):
        class Media:
            css = "path/to/style1.css"
    ```

    ```py
    class MyComponent(Component):
        class Media:
            css = {
                "all": ["path/to/style1.css"],
            }
    ```

## Supported types for file paths

File paths can be any of:

- `str`
- `bytes`
- `PathLike` (`__fspath__` method)
- `SafeData` (`__html__` method)
- `Callable` that returns any of the above, evaluated at class creation (`__new__`)

See [`ComponentMediaInputPath`](../../../reference/api#django_components.ComponentMediaInputPath).

```py
from pathlib import Path

from django.utils.safestring import mark_safe

class SimpleComponent(Component):
    class Media:
        css = [
            mark_safe('<link href="/static/calendar/style1.css" rel="stylesheet" />'),
            Path("calendar/style1.css"),
            "calendar/style2.css",
            b"calendar/style3.css",
            lambda: "calendar/style4.css",
        ]
        js = [
            mark_safe('<script src="/static/calendar/script1.js"></script>'),
            Path("calendar/script1.js"),
            "calendar/script2.js",
            b"calendar/script3.js",
            lambda: "calendar/script4.js",
        ]
```

## Paths as objects

In the example [above](#supported-types-for-file-paths), you can see that when we used Django's
[`mark_safe()`](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.safestring.mark_safe)
to mark a string as a [`SafeString`](https://docs.djangoproject.com/en/5.1/ref/utils/#django.utils.safestring.SafeString),
we had to define the full `<script>`/`<link>` tag.

This is an extension of Django's [Paths as objects](https://docs.djangoproject.com/en/5.0/topics/forms/media/#paths-as-objects)
feature, where "safe" strings are taken as is, and accessed only at render time.

Because of that, the paths defined as "safe" strings are NEVER resolved, neither relative to component's directory,
nor relative to [`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs).

"Safe" strings can be used to lazily resolve a path, or to customize the `<script>` or `<link>` tag for individual paths:

In the example below, we make use of "safe" strings to add `type="module"` to the script tag that will fetch `calendar/script2.js`.
In this case, we implemented a "safe" string by defining a `__html__` method.

```py
class ModuleJsPath:
    def __init__(self, static_path: str) -> None:
        self.static_path = static_path

    def __html__(self):
        full_path = static(self.static_path)
        return format_html(
            f'<script type="module" src="{full_path}"></script>'
        )

@register("calendar")
class Calendar(Component):
    template_file = "calendar/template.html"

    def get_context_data(self, date):
        return {
            "date": date,
        }

    class Media:
        css = "calendar/style1.css"
        js = [
            # <script> tag constructed by Media class
            "calendar/script1.js",
            # Custom <script> tag
            ModuleJsPath("calendar/script2.js"),
        ]
```

## Customize how paths are rendered into HTML tags

Sometimes you may need to change how all CSS `<link>` or JS `<script>` tags are rendered for a given component. You can achieve this by providing your own subclass of [Django's `Media` class](https://docs.djangoproject.com/en/5.0/topics/forms/media) to component's `media_class` attribute.

Normally, the JS and CSS paths are passed to `Media` class, which decides how the paths are resolved and how the `<link>` and `<script>` tags are constructed.

To change how the tags are constructed, you can override the [`Media.render_js` and `Media.render_css` methods](https://github.com/django/django/blob/fa7848146738a9fe1d415ee4808664e54739eeb7/django/forms/widgets.py#L102):

```py
from django.forms.widgets import Media
from django_components import Component, register

class MyMedia(Media):
    # Same as original Media.render_js, except
    # the `<script>` tag has also `type="module"`
    def render_js(self):
        tags = []
        for path in self._js:
            if hasattr(path, "__html__"):
                tag = path.__html__()
            else:
                tag = format_html(
                    '<script type="module" src="{}"></script>',
                    self.absolute_path(path)
                )
        return tags

@register("calendar")
class Calendar(Component):
    template_file = "calendar/template.html"
    css_file = "calendar/style.css"
    js_file = "calendar/script.js"

    class Media:
        css = "calendar/style1.css"
        js = "calendar/script2.js"

    # Override the behavior of Media class
    media_class = MyMedia
```

## Accessing component's HTML / JS / CSS

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

## Accessing component's Media files

To access the files that you defined under [`Component.Media`](../../../reference/api#django_components.Component.Media),
use [`Component.media`](../../reference/api.md#django_components.Component.media) (lowercase).
This is consistent behavior with
[Django's Media class](https://docs.djangoproject.com/en/5.1/topics/forms/media/#assets-as-a-static-definition).

```py
class MyComponent(Component):
    class Media:
        js = "path/to/script.js"
        css = "path/to/style.css"

print(MyComponent.media)
# Output:
# <script src="/static/path/to/script.js"></script>
# <link href="/static/path/to/style.css" media="all" rel="stylesheet">
```

### `Component.Media` vs `Component.media`

When working with component media files, there are a few important concepts to understand:

- `Component.Media`

    - Is the "raw" media definition, or the input, which holds only the component's **own** media definition
    - This class is NOT instantiated, it merely holds the JS / CSS files.

- `Component.media`
    - Returns all resolved media files, **including** those inherited from parent components
    - Is an instance of [`Component.media_class`](../../reference/api.md#django_components.Component.media_class)

```python
class ParentComponent(Component):
    class Media:
        js = ["parent.js"]

class ChildComponent(ParentComponent):
    class Media:
        js = ["child.js"]

# Access only this component's media
print(ChildComponent.Media.js)  # ["child.js"]

# Access all inherited media
print(ChildComponent.media._js)  # ["parent.js", "child.js"]
```

!!! note

    You should **not** manually modify `Component.media` or `Component.Media` after the component has been resolved, as this may lead to unexpected behavior.

If you want to modify the class that is instantiated for [`Component.media`](../../reference/api.md#django_components.Component.media),
you can configure [`Component.media_class`](../../reference/api.md#django_components.Component.media_class)
([See example](#customize-how-paths-are-rendered-into-html-tags)).

## Controlling Media Inheritance

By default, the media files are inherited from the parent component.

```python
class ParentComponent(Component):
    class Media:
        js = ["parent.js"]

class MyComponent(ParentComponent):
    class Media:
        js = ["script.js"]

print(MyComponent.media._js)  # ["parent.js", "script.js"]
```

You can set the component NOT to inherit from the parent component by setting the [`extend`](../../reference/api.md#django_components.ComponentMediaInput.extend) attribute to `False`:

```python
class ParentComponent(Component):
    class Media:
        js = ["parent.js"]

class MyComponent(ParentComponent):
    class Media:
        extend = False  # Don't inherit parent media
        js = ["script.js"]

print(MyComponent.media._js)  # ["script.js"]
```

Alternatively, you can specify which components to inherit from. In such case, the media files are inherited ONLY from the specified components, and NOT from the original parent components:

```python
class ParentComponent(Component):
    class Media:
        js = ["parent.js"]

class MyComponent(ParentComponent):
    class Media:
        # Only inherit from these, ignoring the files from the parent
        extend = [OtherComponent1, OtherComponent2]

        js = ["script.js"]

print(MyComponent.media._js)  # ["script.js", "other1.js", "other2.js"]
```

!!! info

    The `extend` behaves consistently with
    [Django's Media class](https://docs.djangoproject.com/en/5.1/topics/forms/media/#extend),
    with one exception:

    - When you set `extend` to a list, the list is expected to contain Component classes (or other classes that have a nested `Media` class).
