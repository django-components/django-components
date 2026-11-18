## Introduction

Components consist of 3 parts - HTML, JS and CSS.

Handling of HTML is straightforward - it is rendered as is, and inserted where
the [`{% component %}`](../../reference/template_tags.md#component) tag is.

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

- [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies) - Set new location(s) for JS scripts
- [`{% component_css_dependencies %}`](../../reference/template_tags.md#component_css_dependencies) - Set new location(s) for CSS styles

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
  or in [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies).

- CSS from `MyButton.css` and `MyButton.Media.css` will be rendered at the default place (`<head>`),
  or in [`{% component_css_dependencies %}`](../../reference/template_tags.md#component_css_dependencies).

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

[`render()`][Component.render] and [`render_to_response()`][Component.render_to_response]
accept a `deps_strategy` parameter, which controls where and how the JS / CSS are inserted into the HTML.

```python
main_page = MainPage.render(deps_strategy="document")
fragment = MyComponent.render_to_response(deps_strategy="fragment")
```

The `deps_strategy` parameter is set at the root of a component render tree, which is why it is not available for
the [`{% component %}`](../../reference/template_tags.md#component) tag.

When you use Django's [`django.shortcuts.render()`](https://docs.djangoproject.com/en/5.2/topics/http/shortcuts/#render)
or [`Template.render()`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template.render) to render templates,
you can't directly set the `deps_strategy` parameter.

In this case, you can set the `deps_strategy` with the `DJC_DEPS_STRATEGY` context variable.

```python
from django.template.context import Context
from django.shortcuts import render

ctx = Context({"DJC_DEPS_STRATEGY": "fragment"})
fragment = render(request, "my_component.html", ctx=ctx)
```

!!! info

    The `deps_strategy` parameter is ultimately passed to [`render_dependencies()`][render_dependencies].

!!! note "Why is `deps_strategy` required?"

    This is a technical limitation of the current implementation.

    When a component is rendered, django-components embeds metadata about the component's JS and CSS into the HTML.

    This way we can compose components together, and know which JS / CSS dependencies are needed.

    As the last step of rendering, django-components extracts this metadata and uses a selected strategy
    to insert the JS / CSS into the HTML.

There are six dependencies strategies:

- [`document`](#document) (default for top-level)
    - Smartly inserts JS / CSS into placeholders or into `<head>` and `<body>` tags.
    - Requires the HTML to be rendered in a JS-enabled browser.
    - Inserts extra script for managing fragments.
- [`fragment`](#fragment)
    - A lightweight HTML fragment to be inserted into a document with AJAX.
    - Fragment will fetch its own JS / CSS dependencies when inserted into the page.
    - Requires the HTML to be rendered in a JS-enabled browser.
- [`simple`](#simple)
    - Smartly insert JS / CSS into placeholders or into `<head>` and `<body>` tags.
    - No extra script loaded.
- [`prepend`](#prepend)
    - Insert JS / CSS before the rendered HTML.
    - No extra script loaded.
- [`append`](#append)
    - Insert JS / CSS after the rendered HTML.
    - No extra script loaded.
- [`ignore`](#ignore) (default when nested)
    - HTML is left as-is. You can still process it with a different strategy later with
      [`render_dependencies()`][render_dependencies].
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

- Preferentially into JS / CSS placeholders like [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies)
- Otherwise, JS into `<body>` element, and CSS into `<head>` element
- If neither found, JS / CSS are NOT inserted

**Included scripts:**

For the `"document"` strategy, the JS and CSS is set up to avoid any delays when the end user loads
the page in the browser:

- Components' primary JS and CSS scripts ([`Component.js`][Component.js]
  and [`Component.css`][Component.css]) - fully inlined:

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
  ([`Component.Media`][Component.Media]) - inserted as links:

    ```html
    <link rel="stylesheet" href="https://example.com/styles.css" />
    <script src="https://example.com/script.js"></script>
    ```

- A JS script is injected to manage component dependencies, enabling lazy loading of JS and CSS
  for HTML fragments.

!!! note "How the dependency manager works"

    The dependency manager is a JS script that keeps track of all the JS and CSS dependencies that have already been loaded.

    When a fragment is inserted into the page, it will also insert a JSON `<script>` tag with fragment metadata.

    The dependency manager will pick up on that, and check which scripts the fragment needs.

    It will then fetch only the scripts that haven't been loaded yet.

### `fragment`

`deps_strategy="fragment"` is used when rendering a piece of HTML that will be inserted into a page:

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

- Preferentially into JS / CSS placeholders like [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies)
- Otherwise, JS into `<body>` element, and CSS into `<head>` element
- If neither found, JS / CSS are NOT inserted

**Included scripts:**

- Components' primary JS and CSS scripts ([`Component.js`][Component.js]
  and [`Component.css`][Component.css]) - fully inlined:

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
  ([`Component.Media`][Component.Media]) - inserted as links:

    ```html
    <link rel="stylesheet" href="https://example.com/styles.css" />
    <script src="https://example.com/script.js"></script>
    ```

- No extra scripts are inserted.

### `prepend`

This is the same as [`"simple"`](#simple), but placeholders like [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies) and HTML tags `<head>` and `<body>` are all ignored. The JS and CSS are **always** inserted **before** the rendered content.

```python
html = MyComponent.render(deps_strategy="prepend")
```

**Location:**

JS and CSS is **always** inserted before the rendered content.

**Included scripts:**

Same as for the [`"simple"`](#simple) strategy.

### `append`

This is the same as [`"simple"`](#simple), but placeholders like [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies) and HTML tags `<head>` and `<body>` are all ignored. The JS and CSS are **always** inserted **after** the rendered content.

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

The rendered HTML is left as-is. You can still process it with a different strategy later with [`render_dependencies()`][render_dependencies].

This is useful when you want to insert rendered HTML into another component.

```python
html = MyComponent.render(deps_strategy="ignore")
html = AnotherComponent.render(slots={"content": html})
```

### Behavior inside `get_template_data()`

When you pre-render a component in Python, and pass it into another component's `get_template_data()`,
you should pass `deps_strategy="ignore"` to the render function to avoid rendering the dependencies twice.

```py
class Outer(Component):
    def get_template_data(self, args, kwargs, slots, context):
        content = Inner.render(deps_strategy="ignore")
        return {"content": content}
```

django-components makes this easier for you. When you
are inside another component, the `deps_strategy` defaults to `"ignore"` automatically.

Top-level renders still default to `"document"`.

```py
class Outer(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # defaults to "ignore" when nested
        content = Inner.render()
        return {"content": content}

# `deps_strategy` defaults to "document" when top-level
rendered = Outer.render()
```

## Modifying JS / CSS scripts

Before JS and CSS dependencies are rendered into `<script>`, `<style>`, and `<link>` tags,
they can be modified in two places:

1. **Per component:** Each component's dependencies are passed through that component's [`Component.on_dependencies()`][Component.on_dependencies] hook. This includes the component's [`Component.js`][Component.js] / [`Component.css`][Component.css] and [JS/CSS variables](../fundamentals/html_js_css_variables.md). See [Component hooks: on_dependencies](hooks.md#on_dependencies).
2. **Globally:** The combined list of all dependencies is then passed through the [`ComponentExtension.on_dependencies`][ComponentExtension.on_dependencies] extension hook.

You can use these hooks to add, remove, or modify [`Script`][Script] and [`Style`][Style] objects,
so that the final HTML reflects your changes.

Use cases include:

- Adding a custom `<script>` or `<style>` (e.g. analytics, CSP nonce)
- Removing or reordering scripts or styles
- Changing attributes on scripts (e.g. `type="module"`) or styles

### Component hook: `on_dependencies`

[`Component.on_dependencies`][Component.on_dependencies] is a **classmethod** hook that allows you to modify the JS / CSS dependencies emitted by this component only.

These are the `<script>` and `<style>` tags that will be rendered for this component.

The JS / CSS are available as lists of [`Script`][Script] and [`Style`][Style] objects.

**Example:**

```python
from django_components import Component, Script, Style

class MyButton(Component):
    # ...

    @classmethod
    def on_dependencies(cls, scripts, styles):
        # Add a nonce to every inline style for this component
        for style in styles:
            if style.content and "nonce" not in style.attrs:
                style.attrs["nonce"] = get_current_nonce()
        return (scripts, styles)
```

Full details and more examples are in [Component hooks](hooks.md#on_dependencies).

### Extension hook: `on_dependencies`

In the [`ComponentExtension.on_dependencies`][ComponentExtension.on_dependencies] hook, you can modify the **entire** list of [`Script`][Script] and [`Style`][Style] objects that will be rendered (all components and Media).

Return a tuple `(scripts, styles)` to replace the lists that will be rendered, or `None` to leave dependencies unchanged.

**Example:**

```python
from django_components import ComponentExtension, OnDependenciesContext, Script, Style

class MyExtension(ComponentExtension):
    name = "my_extension"

    def on_dependencies(self, ctx: OnDependenciesContext):
        scripts = list(ctx.scripts)
        styles = list(ctx.styles)
        # Add a nonce to every inline style
        for style in styles:
            if style.content and "nonce" not in style.attrs:
                style.attrs["nonce"] = get_current_nonce()
        return (scripts, styles)
```

See [Extensions](extensions.md) for how to register and configure extensions.

### Wrapping inline JS in a self-executing function

By default, inline JavaScript in component scripts is wrapped in a [**self-executing (IIFE)**](https://developer.mozilla.org/en-US/docs/Glossary/IIFE) function
so that variables do not leak into the global scope.

Whether a given `<script>` is wrapped depends on [`Script.wrap`][Script] (default `True`) and the script's `type` attribute.

To disable wrapping for a specific script, set
[`Script.wrap`][Script] to `False`.

```python
script = Script(
    content="console.log('Hello');",
    wrap=False,
)
```

**Wrapping is applied when:**

- No `type` attribute, e.g. `<script>`
- Empty `type`, e.g. `<script type="">`
- JavaScript MIME types, e.g. `type="text/javascript"` or `type="application/javascript"`

**Wrapping is NOT applied when:**

Anything else is not wrapped. This includes:

- `type="module"` - ES modules have their own scope
- `type="importmap"` - import map JSON, not executable JS
- `type="speculationrules"` - speculation rules JSON
- `type="application/json"` or any other non-JS type - data blocks are not executed as script

## Manually rendering JS / CSS

When rendering templates or components, django-components covers all the traditional ways how components
or templates can be rendered:

- [`Component.render()`][Component.render]
- [`Component.render_to_response()`][Component.render_to_response]
- [`Template.render()`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template.render)
- [`django.shortcuts.render()`](https://docs.djangoproject.com/en/5.2/topics/http/shortcuts/#render)

This way you don't need to manually handle rendering of JS / CSS.

However, for advanced or low-level use cases, you may need to control when to render JS / CSS.

In such case you can directly pass rendered HTML to [`render_dependencies()`][render_dependencies].

This function will extract all used components in the HTML string, and insert the components' JS and CSS
based on given strategy.

!!! info

    The truth is that all the methods listed above call [`render_dependencies()`][render_dependencies]
    internally.

**Example:**

To see how [`render_dependencies()`][render_dependencies] works,
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

## Content Security Policy

If your site sends a [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP) with a nonce, use the [`ComponentExtension.on_dependencies`][ComponentExtension.on_dependencies] hook to put the nonce on the scripts:

```python
from django_components import ComponentExtension, OnDependenciesContext

class NonceExtension(ComponentExtension):
    name = "nonce"

    def on_dependencies(self, ctx: OnDependenciesContext):
        for script in ctx.scripts:
            script.attrs["nonce"] = get_current_nonce()
        for style in ctx.styles:
            if style.content:
                style.attrs["nonce"] = get_current_nonce()
        return (ctx.scripts, ctx.styles)
```

Here `get_current_nonce()` stands for a helper of your own. The hook gets no `request`, so have a middleware keep the request's nonce in a [`ContextVar`](https://docs.python.org/3/library/contextvars.html) for the helper to read.

Use `'strict-dynamic'` in your policy if you use [fragments](html_fragments.md). A fragment's files load through the dependency manager, and this hook doesn't see them, so they carry no nonce of their own. Stylesheets get no help from `'strict-dynamic'`, so your `style-src` must allow them.

Also add `base-uri 'self'` to your policy. The browser then ignores a `<base>` tag that an attacker injects into the page. Without it, such a tag moves every relative URL on the page to the attacker's site, and the nonce lets those scripts run.

With Django 6.0 and newer:

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "base-uri": [CSP.SELF],
    # ...
}
```

### How django-components protects the page

If an attacker can inject HTML into your page, django-components limits what the injected HTML can do to its own JS.

**The dependency manager file.** The tag that loads the dependency manager carries `integrity` and `crossorigin="anonymous"`, so the browser runs only the exact file from your installed django-components. The same goes for the JS and CSS files that a fragment loads from `/components/cache/`.

If the browser gets a file with other bytes, it refuses the file, and component JS does not run. So:

- Run `collectstatic` when you upgrade.
- Clear CDN caches and whole-page caches, such as `cache_page`, when you upgrade. A cached page asks for the old file by its hash.
- During a rolling deploy, deploy your static files before the new HTML, or use hashed file names with [`ManifestStaticFilesStorage`](https://docs.djangoproject.com/en/stable/ref/contrib/staticfiles/#manifeststaticfilesstorage). If a new page asks an old server for the file, the browser can cache the old bytes under the new URL and keep refusing them.
- Exclude your static files from any proxy that rewrites JS.
- If a relative `STATIC_URL` redirects to another host, or your own `<base>` tag points at one, that host must send `Access-Control-Allow-Origin`.

The URL of the dependency manager gets a `?v=` version made from its content, so a visitor's browser doesn't keep using the file from an older release.

If `STATIC_URL` is a full URL such as `https://cdn.example.com/static/`, the tag stays as it was. A `<base>` tag can't move a full URL.

Files from [`Component.Media`][ComponentMediaInput] carry no hash, because they are your files and django-components doesn't know their content. `base-uri 'self'` is what protects them.

**The JSON blocks.** A `<script data-djc>` block tells the dependency manager which files to load and which components to call. When the dependency manager's own tag has a nonce, it obeys only a block with the same nonce in its JSON, and logs an error in the browser console for any other block. You don't need to write this nonce yourself. django-components copies it into the JSON from the tag that your hook gave a nonce to.

### Fragments on a page with a nonce

A [fragment](html_fragments.md) needs the nonce of the page it goes into, and a fragment response is a separate request. So keep the page's nonce on the server when you render the page, and use that nonce when you render the fragment:

```python
class MyPage(Component):
    class View:
        def get(self, request):
            # The nonce that this response sends in its policy
            nonce = str(get_current_nonce())
            request.session["page_nonce"] = nonce
            return self.component_cls.render_to_response(
                request=request,
            )


class Frag(Component):
    class View:
        def get(self, request):
            # From here on, `get_current_nonce()` gives the page's
            # nonce. `set_current_nonce()` is your own helper too.
            set_current_nonce(request.session["page_nonce"])
            return self.component_cls.render_to_response(
                request=request,
                deps_strategy="fragment",
            )
```

A session holds one nonce, so when a user opens your site in a second tab, fragments sent to the first tab stop starting. Store one nonce per page if your users work in several tabs.

Tools that swap the whole page with JS, such as `hx-boost` or Turbo, have the same limit. The dependency manager stays from the first page, so the new page needs the first page's nonce, or a full reload.

### Pages without a nonce

The dependency manager reads the nonce from its own tag. When that tag has no nonce, it has nothing to compare, so it can't tell your `<script data-djc>` blocks from injected ones. This is the case when:

- Your policy uses hashes or hosts, and the tag has no nonce.
- Your site sends no policy.
- A hook renders the tag with `type="module"`. A module can't read the tag that loaded it.

On such a page, a block loads a script only when the file is one that your app serves:

- the JS file of a component, which django-components serves from `/components/cache/` on the page's origin;
- a file under your `STATIC_URL`, such as a relative path in [`Component.Media.js`][ComponentMediaInput].

The dependency manager finds `STATIC_URL` from its own URL, `<STATIC_URL>django_components/django_components.min.js`. A `STATIC_URL` on another host, such as `https://cdn.example.com/static/`, counts when the tag has no `integrity`, which is how django-components writes the tag for such a URL. The dependency manager can't work out `STATIC_URL` in these cases, so only files from `/components/cache/` load:

- `STATIC_URL = "/"`, because the root of your site would include every path on it;
- a `type="module"` tag, or a tag on another host that a hook gave an `integrity`;
- a CDN or proxy that serves the file from another folder, so its URL has no `django_components/` folder;
- a URL with `%` in its path.

The dependency manager skips any other script, and the browser console shows an error. The fragment's components still run, but their JS fails where it needs the skipped script. When you render a fragment without a nonce, django-components also logs a warning on the server for each script it expects the dependency manager to skip, once per URL. The dependency manager also ignores a block that holds JS variables, because django-components sends them in a file of their own.

The dependency manager loads each of these scripts from its full URL, read against the page's address, so a `<base>` tag can't move them.

So on a page without a nonce, even on a site with no policy at all, a fragment's `Component.Media.js` loads only files under `STATIC_URL`. A script from a CDN, or from another path on your site such as Django's `/jsi18n/`, doesn't load. To use such a script, do one of these:

- Load it on the page itself. When a component on the page lists the same URL in its `Component.Media.js`, the dependency manager knows that the page has the script, and doesn't ask for it again. If you load it with a `<script>` tag of your own, also call `DjangoComponents.manager.markScriptLoaded("js", url)` from your own JS, with the URL exactly as the fragment writes it, before the fragment arrives.
- Serve the file from your `STATIC_URL`.
- Give the page a nonce, as described above. On a page with a nonce, a fragment loads every script it names.

What this can't cover: injected HTML can still start your page's components on elements it adds, with data files your server already wrote, and load any file under `STATIC_URL`. A library there that acts on the HTML of the page, such as htmx or Alpine.js, then does what the injected HTML tells it. If visitors can upload files that your site serves as JavaScript from its own domain, injected HTML can load those too, through a copy of the dependency manager uploaded into a folder named `django_components`. Give pages that receive fragments a nonce, and serve uploads from another domain.

### What the nonce check can't cover

The check relies on your policy to refuse a script tag with no nonce. If `script-src` allows `'self'` or a host that serves your static files, an attacker can inject a second copy of the dependency manager. That copy has no nonce, so it treats the page as one [without a nonce](#pages-without-a-nonce): it obeys every block, and loads the scripts that such a page allows. Prefer `'strict-dynamic'`, which makes the browser ignore `'self'` and hosts.

## HTML fragments

Django-components provides a seamless integration with HTML fragments with AJAX ([HTML over the wire](https://hotwired.dev/)),
whether you're using jQuery, HTMX, AlpineJS, vanilla JavaScript, or other.

This is achieved by the [`"fragment"`](#fragment) strategy.

Read more about [HTML fragments](html_fragments.md).
