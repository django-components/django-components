---
title: v0.148.0 (2026-02-05)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.148.0/
description: "- JS from Component.js is now scoped by default"
---

# v0.148.0 (2026-02-05)

#### Feat

- **JS from `Component.js` is now scoped by default**

    Until now, if you assigned a variable or declared a function in your `Component.js` code, it would be available in the global scope. This could cause conflicts with other scripts on the page.

    Now, the JS code is scoped, so you can't accidentally assign global variables or functions.

    To define global variables or functions, you should instead use the `globalThis` keyword:


    ```javascript
    globalThis.myGlobalVariable = "Hello, world!";

    globalThis.myGlobalFunction = () => {
        console.log("Hello, world!");
    };
    ```


- **`Component.on_dependencies` hook to override JS/CSS rendering**

    You can override [`Component.on_dependencies`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.Component.on_dependencies) (a **classmethod**) to modify the JS/CSS dependencies emitted by that component only - for example to inject a CSP nonce, change attributes, or wrap inline JS.

    The hook receives lists of [`Script`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.Script) and [`Style`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.Style) objects for this component (from `Component.js`/`Component.css`, [JS/CSS variables](https://django-components.github.io/django-components/0.148.0/concepts/fundamentals/html_js_css_variables), and Media). Return `(new_scripts, new_styles)` to replace them, or `None` to leave them unchanged.

    To modify **all** dependencies for the whole page, use the [extension hook](https://django-components.github.io/django-components/0.148.0/reference/extension_hooks#django_components.extension.ComponentExtension.on_dependencies) instead.

    **Example:**


    ```python
    from django_components import Component, Script, Style

    class MyButton(Component):
        @classmethod
        def on_dependencies(cls, scripts, styles):
            # Add a nonce to every inline style for this component
            for style in styles:
                if style.content and "nonce" not in style.attrs:
                    style.attrs["nonce"] = get_current_nonce()
            return (scripts, styles)
    ```


- **`ComponentExtension.on_dependencies` hook to override JS/CSS rendering**

    Say you want to add a CSP nonce to all scripts, or render scripts as `type="module"`.

    Before, you had to subclass a `Media` class to intercept how JS and CSS scripts are rendered.
    But this did not capture ALL JS and CSS scripts that are rendered.

    Now, there is a new [`on_dependencies`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.ComponentExtension.on_dependencies) extension hook that you can use to modify JS and CSS scripts before they are rendered.

    This hook exposes JS/CSS scripts as `Script` and `Style` objects, so you can modify them before they are rendered.

    You can add or remove attributes, add or remove entire scripts, and more. See [Modifying JS / CSS scripts](https://django-components.github.io/django-components/0.148.0/concepts/advanced/rendering_js_css#modifying-js--css-scripts) for more details.


    ```python
    from django_components import ComponentExtension, OnDependenciesContext, Script, Style

    class MyExtension(ComponentExtension):
        def on_dependencies(self, ctx: OnDependenciesContext):
            scripts = list(ctx.scripts)
            styles = list(ctx.styles)

            # Set nonce attribute on all JS scripts
            for script in scripts:
                script.attrs["nonce"] = "1234567890"

            return (scripts, styles)
    ```


- **`Dependency`, `Script`, and `Style` helper classes**

    Instead of modifying the JS and CSS scripts as raw strings like `<script>` and `<style>`,
    the JS and CSS dependencies are represented by helper objects:

    - [`Script`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.Script)
        - Represents a `<script>` tag.
        - Set `Script.wrap = False` to prevent classic JS from being wrapped in an IIFE.

    - [`Style`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.Style)
        - Represents a `<style>` tag or a `<link rel="stylesheet">` tag.
        - When `Style.url` is set, renders as `<link>`, otherwise as `<style>` with
        inline `content`.

- **Use `Script` and `Style` objects in `Component.Media.js` / `Component.Media.css`**

    You can now put [`Script`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.Script)
    and [`Style`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.Style)
    objects directly in [`Component.Media.js`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.ComponentMediaInput.js)
    and [`Component.Media.css`](https://django-components.github.io/django-components/0.148.0/reference/api#django_components.ComponentMediaInput.css).


    ```python
    from django_components import Component, Script, Style, register

    @register("calendar")
    class Calendar(Component):
        class Media:
            js = [
                Script(content="console.log('inline');")
            ]
            css = [
                Style(content=".x { color: red; }")
            ]
    ```


#### Fix

- Fixed race condition where `Component._template` was not set correctly when rendering multiple components in parallel.

    See [#1587](https://github.com/django-components/django-components/issues/1587)


    ```python
    class MyComponent(Component):
        template = "<div>Hello, world!</div>"
    ```


#### Refactor

- `Component.Media.js/css` now render BEFORE `Component.js/css`, instead of after.

- **Rendering components in Python is now simpler: No explicit `deps_strategy` needed when nested**

    When you pre-render a component in Python, and pass it into another component's `get_template_data()`,
    you should pass `deps_strategy="ignore"` to the render function to avoid rendering the dependencies twice.

    django-components now makes this easier for you.

    When you call `Component.render()` from Python inside another component (e.g. in `get_template_data()`),
    you no longer need to pass `deps_strategy="ignore"` to the inner Component. This is set automatically be default.

    Top-level renders still default to `"document"`.

    See [issue #1463](https://github.com/django-components/django-components/issues/1463).

    Before:


    ```py
    class Outer(Component):
        def get_template_data(self, args, kwargs, slots, context):
            content = Inner.render(deps_strategy="ignore")
            return {"content": content}
    ```


    After:


    ```py
    class Outer(Component):
        def get_template_data(self, args, kwargs, slots, context):
            content = Inner.render()  # no deps_strategy needed!
            return {"content": content}
    ```
