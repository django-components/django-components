---
title: v0.147.0 (2026-02-02)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.147.0/
description: "Added support for Django 6.0, JS and CSS variables, and component tree navigation."
---

# v0.147.0 (2026-02-02)

Added support for Django 6.0, JS and CSS variables, and component tree navigation.

#### Breaking changes 🚨📢

- Dropped support for Python 3.8 and 3.9.

- Dropped support for Django 5.1.

#### Feat

- **JS variables with `get_js_data()`**

    Pass data from Python to JavaScript with `Component.get_js_data()`.

    `Component.get_js_data()` returns a dictionary. This data is automatically
    serialized to JSON and made available to your component's JavaScript code.

    In your JavaScript file, access these variables using the `$onComponent()` callback function.

    JS variables are automatically scoped to each component instance. Different
    instances of the same component can have different JS variable values.

    **Example:**


    ```python
    from django_components import Component, register

    @register("product_card")
    class ProductCard(Component):
        template_file = "product_card.html"
        js_file = "product_card.js"
        css_file = "product_card.css"

        def get_js_data(self, args, kwargs: Kwargs, slots, context):
            product = Product.objects.get(id=kwargs.product_id)
            return {
                "product_id": kwargs.product_id,
                "price": float(product.price),
                "api_endpoint": f"/api/products/{kwargs.product_id}/",
            }
    ```



    ```javascript
    // product_card.js

    // Access component JS variables in $onComponent callback
    $onComponent(({ product_id, price, api_endpoint }, ctx) => {
      const containerEl = ctx.els[0];
      containerEl.querySelector(".add-to-cart")
        .addEventListener("click", () => {
          fetch(api_endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "add_to_cart", price: price }),
          });
        });
    });
    ```


- **CSS variables with `get_css_data()`**

    Pass data from Python to CSS with [`get_css_data()`](https://django-components.github.io/django-components/0.147.0/reference/api#django_components.Component.get_css_data).

    [`get_css_data()`](https://django-components.github.io/django-components/0.147.0/reference/api#django_components.Component.get_css_data) returns a dictionary. This data is automatically
    converted to CSS custom properties and made available in your component's CSS.

    In your CSS file, access these variables using `var()`.

    CSS variables are automatically scoped to each component instance, allowing different
    instances of the same component to have different variable values.

    **Example:**


    ```python
    class ThemeableButton(Component):
        template_file = "button.html"
        css_file = "button.css"

        class Kwargs:
            theme: str = "default"

        def get_css_data(self, args, kwargs: Kwargs, slots, context):
            themes = {
                "default": {"bg": "#f0f0f0", "color": "#333"},
                "primary": {"bg": "#0275d8", "color": "#fff"},
                "danger": {"bg": "#d9534f", "color": "#fff"},
            }
            css_vars = themes.get(kwargs.theme, themes["default"])
            return css_vars
    ```



    ```css
    /* button.css */
    .button {
      background-color: var(--bg);
      color: var(--color);
    }
    ```


- **Component tree navigation: `parent`, `root`, and `ancestors` properties.**

    Components can now access their parent component, root component, and all ancestors
    during rendering. These properties are part of the Render API and allow components
    to navigate the component tree.

    - `Component.parent` - Returns the parent component instance, or `None` if this is the root component.
    - `Component.root` - Returns the root component instance (top-most ancestor), or `self` if this is the root.
    - `Component.ancestors` - Returns an iterator that yields all ancestor component instances, walking up the tree.

    **Example:**


    ```python
    class Theme(Component):
        ...

    class Table(Component):
        def get_template_data(self, args, kwargs, slots, context):
            if self.parent is not None:
                # This component is nested in another component
                # Access parent's data
                if isinstance(self.parent, Theme):
                    theme_color = self.parent.kwargs.get("color", "default")
                    ...
    ```


    See [#1252](https://github.com/django-components/django-components/issues/1252)

- **New `on_extension_created` hook for extensions.**

    New hook is called when the extension class is instantiated during Django startup.

    Use this hook to perform initialization logic that needs to run at server startup.

    **Example:**


    ```python
    from django_components.extension import ComponentExtension, OnExtensionCreatedContext

    class MyExtension(ComponentExtension):
        name = "my_extension"

        def on_extension_created(self, ctx: OnExtensionCreatedContext) -> None:
            # Perform initialization logic
            import_my_modules()
            setup_global_state()
    ```


#### Fix

- Add missing export of `OnCssLoadedContext` and `OnJsLoadedContext`

- Fixed bug where Python expressions in template tags were not evaluated correctly
  when the expression was on a separate line.

    See [#1255](https://github.com/django-components/django-components/issues/1255)


    ```django
    {% component "ListItem"
      attrs:class="
        {{ module_classes }}
        project-nav--item
        w-full mt-0 shadow
      "
    / %}
    ```


- Fixed bug where multiple attributes with the same name (e.g., `class`) were not being merged
  correctly in `{% html_attrs %}`.

    See [#1281](https://github.com/django-components/django-components/issues/1281)

    Previously, when using duplicate `class` or `style` attributes with both variables and
    literals, only the first value was used. Now all values are properly merged:


    ```django
    {% html_attrs attrs
      class=btn_class
      class="inline-flex w-full text-sm font-semibold"
    %}
    ```


    Both `btn_class` and the literal string are now merged together.

- Fixed bug when `{% component %}` is used inside a `{% block %}` tag with `{% extends %}`,
  causing context processor data to be duplicated and shadowed. Components now reuse context
  processor data from `RequestContext` when Django has already run `bind_template()`.

    See [#1569](https://github.com/django-components/django-components/issues/1569)

- Fixed occasional `RuntimeError: Template not patched` multithreading / concurrency issue. When django-components receives an unpatched `Template` instance, it now
  logs a warning and patches the template class on-the-fly instead of raising.

    See [#1571](https://github.com/django-components/django-components/issues/1571)