## Introduction

Components consist of 3 parts - HTML, JS and CSS.

Handling of HTML is straightforward - it is rendered as is, and inserted where
the [`{% component %}`](../../../reference/template_tags#component) tag is.

However, handling of JS and CSS is more complex:

- JS and CSS is are inserted elsewhere in the HTML. As a best practice, JS is placed in the `<body>` HTML tag, and CSS in the `<head>`.
- Multiple components may use the same JS and CSS files. We don't want to load the same files multiple times.
- Fetching of JS and CSS may block the page, so the JS / CSS should be embedded in the HTML.
- Components inserted as HTML fragments need different handling for JS and CSS.

## Default JS / CSS locations

If your components use JS and CSS then, by default, the JS and CSS will be automatically inserted into the HTML:

- CSS styles will be inserted at the end of the `<head>`
- JS scripts will be inserted at the end of the `<body>`

If you want to place the dependencies elsewhere in the HTML, you can override
the locations by inserting following Django template tags:

- [`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies) - Set new location(s) for JS scripts
- [`{% component_css_dependencies %}`](../../../reference/template_tags#component_css_dependencies) - Set new location(s) for CSS styles

So if you have a component with JS and CSS:

```djc_py
from django_components import Component, types

class MyButton(Component):
    template: types.django_html = """
        <button class="my-button">
            Click me!
        </button>
    """

    js: types.js = """
        for (const btnEl of document.querySelectorAll(".my-button")) {
            btnEl.addEventListener("click", () => {
                console.log("BUTTON CLICKED!");
            });
        }
    """

    css: types.css """
        .my-button {
            background: green;
        }
    """

    class Media:
        js = ["/extra/script.js"]
        css = ["/extra/style.css"]
```

Then:

- JS from `MyButton.js` and `MyButton.Media.js` will be rendered at the default place (`<body>`),
  or in [`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies).

- CSS from `MyButton.css` and `MyButton.Media.css` will be rendered at the default place (`<head>`),
or in [`{% component_css_dependencies %}`](../../../reference/template_tags#component_css_dependencies).

And if you don't specify `{% component_dependencies %}` tags, it is the equivalent of:

```django
<!doctype html>
<html>
  <head>
    <title>MyPage</title>
    ...
    {% component_css_dependencies %}
  </head>
  <body>
    <main>
      ...
    </main>
    {% component_js_dependencies %}
  </body>
</html>
```

!!! warning

    If the rendered HTML does NOT contain neither `{% component_dependencies %}` template tags,
    nor `<head>` and `<body>` HTML tags, then the JS and CSS will NOT be inserted!

    To force the JS and CSS to be inserted, use the [`"append"`](#append) or [`"prepend"`](#prepend)
    strategies.

## Dependencies strategies

The rendered HTML may be used in different contexts (browser, email, etc).
If your components use JS and CSS scripts, you may need to handle them differently.

The different ways for handling JS / CSS are called **"dependencies strategies"**.

[`render()`](../../../reference/api/#django_components.Component.render) and [`render_to_response()`](../../../reference/api/#django_components.Component.render_to_response)
accept a `deps_strategy` parameter, which controls where and how the JS / CSS are inserted into the HTML.

```python
main_page = MainPage.render(deps_strategy="document")
fragment = MyComponent.render_to_response(deps_strategy="fragment")
```

The `deps_strategy` parameter is set at the root of a component render tree, which is why it is not available for
the [`{% component %}`](../../../reference/template_tags#component) tag.

When you use Django's [`django.shortcuts.render()`](https://docs.djangoproject.com/en/5.1/topics/http/shortcuts/#render)
or [`Template.render()`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Template.render) to render templates,
you can't directly set the `deps_strategy` parameter.

In this case, you can set the `deps_strategy` with the `DJC_DEPS_STRATEGY` context variable.

```python
from django.template.context import Context
from django.shortcuts import render

ctx = Context({"DJC_DEPS_STRATEGY": "fragment"})
fragment = render(request, "my_component.html", ctx=ctx)
```

!!! info

    The `deps_strategy` parameter is ultimately passed to [`render_dependencies()`](../../../reference/api/#django_components.render_dependencies).

!!! note "Why is `deps_strategy` required?"

    This is a technical limitation of the current implementation.

    When a component is rendered, django-components embeds metadata about the component's JS and CSS into the HTML.

    This way we can compose components together, and know which JS / CSS dependencies are needed.

    As the last step of rendering, django-components extracts this metadata and uses a selected strategy
    to insert the JS / CSS into the HTML.

There are six dependencies strategies:

- [`document`](../../advanced/rendering_js_css#document) (default)
    - Smartly inserts JS / CSS into placeholders or into `<head>` and `<body>` tags.
    - Inserts extra script to allow `fragment` strategy to work.
    - Assumes the HTML will be rendered in a JS-enabled browser.
- [`fragment`](../../advanced/rendering_js_css#fragment)
    - A lightweight HTML fragment to be inserted into a document with AJAX.
    - No JS / CSS included.
- [`simple`](../../advanced/rendering_js_css#simple)
    - Smartly insert JS / CSS into placeholders or into `<head>` and `<body>` tags.
    - No extra script loaded.
- [`prepend`](../../advanced/rendering_js_css#prepend)
    - Insert JS / CSS before the rendered HTML.
    - No extra script loaded.
- [`append`](../../advanced/rendering_js_css#append)
    - Insert JS / CSS after the rendered HTML.
    - No extra script loaded.
- [`ignore`](../../advanced/rendering_js_css#ignore)
    - HTML is left as-is. You can still process it with a different strategy later with
      [`render_dependencies()`](../../../reference/api/#django_components.render_dependencies).
    - Used for inserting rendered HTML into other components.

### `document`

`deps_strategy="document"` is the default. Use this if you are rendering a whole page, or if no other option suits better.

```python
html = Button.render(deps_strategy="document")
```

When you render a component tree with the `"document"` strategy, it is expected that:

- The HTML will be rendered at page load.
- The HTML will be inserted into a page / browser where JS can be executed.

**Location:**

JS and CSS is inserted:

- Preferentially into JS / CSS placeholders like [`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies)
- Otherwise, JS into `<body>` element, and CSS into `<head>` element
- If neither found, JS / CSS are NOT inserted

**Included scripts:**

For the `"document"` strategy, the JS and CSS is set up to avoid any delays when the end user loads
the page in the browser:

- Components' primary JS and CSS scripts ([`Component.js`](../../../reference/api/#django_components.Component.js)
  and [`Component.css`](../../../reference/api/#django_components.Component.css)) - fully inlined:

    ```html
    <script>
        console.log("Hello from Button!");
    </script>
    <style>
        .button {
            background-color: blue;
        }
    </style>
    ```

- Components' secondary JS and CSS scripts
  ([`Component.Media`](../../../reference/api/#django_components.Component.Media)) - inserted as links:

    ```html
    <link rel="stylesheet" href="https://example.com/styles.css" />
    <script src="https://example.com/script.js"></script>
    ```

- A JS script is injected to manage component dependencies, enabling lazy loading of JS and CSS
  for HTML fragments.

!!! info

    This strategy is required for fragments to work properly, as it sets up the dependency manager that fragments rely on.

!!! note "How the dependency manager works"

    The dependency manager is a JS script that keeps track of all the JS and CSS dependencies that have already been loaded.

    When a fragment is inserted into the page, it will also insert a JSON `<script>` tag with fragment metadata.

    The dependency manager will pick up on that, and check which scripts the fragment needs.

    It will then fetch only the scripts that haven't been loaded yet.

### `fragment`

`deps_strategy="fragment"` is used when rendering a piece of HTML that will be inserted into a page
that has already been rendered with the [`"document"`](#document) strategy:

```python
fragment = MyComponent.render(deps_strategy="fragment")
```

The HTML of fragments is very lightweight because it doesn't include the JS and CSS scripts
of the rendered components.

With fragments, even if a component has JS and CSS, you can insert the same component into a page
hundreds of times, and the JS and CSS will only ever be loaded once.

This is intended for dynamic content that's loaded with AJAX after the initial page load, such as with [jQuery](https://jquery.com/), [HTMX](https://htmx.org/), [AlpineJS](https://alpinejs.dev/) or similar libraries.

**Location:**

None. The fragment's JS and CSS files will be loaded dynamically into the page.

**Included scripts:**

- A special JSON `<script>` tag that tells the dependency manager what JS and CSS to load.

### `simple`

`deps_strategy="simple"` is used either for non-browser use cases, or when you don't want to use the dependency manager.

Practically, this is the same as the [`"document"`](#document) strategy, except that the dependency manager is not used.

```python
html = MyComponent.render(deps_strategy="simple")
```

**Location:**

JS and CSS is inserted:

- Preferentially into JS / CSS placeholders like [`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies)
- Otherwise, JS into `<body>` element, and CSS into `<head>` element
- If neither found, JS / CSS are NOT inserted

**Included scripts:**

- Components' primary JS and CSS scripts ([`Component.js`](../../../reference/api/#django_components.Component.js)
  and [`Component.css`](../../../reference/api/#django_components.Component.css)) - fully inlined:

    ```html
    <script>
        console.log("Hello from Button!");
    </script>
    <style>
        .button {
            background-color: blue;
        }
    </style>
    ```

- Components' secondary JS and CSS scripts
  ([`Component.Media`](../../../reference/api/#django_components.Component.Media)) - inserted as links:

    ```html
    <link rel="stylesheet" href="https://example.com/styles.css" />
    <script src="https://example.com/script.js"></script>
    ```

- No extra scripts are inserted.

### `prepend`

This is the same as [`"simple"`](#simple), but placeholders like [`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies) and HTML tags `<head>` and `<body>` are all ignored. The JS and CSS are **always** inserted **before** the rendered content.

```python
html = MyComponent.render(deps_strategy="prepend")
```

**Location:**

JS and CSS is **always** inserted before the rendered content.

**Included scripts:**

Same as for the [`"simple"`](#simple) strategy.

### `append`

This is the same as [`"simple"`](#simple), but placeholders like [`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies) and HTML tags `<head>` and `<body>` are all ignored. The JS and CSS are **always** inserted **after** the rendered content.

```python
html = MyComponent.render(deps_strategy="append")
```

**Location:**

JS and CSS is **always** inserted after the rendered content.

**Included scripts:**

Same as for the [`"simple"`](#simple) strategy.

### `ignore`

`deps_strategy="ignore"` is used when you do NOT want to process JS and CSS of the rendered HTML.

```python
html = MyComponent.render(deps_strategy="ignore")
```

The rendered HTML is left as-is. You can still process it with a different strategy later with `render_dependencies()`.

This is useful when you want to insert rendered HTML into another component.

```python
html = MyComponent.render(deps_strategy="ignore")
html = AnotherComponent.render(slots={"content": html})
```

## Manually rendering JS / CSS

When rendering templates or components, django-components covers all the traditional ways how components
or templates can be rendered:

-  [`Component.render()`](../../../reference/api/#django_components.Component.render)
-  [`Component.render_to_response()`](../../../reference/api/#django_components.Component.render_to_response)
-  [`Template.render()`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Template.render)
-  [`django.shortcuts.render()`](https://docs.djangoproject.com/en/5.1/topics/http/shortcuts/#render)

This way you don't need to manually handle rendering of JS / CSS.

However, for advanced or low-level use cases, you may need to control when to render JS / CSS.

In such case you can directly pass rendered HTML to [`render_dependencies()`](../../../reference/api/#django_components.render_dependencies).

This function will extract all used components in the HTML string, and insert the components' JS and CSS
based on given strategy.

!!! info

    The truth is that all the methods listed above call [`render_dependencies()`](../../../reference/api/#django_components.render_dependencies)
    internally.

**Example:**

To see how [`render_dependencies()`](../../../reference/api/#django_components.render_dependencies) works,
let's render a template with a component.

We will render it twice:

- First time, we let `template.render()` handle the rendering.
- Second time, we prevent `template.render()` from inserting the component's JS and CSS with `deps_strategy="ignore"`.

    Instead, we pass the "unprocessed" HTML to `render_dependencies()` ourselves to insert the component's JS and CSS.

```python
from django.template.base import Template
from django.template.context import Context
from django_components import render_dependencies

template = Template("""
    {% load component_tags %}
    <!doctype html>
    <html>
    <head>
        <title>MyPage</title>
    </head>
    <body>
        <main>
            {% component "my_button" %}
                Click me!
            {% endcomponent %}
        </main>
    </body>
    </html>
""")

rendered = template.render(Context({}))

rendered2_raw = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))
rendered2 = render_dependencies(rendered2_raw)

assert rendered == rendered2
```

Same applies to other strategies and other methods of rendering:

```python
raw_html = MyComponent.render(deps_strategy="ignore")
html = render_dependencies(raw_html, deps_strategy="document")

html2 = MyComponent.render(deps_strategy="document")

assert html == html2
```

## HTML fragments

Django-components provides a seamless integration with HTML fragments with AJAX ([HTML over the wire](https://hotwired.dev/)),
whether you're using jQuery, HTMX, AlpineJS, vanilla JavaScript, or other.

This is achieved by the combination of the [`"document"`](#document) and [`"fragment"`](#fragment) strategies.

Read more about [HTML fragments](../../advanced/html_fragments).
