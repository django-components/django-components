Your components can be rendered either within your Django templates, or directly in Python code.

## Overview

Django Components provides three main methods to render components:

- [`{% component %}` tag](#component-tag) - Renders the component within your Django templates
- [`Component.render()` method](#render-method) - Renders the component to a string
- [`Component.render_to_response()` method](#render-to-response-method) - Renders the component and wraps it in an HTTP response

## `{% component %}` tag

Use the [`{% component %}`](../../../reference/template_tags#component) tag to render a component within your Django templates.

The [`{% component %}`](../../../reference/template_tags#component) tag takes:

- Component's registered name as the first positional argument,
- Followed by any number of positional and keyword arguments.

```django
{% load component_tags %}
<div>
  {% component "button" name="John" job="Developer" / %}
</div>
```

To pass in slots content, you can insert [`{% fill %}`](../../../reference/template_tags#fill) tags,
directly within the [`{% component %}`](../../../reference/template_tags#component) tag to "fill" the slots:

```django
{% component "my_table" rows=rows headers=headers %}
    {% fill "pagination" %}
      < 1 | 2 | 3 >
    {% endfill %}
{% endcomponent %}
```

You can even nest [`{% fill %}`](../../../reference/template_tags#fill) tags within
[`{% if %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#if),
[`{% for %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#for)
and other tags:

```django
{% component "my_table" rows=rows headers=headers %}
    {% if rows %}
        {% fill "pagination" %}
            < 1 | 2 | 3 >
        {% endfill %}
    {% endif %}
{% endcomponent %}
```

!!! info "Omitting the `component` keyword"

    If you would like to omit the `component` keyword, and simply refer to your
    components by their registered names:

    ```django
    {% button name="John" job="Developer" / %}
    ```

    You can do so by setting the "shorthand" [Tag formatter](../../advanced/tag_formatters) in the settings:

    ```python
    # settings.py
    COMPONENTS = {
        "tag_formatter": "django_components.component_shorthand_formatter",
    }
    ```

!!! info "Extended template tag syntax"

    Unlike regular Django template tags, django-components' tags offer extra features like
    defining literal lists and dicts, and more. Read more about [Template tag syntax](../template_tag_syntax).

### Registering components

For a component to be renderable with the [`{% component %}`](../../../reference/template_tags#component) tag, it must be first registered with the [`@register()`](../../../reference/api/#django_components.register) decorator.

For example, if you register a component under the name `"button"`:

```python
from typing import NamedTuple
from django_components import Component, register

@register("button")
class Button(Component):
    template_file = "button.html"

    class Kwargs(NamedTuple):
        name: str
        job: str

    def get_template_data(self, args, kwargs, slots, context):
        ...
```

Then you can render this component by using its registered name `"button"` in the template:

```django
{% component "button" name="John" job="Developer" / %}
```

As you can see above, the args and kwargs passed to the [`{% component %}`](../../../reference/template_tags#component) tag correspond
to the component's input.

For more details, read [Registering components](../../advanced/component_registry).

!!! note "Why do I need to register components?"

    TL;DR: To be able to share components as libraries, and because components can be registed with multiple registries / libraries.

    Django-components allows to [share components across projects](../../advanced/component_libraries).

    However, different projects may use different settings. For example, one project may prefer the "long" format:

    ```django
    {% component "button" name="John" job="Developer" / %}
    ```

    While the other may use the "short" format:

    ```django
    {% button name="John" job="Developer" / %}
    ```

    Both approaches are supported simultaneously for backwards compatibility, because django-components
    started out with only the "long" format.

    To avoid ambiguity, when you use a 3rd party library, it uses the syntax that the author
    had configured for it.

    So when you are creating a component, django-components need to know which registry the component
    belongs to, so it knows which syntax to use.

### Rendering templates

If you have embedded the component in a Django template using the
[`{% component %}`](../../reference/template_tags#component) tag:

```django title="[project root]/templates/my_template.html"
{% load component_tags %}
<div>
  {% component "calendar" date="2024-12-13" / %}
</div>
```

You can simply render the template with the Django's API:

- [`django.shortcuts.render()`](https://docs.djangoproject.com/en/5.2/topics/http/shortcuts/#render)

    ```python
    from django.shortcuts import render

    context = {"date": "2024-12-13"}
    rendered_template = render(request, "my_template.html", context)
    ```

- [`Template.render()`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template.render)

    ```python
    from django.template import Template
    from django.template.loader import get_template

    # Either from a file
    template = get_template("my_template.html")

    # or inlined
    template = Template("""
        {% load component_tags %}
        <div>
            {% component "calendar" date="2024-12-13" / %}
        </div>
    """)

    rendered_template = template.render()
    ```

### Isolating components

By default, components behave similarly to Django's
[`{% include %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#include),
and the template inside the component has access to the variables defined in the outer template.

You can selectively isolate a component, using the `only` flag, so that the inner template
can access only the data that was explicitly passed to it:

```django
{% component "name" positional_arg keyword_arg=value ... only / %}
```

Alternatively, you can set all components to be isolated by default, by setting
[`context_behavior`](../../../reference/settings#django_components.app_settings.ComponentsSettings.context_behavior)
to `"isolated"` in your settings:

```python
# settings.py
COMPONENTS = {
    "context_behavior": "isolated",
}
```

## `render()` method

The [`Component.render()`](../../../reference/api/#django_components.Component.render) method renders a component to a string.

This is the equivalent of calling the [`{% component %}`](../template_tags#component) tag.

```python
from typing import NamedTuple, Optional
from django_components import Component, SlotInput

class Button(Component):
    template_file = "button.html"

    class Args(NamedTuple):
        name: str

    class Kwargs(NamedTuple):
        surname: str
        age: int

    class Slots(NamedTuple):
        footer: Optional[SlotInput] = None

    def get_template_data(self, args, kwargs, slots, context):
        ...

Button.render(
    args=["John"],
    kwargs={
        "surname": "Doe",
        "age": 30,
    },
    slots={
        "footer": "i AM A SLOT",
    },
)
```

[`Component.render()`](../../../reference/api/#django_components.Component.render) accepts the following arguments:

- `args` - Positional arguments to pass to the component (as a list or tuple)
- `kwargs` - Keyword arguments to pass to the component (as a dictionary)
- `slots` - Slot content to pass to the component (as a dictionary)
- `context` - Django context for rendering (can be a dictionary or a `Context` object)
- `deps_strategy` - [Dependencies rendering strategy](#dependencies-rendering) (default: `"document"`)
- `request` - [HTTP request object](../http_request), used for context processors (optional)
- `escape_slots_content` - Whether to HTML-escape slot content (default: `True`)

All arguments are optional. If not provided, they default to empty values or sensible defaults.

See the API reference for [`Component.render()`](../../../reference/api/#django_components.Component.render)
for more details on the arguments.

## `render_to_response()` method

The [`Component.render_to_response()`](../../../reference/api/#django_components.Component.render_to_response)
method works just like [`Component.render()`](../../../reference/api/#django_components.Component.render),
but wraps the result in an HTTP response.

It accepts all the same arguments as [`Component.render()`](../../../reference/api/#django_components.Component.render).

Any extra arguments are passed to the [`HttpResponse`](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpResponse)
constructor.

```python
from typing import NamedTuple, Optional
from django_components import Component, SlotInput

class Button(Component):
    template_file = "button.html"

    class Args(NamedTuple):
        name: str

    class Kwargs(NamedTuple):
        surname: str
        age: int

    class Slots(NamedTuple):
        footer: Optional[SlotInput] = None

    def get_template_data(self, args, kwargs, slots, context):
        ...

# Render the component to an HttpResponse
response = Button.render_to_response(
    args=["John"],
    kwargs={
        "surname": "Doe",
        "age": 30,
    },
    slots={
        "footer": "i AM A SLOT",
    },
    # Additional response arguments
    status=200,
    headers={"X-Custom-Header": "Value"},
)
```

This method is particularly useful in view functions, as you can return the result of the component directly:

```python
def profile_view(request, user_id):
    return Button.render_to_response(
        kwargs={
            "surname": "Doe",
            "age": 30,
        },
        request=request,
    )
```

### Custom response classes

By default, [`Component.render_to_response()`](../../../reference/api/#django_components.Component.render_to_response)
returns a standard Django [`HttpResponse`](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpResponse).

You can customize this by setting the [`response_class`](../../../reference/api/#django_components.Component.response_class)
attribute on your component:

```python
from django.http import HttpResponse
from django_components import Component

class MyHttpResponse(HttpResponse):
    ...

class MyComponent(Component):
    response_class = MyHttpResponse

response = MyComponent.render_to_response()
assert isinstance(response, MyHttpResponse)
```

## Dependencies rendering

The rendered HTML may be used in different contexts (browser, email, etc), and each may need different handling of JS and CSS scripts.

[`render()`](../../../reference/api/#django_components.Component.render) and [`render_to_response()`](../../../reference/api/#django_components.Component.render_to_response)
accept a `deps_strategy` parameter, which controls where and how the JS / CSS are inserted into the HTML.

The `deps_strategy` parameter is ultimately passed to [`render_dependencies()`](../../../reference/api/#django_components.render_dependencies).

Learn more about [Rendering JS / CSS](../../advanced/rendering_js_css).

There are six dependencies rendering strategies:

- [`document`](../../advanced/rendering_js_css#document) (default)
    - Smartly inserts JS / CSS into placeholders ([`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies)) or into `<head>` and `<body>` tags.
    - Inserts extra script to allow `fragment` components to work.
    - Assumes the HTML will be rendered in a JS-enabled browser.
- [`fragment`](../../advanced/rendering_js_css#fragment)
    - A lightweight HTML fragment to be inserted into a document with AJAX.
    - Assumes the page was already rendered with `"document"` strategy.
    - No JS / CSS included.
- [`simple`](../../advanced/rendering_js_css#simple)
    - Smartly insert JS / CSS into placeholders ([`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies)) or into `<head>` and `<body>` tags.
    - No extra script loaded.
- [`prepend`](../../advanced/rendering_js_css#prepend)
    - Insert JS / CSS before the rendered HTML.
    - Ignores the placeholders ([`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies)) and any `<head>`/`<body>` HTML tags.
    - No extra script loaded.
- [`append`](../../advanced/rendering_js_css#append)
    - Insert JS / CSS after the rendered HTML.
    - Ignores the placeholders ([`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies)) and any `<head>`/`<body>` HTML tags.
    - No extra script loaded.
- [`ignore`](../../advanced/rendering_js_css#ignore)
    - HTML is left as-is. You can still process it with a different strategy later with
      [`render_dependencies()`](../../../reference/api/#django_components.render_dependencies).
    - Used for inserting rendered HTML into other components.

!!! info

    You can use the `"prepend"` and `"append"` strategies to force to output JS / CSS for components
    that don't have neither the placeholders like [`{% component_js_dependencies %}`](../../../reference/template_tags#component_js_dependencies), nor any `<head>`/`<body>` HTML tags:

    ```py
    rendered = Calendar.render_to_response(
        request=request,
        kwargs={
            "date": request.GET.get("date", ""),
        },
        deps_strategy="append",
    )
    ```

    Renders something like this:

    ```html
    <!-- Calendar component -->
    <div class="calendar">
        ...
    </div>
    <!-- Appended JS / CSS -->
    <script src="..."></script>
    <link href="..."></link>
    ```

## Passing context

The [`render()`](../../../reference/api/#django_components.Component.render) and [`render_to_response()`](../../../reference/api/#django_components.Component.render_to_response) methods accept an optional `context` argument.
This sets the context within which the component is rendered.

When a component is rendered within a template with the [`{% component %}`](../../../reference/template_tags#component)
tag, this will be automatically set to the
[Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
instance that is used for rendering the template.

When you call [`Component.render()`](../../../reference/api/#django_components.Component.render) directly from Python,
there is no context object, so you can ignore this input most of the time.
Instead, use `args`, `kwargs`, and `slots` to pass data to the component.

However, you can pass
[`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
to the `context` argument, so that the component will gain access to the request object and will use
[context processors](https://docs.djangoproject.com/en/5.2/ref/templates/api/#using-requestcontext).
Read more on [Working with HTTP requests](../http_request).

```py
Button.render(
    context=RequestContext(request),
)
```

For advanced use cases, you can use `context` argument to "pre-render" the component in Python, and then
pass the rendered output as plain string to the template. With this, the inner component is rendered as if
it was within the template with [`{% component %}`](../../../reference/template_tags#component).

```py
class Button(Component):
    def render(self, context, template):
        # Pass `context` to Icon component so it is rendered
        # as if nested within Button.
        icon = Icon.render(
            context=context,
            args=["icon-name"],
            deps_strategy="ignore",
        )
        # Update context with icon
        with context.update({"icon": icon}):
            return template.render(context)
```

!!! warning

    Whether the variables defined in `context` are actually available in the template depends on the
    [context behavior mode](../../../reference/settings#django_components.app_settings.ComponentsSettings.context_behavior):

    - In `"django"` context behavior mode, the template will have access to the keys of this context.

    - In `"isolated"` context behavior mode, the template will NOT have access to this context,
        and data MUST be passed via component's args and kwargs.

    Therefore, it's **strongly recommended** to not rely on defining variables on the context object,
    but instead passing them through as `args` and `kwargs`

    ❌ Don't do this:

    ```python
    html = ProfileCard.render(
        context={"name": "John"},
    )
    ```

    ✅ Do this:

    ```python
    html = ProfileCard.render(
        kwargs={"name": "John"},
    )
    ```

## Typing render methods

Neither [`Component.render()`](../../../reference/api/#django_components.Component.render)
nor [`Component.render_to_response()`](../../../reference/api/#django_components.Component.render_to_response)
are typed, due to limitations of Python's type system.

To add type hints, you can wrap the inputs
in component's [`Args`](../../../reference/api/#django_components.Component.Args),
[`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
and [`Slots`](../../../reference/api/#django_components.Component.Slots) classes.

Read more on [Typing and validation](../../advanced/typing_and_validation).

```python
from typing import NamedTuple, Optional
from django_components import Component, Slot, SlotInput

# Define the component with the types
class Button(Component):
    class Args(NamedTuple):
        name: str

    class Kwargs(NamedTuple):
        surname: str
        age: int

    class Slots(NamedTuple):
        my_slot: Optional[SlotInput] = None
        footer: SlotInput

# Add type hints to the render call
Button.render(
    args=Button.Args(
        name="John",
    ),
    kwargs=Button.Kwargs(
        surname="Doe",
        age=30,
    ),
    slots=Button.Slots(
        footer=Slot(lambda ctx: "Click me!"),
    ),
)
```

## Components as input

django_components makes it possible to compose components in a "React-like" way,
where you can render one component and use its output as input to another component:

```python
from django.utils.safestring import mark_safe

# Render the inner component
inner_html = InnerComponent.render(
    kwargs={"some_data": "value"},
    deps_strategy="ignore",  # Important for nesting!
)

# Use inner component's output in the outer component
outer_html = OuterComponent.render(
    kwargs={
        "content": mark_safe(inner_html),  # Mark as safe to prevent escaping
    },
)
```

The key here is setting [`deps_strategy="ignore"`](../../advanced/rendering_js_css#ignore) for the inner component. This prevents duplicate
rendering of JS / CSS dependencies when the outer component is rendered.

When `deps_strategy="ignore"`:

- No JS or CSS dependencies will be added to the output HTML
- The component's content is rendered as-is
- The outer component will take care of including all needed dependencies

Read more about [Rendering JS / CSS](../../advanced/rendering_js_css).

## Dynamic components

Django components defines a special "dynamic" component ([`DynamicComponent`](../../../reference/components#django_components.components.dynamic.DynamicComponent)).

Normally, you have to hard-code the component name in the template:

```django
{% component "button" / %}
```

The dynamic component allows you to dynamically render any component based on the `is` kwarg. This is similar
to [Vue's dynamic components](https://vuejs.org/guide/essentials/component-basics#dynamic-components) (`<component :is>`).

```django
{% component "dynamic" is=table_comp data=table_data headers=table_headers %}
    {% fill "pagination" %}
        {% component "pagination" / %}
    {% endfill %}
{% endcomponent %}
```

The args, kwargs, and slot fills are all passed down to the underlying component.

As with other components, the dynamic component can be rendered from Python:

```py
from django_components import DynamicComponent

DynamicComponent.render(
    kwargs={
        "is": table_comp,
        "data": table_data,
        "headers": table_headers,
    },
    slots={
        "pagination": PaginationComponent.render(
            deps_strategy="ignore",
        ),
    },
)
```

### Dynamic component name

By default, the dynamic component is registered under the name `"dynamic"`. In case of a conflict,
you can set the
[`COMPONENTS.dynamic_component_name`](../../../reference/settings#django_components.app_settings.ComponentsSettings.dynamic_component_name)
setting to change the name used for the dynamic components.

```py
# settings.py
COMPONENTS = ComponentsSettings(
    dynamic_component_name="my_dynamic",
)
```

After which you will be able to use the dynamic component with the new name:

```django
{% component "my_dynamic" is=table_comp data=table_data headers=table_headers %}
    {% fill "pagination" %}
        {% component "pagination" / %}
    {% endfill %}
{% endcomponent %}
```

## HTML fragments

Django-components provides a seamless integration with HTML fragments with AJAX ([HTML over the wire](https://hotwired.dev/)),
whether you're using jQuery, HTMX, AlpineJS, vanilla JavaScript, or other.

This is achieved by the combination of the [`"document"`](../../advanced/rendering_js_css#document)
and [`"fragment"`](../../advanced/rendering_js_css#fragment) dependencies rendering strategies.

Read more about [HTML fragments](../../advanced/html_fragments) and [Rendering JS / CSS](../../advanced/rendering_js_css).
