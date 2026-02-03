## Overview

Each component can define extra or "secondary" CSS / JS files using the nested [`Component.Media`](../../reference/api.md#django_components.Component.Media) class,
by setting [`Component.Media.js`](../../reference/api.md#django_components.ComponentMediaInput.js) and [`Component.Media.css`](../../reference/api.md#django_components.ComponentMediaInput.css).

The [main HTML / JS / CSS files](html_js_css_files.md) are limited to 1 per component. This is not the case for the secondary files,
where components can have many of them.

There is also no special behavior or post-processing for these secondary files, they are loaded as is.

You can use these for third-party libraries, or for shared CSS / JS files.

To modify how JS/CSS is rendered into `<script>`, `<style>`, or `<link>` tags (e.g. add attributes,
reorder, or inject scripts), see [Modifying JS / CSS scripts](../advanced/rendering_js_css.md#modifying-js-css-scripts).

These must be set as paths, URLs, or [custom objects](#paths-as-objects).

```py
@register("calendar")
class Calendar(Component):
    class Media:
        js = [
            "https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js",
            "calendar/script.js",
        ]
        css = [
            "https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css",
            "calendar/style.css",
        ]
```

!!! note

    django-component's management of files is inspired by [Django's `Media` class](https://docs.djangoproject.com/en/5.2/topics/forms/media/).

    To be familiar with how Django handles static files, we recommend reading also:

    - [How to manage static files (e.g. images, JavaScript, CSS)](https://docs.djangoproject.com/en/5.2/howto/static-files/)

## `Media` class

<!-- TODO: This section deserves to be expanded with more examples,
  so it's easier to follow. Right now it assumes that the read
  is familiar with Django's Media class, as we describe our Media class
  in constrast to it.

  Instead we should go over all features / behaviours of the `Media` class.

  We should also make `Media` class into a separate extension,
  and then have a separate page on "Secondary JS / CSS files".
 -->

Use the `Media` class to define secondary JS / CSS files for a component.

This `Media` class behaves similarly to
[Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#assets-as-a-static-definition):

- **Static paths** - Paths are handled as static file paths, and are resolved to URLs with Django's
  [`{% static %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#static) template tag.
- **URLs** - A path that starts with `http`, `https`, or `/` is considered a URL. URLs are NOT resolved with [`{% static %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#static).
- **HTML tags** - Both static paths and URLs are rendered to `<script>` and `<link>` HTML tags with
  `media_class.render_js()` and `media_class.render_css()`.
- **Bypass formatting** - A [`SafeString`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.SafeString),
  or a function (with `__html__` method) is considered an already-formatted HTML tag, skipping both static file
  resolution and rendering with `media_class.render_js()` or `media_class.render_css()`.
- **Inheritance** - You can set [`extend`](../../reference/api.md#django_components.ComponentMediaInput.extend) to configure
  whether to inherit JS / CSS from parent components. See [Media inheritance](#media-inheritance).

However, there's a few differences from Django's Media class:

1. Our Media class accepts various formats for the JS and CSS files: either a single file, a list,
   or (CSS-only) a dictonary (See [`ComponentMediaInput`](../../reference/api.md#django_components.ComponentMediaInput)).
2. Individual JS / CSS files can be any of `str`, `bytes`, `Path`,
   [`SafeString`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.SafeString), or a function
   (See [`ComponentMediaInputPath`](../../reference/api.md#django_components.ComponentMediaInputPath)).
3. Individual JS / CSS files can be glob patterns, e.g. `*.js` or `styles/**/*.css`.
4. If you set [`Media.extend`](../../reference/api.md#django_components.ComponentMediaInput.extend) to a list,
   it should be a list of [`Component`](../../reference/api.md#django_components.Component) classes.

```py
from components.layout import LayoutComp

class MyTable(Component):
    class Media:
        js = [
            "path/to/script.js",
            "path/to/*.js",  # Or as a glob
            "https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js",  # AlpineJS
        ]
        css = {
            "all": [
                "path/to/style.css",
                "path/to/*.css",  # Or as a glob
                "https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css",  # TailwindCSS
            ],
            "print": ["path/to/style2.css"],
        }

        # Reuse JS / CSS from LayoutComp
        extend = [
            LayoutComp,
        ]
```

### CSS media types

You can define which stylesheets will be associated with which
[CSS media types](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_media_queries/Using_media_queries#targeting_media_types). You do so by defining CSS files as a dictionary.

See the corresponding [Django Documentation](https://docs.djangoproject.com/en/5.2/topics/forms/media/#css).

Again, you can set either a single file or a list of files per media type:

```py
class MyComponent(Component):
    class Media:
        css = {
            "all": "path/to/style1.css",
            "print": ["path/to/style2.css", "path/to/style3.css"],
        }
```

Which will render the following HTML:

```html
<link href="/static/path/to/style1.css" media="all" rel="stylesheet" />
<link href="/static/path/to/style2.css" media="print" rel="stylesheet" />
<link href="/static/path/to/style3.css" media="print" rel="stylesheet" />
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

### Media inheritance

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
    [Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#extend),
    with one exception:

    - When you set `extend` to a list, the list is expected to contain Component classes (or other classes that have a nested `Media` class).

### Accessing Media files

To access the files that you defined under [`Component.Media`](../../reference/api.md#django_components.Component.Media),
use [`Component.media`](../../reference/api.md#django_components.Component.media) (lowercase).

This is consistent behavior with
[Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#assets-as-a-static-definition).

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

When working with component media files, it is important to understand the difference:

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
([See example](#rendering-paths)).

## File paths

Unlike the [main HTML / JS / CSS files](html_js_css_files.md), the path definition for the secondary files are quite ergonomic.

### Relative to component

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

### Globs

Components can have many secondary files. To simplify their declaration, you can use globs.

Globs MUST be relative to the component's directory.

```py title="[project root]/components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    class Media:
        js = [
            "path/to/*.js",
            "another/path/*.js",
        ]
        css = "*.css"
```

How this works is that django-components will detect that the path is a glob, and will try to resolve all files matching the glob pattern relative to the component's directory.

After that, the file paths are handled the same way as if you defined them explicitly.

### Supported types

File paths can be any of:

- `str`
- `bytes`
- `PathLike` (`__fspath__` method)
- `SafeData` (`__html__` method)
- `Script`
- `Style`
- `Callable` that returns any of the above, evaluated at class creation (`__new__`)

To help with typing the union, use [`ComponentMediaInputPath`](../../reference/api.md#django_components.ComponentMediaInputPath).

```py
from pathlib import Path
from django_components import Script, Style
from django.utils.safestring import mark_safe

class SimpleComponent(Component):
    class Media:
        css = [
            mark_safe('<link href="/static/calendar/style1.css" rel="stylesheet" />'),
            Path("calendar/style1.css"),
            Style(content=".x { color: red; }"),
            "calendar/style2.css",
            b"calendar/style3.css",
            lambda: "calendar/style4.css",
        ]
        js = [
            mark_safe('<script src="/static/calendar/script1.js"></script>'),
            Path("calendar/script1.js"),
            Script(content="console.log('inline');", wrap=False),
            "calendar/script2.js",
            b"calendar/script3.js",
            lambda: "calendar/script4.js",
        ]
```

### Paths as objects

In the example [above](#supported-types), you can see that when we used Django's
[`mark_safe()`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.mark_safe)
to mark a string as a [`SafeString`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.SafeString),
we had to define the URL / path as an HTML `<script>`/`<link>` elements.

This is an extension of Django's [Paths as objects](https://docs.djangoproject.com/en/5.2/topics/forms/media/#paths-as-objects)
feature, where "safe" strings are taken as is, and are accessed only at render time.

Because of that, the paths defined as "safe" strings are NEVER resolved, neither relative to component's directory,
nor relative to [`COMPONENTS.dirs`](../../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs). It is assumed that you will define the full `<script>`/`<link>` tag with the correct URL / path.

"Safe" strings can be used to lazily resolve a path, or to customize the `<script>` or `<link>` tag for individual paths:

In the example below, we make use of "safe" strings to add `type="module"` to the script tag that will fetch `calendar/script2.js`.
In this case, we implemented a "safe" string by defining a `__html__` method.

```py
# Path object
class ModuleJsPath:
    def __init__(self, static_path: str) -> None:
        self.static_path = static_path

    # Lazily resolve the path
    def __html__(self):
        full_path = static(self.static_path)
        return format_html(
            f'<script type="module" src="{full_path}"></script>'
        )

@register("calendar")
class Calendar(Component):
    template_file = "calendar/template.html"

    class Media:
        css = "calendar/style1.css"
        js = [
            # <script> tag constructed by Media class
            "calendar/script1.js",
            # Custom <script> tag
            ModuleJsPath("calendar/script2.js"),
        ]
```

### `Script` and `Style` in Media

You can use [`Script`](../../reference/api.md#django_components.Script) and [`Style`](../../reference/api.md#django_components.Style) objects from `django_components` directly in [`Component.Media.js`](../../reference/api.md#django_components.ComponentMediaInput.js) and [`Component.Media.css`](../../reference/api.md#django_components.ComponentMediaInput.css). This lets you add inline JS/CSS or external URLs with custom attributes (e.g. `type="module"`, `nonce`) without building HTML strings.

```py
from django_components import Component, Script, Style

@register("calendar")
class Calendar(Component):
    class Media:
        js = [
            "calendar/script.js",  # path as usual
            Script(
                content="console.log('inline');",
                attrs={"type": "module"},
                wrap=False,
            ),
            Script(url="/static/analytics.js", content=None),
        ]
        css = [
            "calendar/style.css",
            Style(content=".print-only { display: none; }", attrs={"media": "print"}),
            Style(url="/static/print.css", content=None, attrs={"media": "print"}),
        ]
```

See [Modifying JS / CSS scripts](../advanced/rendering_js_css.md#modifying-js-css-scripts) for more on `Script`/`Style` and the `on_dependencies` hooks.

### Rendering paths

As part of the rendering process, the secondary JS / CSS files are resolved and rendered into `<link>` and `<script>` HTML tags, so they can be inserted into the render.

In the [Paths as objects](#paths-as-objects) section, we saw that we can use that to selectively change
how the HTML tags are constructed.

However, if you need to change how ALL CSS and JS files are rendered for a given component,
you can provide your own subclass of [Django's `Media` class](https://docs.djangoproject.com/en/5.2/topics/forms/media) to the [`Component.media_class`](../../reference/api.md#django_components.Component.media_class) attribute.

To change how the tags are constructed, you can override the [`Media.render_js()` and `Media.render_css()` methods](https://github.com/django/django/blob/fa7848146738a9fe1d415ee4808664e54739eeb7/django/forms/widgets.py#L102):

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
