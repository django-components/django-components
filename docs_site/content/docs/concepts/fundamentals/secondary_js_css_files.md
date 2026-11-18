## Overview

Each component can define extra or "secondary" CSS / JS files using the nested [`Component.Media`][Component.Media] class,
by setting [`Component.Media.js`][ComponentMediaInput.js] and [`Component.Media.css`][ComponentMediaInput.css].

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
  or any other object with an `__html__` method, is treated as an already-built HTML tag. django-components
  doesn't resolve its path, and the default `media_class.render_js()` and `media_class.render_css()` output
  what its `__html__` method returns. Django's `Script` is one of these objects, and it still applies
  `{% static %}` to its path.
- **Inheritance** - You can set [`extend`][ComponentMediaInput.extend] to configure
  whether to inherit JS / CSS from parent components. See [Media inheritance](#media-inheritance).

However, there's a few differences from Django's Media class:

1. Our Media class accepts various formats for the JS and CSS files: either a single file, a list,
   or (CSS-only) a dictonary (See [`ComponentMediaInput`][ComponentMediaInput]).
2. Individual JS / CSS files can be any of `str`, `bytes`, `Path`,
   [`SafeString`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.SafeString), or a function
   (See [`ComponentMediaInputPath`][ComponentMediaInputPath]).
3. Individual JS / CSS files can be glob patterns, e.g. `*.js` or `styles/**/*.css`.
4. If you set [`Media.extend`][ComponentMediaInput.extend] to a list,
   it should be a list of [`Component`][Component] classes.

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

print(MyComponent.media.render_js())
# ['<script src="/static/script.js"></script>',
#  '<script src="/static/parent.js"></script>']
```

The component's own files come first, then the parent's. Django's `Media` class does the opposite.

You can set the component NOT to inherit from the parent component by setting the [`extend`][ComponentMediaInput.extend] attribute to `False`:

```python
class ParentComponent(Component):
    class Media:
        js = ["parent.js"]

class MyComponent(ParentComponent):
    class Media:
        extend = False  # Don't inherit parent media
        js = ["script.js"]

print(MyComponent.media.render_js())
# ['<script src="/static/script.js"></script>']
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

print(MyComponent.media.render_js())
# ['<script src="/static/script.js"></script>',
#  '<script src="/static/other2.js"></script>',
#  '<script src="/static/other1.js"></script>']
```

Don't rely on the order of the files that come from the classes in `extend`. If one file must load
before another, list both in the same `js` list, in the order you need. For example, a component can list
`["parent.js", "script.js"]` even though its parent also declares `parent.js`.

!!! info

    The `extend` behaves consistently with
    [Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#extend),
    with two exceptions:

    - When you set `extend` to a list, the list is expected to contain Component classes (or other classes that have a nested `Media` class).
    - The component's own files come before the files it inherits.

### Accessing Media files

To access the files that you defined under [`Component.Media`][Component.Media],
use [`Component.media`][Component.media] (lowercase).

This is consistent behavior with
[Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#assets-as-a-static-definition).

```py
class MyComponent(Component):
    class Media:
        js = "path/to/script.js"
        css = "path/to/style.css"

print(MyComponent.media)
# Output:
# <link href="/static/path/to/style.css" media="all" rel="stylesheet">
# <script src="/static/path/to/script.js"></script>
```

When working with component media files, it is important to understand the difference:

- `Component.Media`

    - Is the "raw" media definition, or the input, which holds only the component's **own** media definition
    - This class is NOT instantiated, it merely holds the JS / CSS files.

- `Component.media`
    - Returns all resolved media files, **including** those inherited from parent components
    - Is an instance of [`Component.media_class`][Component.media_class]

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
print(ChildComponent.media.render_js())
# ['<script src="/static/child.js"></script>',
#  '<script src="/static/parent.js"></script>']
```

!!! note

    You should **not** manually modify `Component.media` or `Component.Media` after the component has been resolved, as this may lead to unexpected behavior.

If you want to modify the class that is instantiated for [`Component.media`][Component.media],
you can configure [`Component.media_class`][Component.media_class]
([See example](#change-how-every-file-is-rendered)).

## File paths

Unlike the [main HTML / JS / CSS files](html_js_css_files.md), the path definition for the secondary files are quite ergonomic.

### Relative to component

As seen in the [getting started example](../../getting_started/your_first_component.md), to associate HTML / JS / CSS
files with a component, you can set them as
[`Component.template_file`][Component.template_file],
[`Component.js_file`][Component.js_file]
and
[`Component.css_file`][Component.css_file] respectively:

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
[`COMPONENTS.dirs`][ComponentsSettings.dirs]
or
[`COMPONENTS.app_dirs`][ComponentsSettings.app_dirs].

If you specify the paths relative to component's directory, django-componenents does the conversion automatically
for you.

Thus, assuming that
[`COMPONENTS.dirs`][ComponentsSettings.dirs]
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
    in [`COMPONENTS.dirs`][ComponentsSettings.dirs]
    or
    [`COMPONENTS.app_dirs`][ComponentsSettings.app_dirs].

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
- `Script` and `Style` from `django_components`
- `Script` from `django.forms.widgets` (Django's class, see [Add attributes to a single script](#add-attributes-to-a-single-script))
- `Callable` that returns any of the above, evaluated at class creation (`__new__`)

To help with typing the union, use [`ComponentMediaInputPath`][ComponentMediaInputPath].

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
nor relative to [`COMPONENTS.dirs`][ComponentsSettings.dirs]. It is assumed that you will define the full `<script>`/`<link>` tag with the correct URL / path.

"Safe" strings can be used to lazily resolve a path, or to customize the `<script>` or `<link>` tag for individual paths:

In the example below, we make use of "safe" strings to add `type="module"` to the script tag that will fetch `calendar/script2.js`.
In this case, we implemented a "safe" string by defining a `__html__` method.

To add attributes to one file, you usually don't need a custom class. See [Add attributes to a single script](#add-attributes-to-a-single-script).

```py
from django.templatetags.static import static
from django.utils.html import format_html
from django_components import Component, register

# Path object
class ModuleJsPath:
    def __init__(self, static_path: str) -> None:
        self.static_path = static_path

    # Lazily resolve the path
    def __html__(self):
        full_path = static(self.static_path)
        return format_html(
            '<script type="module" src="{}"></script>',
            full_path,
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

You can use [`Script`][Script] and [`Style`][Style] objects from `django_components` directly in [`Component.Media.js`][ComponentMediaInput.js] and [`Component.Media.css`][ComponentMediaInput.css]. This lets you add inline JS/CSS or external URLs with custom attributes (e.g. `type="module"`, `nonce`) without building HTML strings.

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

You can change these tags for one file, or for all files of a component.

#### Add attributes to a single script

To add attributes such as `type="module"` to one JS file, use Django's
[`Script`](https://docs.djangoproject.com/en/5.2/topics/forms/media/#script-objects) class
in [`Media.js`][ComponentMediaInput.js]. You don't need a custom `media_class`, and this works on
every Django version that django-components supports.

django-components has its own [`Script`][Script] class with the same name. Choose by what you have:

- Use Django's `Script`, from `django.forms.widgets`, for a file in your static directories.
  Django applies `{% static %}` to the path.
- Use [`Script`][Script] from `django_components` for inline JS, or for a URL that is ready to use.
  It outputs `url` unchanged.

```py
from django.forms.widgets import Script
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar/template.html"

    class Media:
        css = "calendar/style1.css"
        js = [
            "calendar/script1.js",
            # Renders with type="module"
            Script("calendar/script2.js", type="module"),
        ]
```

django-components resolves a path relative to the component's directory only when it is a string,
`bytes` or a `Path`. It doesn't do this for Django's `Script`, so give the path that `{% static %}` expects.
In the example above, that is `"calendar/script2.js"`, even if `script2.js` is next to the component's Python file.

To use both `Script` classes in one file, rename one: `from django.forms.widgets import Script as DjangoScript`.

For a stylesheet, use [`Style`][Style] with `url` and `attrs`, as shown in
[`Script` and `Style` in Media](#script-and-style-in-media). `Style` outputs `url` unchanged, so give it
a full URL, such as the result of `static()`.

#### Change how every file is rendered

If you need to change how ALL CSS and JS files are rendered for a given component,
you can provide your own subclass of [Django's `Media` class](https://docs.djangoproject.com/en/5.2/topics/forms/media) to the [`Component.media_class`][Component.media_class] attribute.

To change how the tags are constructed, you can override the [`Media.render_js()` and `Media.render_css()` methods](https://github.com/django/django/blob/6.1/django/forms/widgets.py#L194).

This example adds `type="module"` to each tag built from a path in `Media.js`, and works on Django 5.2, 6.0 and 6.1.
Tags from `mark_safe()` strings and from [`Script`][Script] in `django_components` stay as they are,
and so does the component's own `js_file`.

```py
from django.forms.utils import flatatt
from django.forms.widgets import Media, Script
from django.utils.html import format_html
from django_components import Component, register

class MyMedia(Media):
    def render_js(self, *, attrs=None):
        tags = []
        for item in self._js:
            if isinstance(item, Script):
                url = item.path
            elif hasattr(item, "__html__"):
                tags.append(item.__html__())
                continue
            else:
                url = self.absolute_path(item)
            tags.append(format_html(
                '<script type="module" src="{}"{}></script>',
                url, flatatt(attrs or {}),
            ))
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

Four parts of this override matter:

- **It accepts `attrs`.** Django 6.1 passes this keyword argument to `render_js()` and `render_css()`
  when something calls `Media.render()`, for example when you print `Calendar.media`.
  Without it, you get a `TypeError`. Rendering a component doesn't call `Media.render()`, so a page can
  render fine and this error appears only when you print the media.
- **It checks for `Script` before `__html__`.** On Django 6.1, `self._js` holds a Django `Script` object
  for each path. On Django 5.2 and 6.0, it holds a string. `Script` objects also have an `__html__` method,
  so if you check `__html__` first, every tag keeps Django's default form and you lose `type="module"` with no error.
- **It doesn't pass a `Script` to `absolute_path()`.** On Django 6.1, that raises
  `AttributeError: 'Script' object has no attribute 'startswith'` when the component renders.
- **It rebuilds `Script` tags.** Other attributes set on a Django `Script` object in `Media.js`,
  such as `defer=True` or `integrity`, are not rendered. To keep them, read `item.attributes` in the
  `Script` branch and pass them to `flatatt()` too.

If your override calls `super().render_js()`, pass `attrs` only on Django 6.1. Django 5.2 and 6.0 don't accept it.

`render_css()` needs the same changes. On Django 6.1, `self._css` holds `Stylesheet` objects.
That class doesn't exist in Django 5.2 and 6.0, so check for the `path` attribute instead.
This example adds `fetchpriority="high"` to each `<link>` tag. Put the method in the same `Media` subclass
as `render_js()`:

```py
from django.forms.utils import flatatt
from django.forms.widgets import Media
from django.utils.html import format_html

class MyMedia(Media):
    def render_css(self, *, attrs=None):
        tags = []
        for medium in sorted(self._css):
            for item in self._css[medium]:
                if hasattr(item, "path"):
                    url = item.path
                elif hasattr(item, "__html__"):
                    tags.append(item.__html__())
                    continue
                else:
                    url = self.absolute_path(item)
                tags.append(format_html(
                    '<link href="{}" media="{}" rel="stylesheet"'
                    ' fetchpriority="high"{}>',
                    url, medium, flatatt(attrs or {}),
                ))
        return tags
```
