### JS and CSS output locations

If:

1. Your components use JS and CSS via any of:
    - [`Component.css`](#TODO)
    - [`Component.js`](#TODO)
    - [`Component.Media.css`](#TODO)
    - [`Component.Media.js`](#TODO)
2. And you use the [`ComponentDependencyMiddleware`](#TODO) middleware

Then, by default, the components' JS and CSS will be automatically inserted into the HTML:

- CSS styles will be inserted at the end of the `<head>`
- JS scripts will be inserted at the end of the `<body>`

If you want to place the dependencies elsewhere in the HTML, you can override
the locations by inserting following Django template tags:

- [`{% component_js_dependencies %}`](#TODO) - Set new location(s) for JS scripts
- [`{% component_css_dependencies %}`](#TODO) - Set new location(s) for CSS styles

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

Then the JS from `MyButton.js` and `MyButton.Media.js` will be rendered at the default place,
or in [`{% component_js_dependencies %}`](#TODO).

And the CSS from `MyButton.css` and `MyButton.Media.css` will be rendered at the default place,
or in [`{% component_css_dependencies %}`](#TODO).

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

### Setting up the middleware

[`ComponentDependencyMiddleware`](#TODO) is a Django [middleware](https://docs.djangoproject.com/en/5.1/topics/http/middleware/)
designed to manage and inject CSS / JS dependencies of rendered components dynamically.
It ensures that only the necessary stylesheets and scripts are loaded
in your HTML responses, based on the components used in your Django templates.

To set it up, add the middleware to your [`MIDDLEWARE`](https://docs.djangoproject.com/en/5.1/ref/settings/#std-setting-MIDDLEWARE)
in `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware classes ...
    'django_components.middleware.ComponentDependencyMiddleware'
    # ... other middleware classes ...
]
```

### `render_dependencies` and rendering JS / CSS without the middleware

For most scenarios, using the [`ComponentDependencyMiddleware`](#TODO) middleware will be just fine.

However, this section is for you if you want to:

- Render HTML that will NOT be sent as a server response
- Insert pre-rendered HTML into another component
- Render HTML fragments (partials)

Every time there is an HTML string that has parts which were rendered using components,
and any of those components has JS / CSS, then this HTML string MUST be processed with [`render_dependencies()`](#TODO).

It is actually [`render_dependencies()`](#TODO) that finds all used components in the HTML string,
and inserts the component's JS and CSS into `{% component_dependencies %}` tags, or at the default locations.

#### Render JS / CSS without the middleware

The truth is that the [`ComponentDependencyMiddleware`](#TODO) middleware just calls [`render_dependencies()`](#TODO),
passing in the HTML content. So if you render a template that contained [`{% component %}`](#TODO) tags,
you MUST pass the result through [`render_dependencies()`](#TODO). And the middleware is just one of the options.

Here is how you can achieve the same, without the middleware, using [`render_dependencies()`](#TODO):

```python
from django.template.base import Template
from django.template.context import Context
from django_component import render_dependencies

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

rendered = template.render(Context())
rendered = render_dependencies(rendered)
```

Same applies if you render a template using Django's [`django.shortcuts.render`](https://docs.djangoproject.com/en/5.1/topics/http/shortcuts/#render):

```python
from django.shortcuts import render

def my_view(request):
    rendered = render(request, "pages/home.html")
    rendered = render_dependencies(rendered)
    return rendered
```

Alternatively, when you render HTML with [`Component.render()`](#TODO)
or [`Component.render_to_response()`](#TODO),
these, by default, call [`render_dependencies()`](#TODO) for you, so you don't have to:

```python
from django_components import Component

class MyButton(Component):
    ...

# No need to call `render_dependencies()`
rendered = MyButton.render()
```

#### Inserting pre-rendered HTML into another component

In previous section we've shown that [`render_dependencies()`](#TODO) does NOT need to be called
when you render a component via [`Component.render()`](#TODO).

API of django_components makes it possible to compose components in a "React-like" way,
where we pre-render a piece of HTML and then insert it into a larger structure.

To do this, you must add [`render_dependencies=False`](#TODO) to the nested components:

```python
card_actions = CardActions.render(
    kwargs={"editable": editable},
    render_dependencies=False,
)

card = Card.render(
    slots={"actions": card_actions},
    render_dependencies=False,
)

page = MyPage.render(
    slots={"card": card},
)
```

Why is `render_dependencies=False` required?

This is a technical limitation of the current implementation.

As mentioned earlier, each time we call [`Component.render()`](#TODO),
we also call [`render_dependencies()`](#TODO).

However, there is a problem here - When we call [`render_dependencies()`](#TODO)
inside [`CardActions.render()`](#TODO),
we extract and REMOVE the info on components' JS and CSS from the HTML. But the template
of `CardActions` contains no `{% component_depedencies %}` tags, and nor `<head>` nor `<body>` HTML tags.
So the component's JS and CSS will NOT be inserted, and will be lost.

To work around this, you must set [`render_dependencies=False`](#TODO) when rendering pieces of HTML
with [`Component.render()`](#TODO) and inserting them into larger structures.

#### Summary

1. Every time you render HTML that contained components, you have to call [`render_dependencies()`](#TODO)
   on the rendered output.
2. There are several ways to call [`render_dependencies()`](#TODO):
    - Using the [`ComponentDependencyMiddleware`](#TODO) middleware
    - Rendering the HTML by calling [`Component.render()`](#TODO) with `render_dependencies=True` (default)
    - Rendering the HTML by calling [`Component.render_to_response()`](#TODO) (always renders dependencies)
    - Directly passing rendered HTML to [`render_dependencies()`](#TODO)
3. If you pre-render one component to pass it into another, the pre-rendered component must be rendered with
   [`render_dependencies=False`](#TODO).
