---
title: v0.141.0 (2025-06-10)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.141.0/
description: "- New extension hooks on_template_loaded, on_js_loaded, on_css_loaded, and on_template_compiled"
---

# v0.141.0 (2025-06-10)

#### Feat

- New extension hooks `on_template_loaded`, `on_js_loaded`, `on_css_loaded`, and `on_template_compiled`

    The first 3 hooks are called when Component's template / JS / CSS is loaded as a string.

    The `on_template_compiled` hook is called when Component's template is compiled to a Template.

    The `on_xx_loaded` hooks can modify the content by returning the new value.


    ```py
    class MyExtension(ComponentExtension):
        def on_template_loaded(self, ctx: OnTemplateLoadedContext) -> Optional[str]:
            return ctx.content + "<!-- Hello! -->"

        def on_js_loaded(self, ctx: OnJsLoadedContext) -> Optional[str]:
            return ctx.content + "// Hello!"

        def on_css_loaded(self, ctx: OnCssLoadedContext) -> Optional[str]:
            return ctx.content + "/* Hello! */"
    ```


    See all [Extension hooks](https://django-components.github.io/django-components/0.141.0/reference/extension_hooks/).

#### Fix

- Subclassing - Previously, if a parent component defined `Component.template` or `Component.template_file`, it's subclass would use the same `Template` instance.

    This could lead to unexpected behavior, where a change to the template of the subclass would also change the template of the parent class.

    Now, each subclass has it's own `Template` instance, and changes to the template of the subclass do not affect the template of the parent class.

- Fix Django failing to restart due to "TypeError: 'Dynamic' object is not iterable" ([#1232](https://github.com/django-components/django-components/issues/1232))

- Fix bug when error formatting failed when error value was not a string.

#### Refactor

- `components ext run` CLI command now allows to call only those extensions that actually have subcommands.