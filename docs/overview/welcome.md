<img src="https://raw.githubusercontent.com/django-components/django-components/master/assets/logo/logo-black-on-white.svg" alt="django-components" style="max-width: 100%; background: white; color: black;">

[![PyPI - Version](https://img.shields.io/pypi/v/django-components)](https://pypi.org/project/django-components/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-components)](https://pypi.org/project/django-components/) [![PyPI - License](https://img.shields.io/pypi/l/django-components)](https://github.com/django-components/django-components/blob/master/LICENSE/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/django-components)](https://pypistats.org/packages/django-components) [![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/django-components/django-components/tests.yml)](https://github.com/django-components/django-components/actions/workflows/tests.yml) [![asv](https://img.shields.io/badge/benchmarked%20by-asv-blue.svg?style=flat)](/django-components/latest/benchmarks/)

`django-components` combines Django's templating system with the modularity seen
in modern frontend frameworks like Vue or React.

With `django-components` you can support Django projects small and large without leaving the Django ecosystem.

## Sponsors

<p align="center">
  <a href="https://www.ohne-makler.net/?ref=django-components" target="_blank"
  title="Ohne-makler: Sell and rent real estate without an agent"><img
  src="https://raw.githubusercontent.com/django-components/django-components/master/assets/sponsors/sponsor-ohne-makler.png" height="120" width="50%"
  /></a>
</p>

## Quickstart

A component in django-components can be as simple as a Django template and Python code to declare the component:

```htmldjango title="components/calendar/calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

```py title="components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
```

Or a combination of Django template, Python, CSS, and Javascript:

```htmldjango title="components/calendar/calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

```css title="components/calendar/calendar.css"
.calendar {
  width: 200px;
  background: pink;
}
```

```js title="components/calendar/calendar.js"
document.querySelector(".calendar").onclick = () => {
  alert("Clicked calendar!");
};
```

```py title="components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    js_file = "calendar.js"
    css_file = "calendar.css"

    def get_template_data(self, args, kwargs, slots, context):
        return {"date": kwargs["date"]}
```

Use the component like this:

```htmldjango
{% component "calendar" date="2024-11-06" %}{% endcomponent %}
```

And this is what gets rendered:

```html
<div class="calendar-component">
  Today's date is <span>2024-11-06</span>
</div>
```

Read on to learn about all the exciting details and configuration possibilities!

(If you instead prefer to jump right into the code, [check out the example project](https://github.com/django-components/django-components/tree/master/sampleproject))

## Features

### Modern and modular UI

- Create self-contained, reusable UI elements.
- Each component can include its own HTML, CSS, and JS, or additional third-party JS and CSS.
- HTML, CSS, and JS can be defined on the component class, or loaded from files.

```djc_py
from django_components import Component

@register("calendar")
class Calendar(Component):
    template = """
        <div class="calendar">
            Today's date is
            <span>{{ date }}</span>
        </div>
    """

    css = """
        .calendar {
            width: 200px;
            background: pink;
        }
    """

    js = """
        document.querySelector(".calendar")
            .addEventListener("click", () => {
                alert("Clicked calendar!");
            });
    """

    # Additional JS and CSS
    class Media:
        js = ["https://cdn.jsdelivr.net/npm/htmx.org@2/dist/htmx.min.js"]
        css = ["bootstrap/dist/css/bootstrap.min.css"]

    # Variables available in the template
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs["date"]
        }
```

### Composition with slots

- Render components inside templates with
  [`{% component %}`](https://django-components.github.io/django-components/latest/reference/template_tags#component) tag.
- Compose them with [`{% slot %}`](https://django-components.github.io/django-components/latest/reference/template_tags#slot)
  and [`{% fill %}`](https://django-components.github.io/django-components/latest/reference/template_tags#fill) tags.
- Vue-like slot system, including [scoped slots](https://django-components.github.io/django-components/latest/concepts/fundamentals/slots/#scoped-slots).

```htmldjango
{% component "Layout"
    bookmarks=bookmarks
    breadcrumbs=breadcrumbs
%}
    {% fill "header" %}
        <div class="flex justify-between gap-x-12">
            <div class="prose">
                <h3>{{ project.name }}</h3>
            </div>
            <div class="font-semibold text-gray-500">
                {{ project.start_date }} - {{ project.end_date }}
            </div>
        </div>
    {% endfill %}

    {# Access data passed to `{% slot %}` with `data` #}
    {% fill "tabs" data="tabs_data" %}
        {% component "TabItem" header="Project Info" %}
            {% component "ProjectInfo"
                project=project
                project_tags=project_tags
                attrs:class="py-5"
                attrs:width=tabs_data.width
            / %}
        {% endcomponent %}
    {% endfill %}
{% endcomponent %}
```

### Extended template tags

`django-components` is designed for flexibility, making working with templates a breeze.

It extends Django's template tags syntax with:

<!-- TODO - Document literal lists and dictionaries -->
- Literal lists and dictionaries in the template
- [Self-closing tags](https://django-components.github.io/django-components/latest/concepts/fundamentals/template_tag_syntax#self-closing-tags) `{% mytag / %}`
- [Multi-line template tags](https://django-components.github.io/django-components/latest/concepts/fundamentals/template_tag_syntax#multiline-tags)
- [Spread operator](https://django-components.github.io/django-components/latest/concepts/fundamentals/template_tag_syntax#spread-operator) `...` to dynamically pass args or kwargs into the template tag
- [Template tags inside literal strings](https://django-components.github.io/django-components/latest/concepts/fundamentals/template_tag_syntax#template-tags-inside-literal-strings) like `"{{ first_name }} {{ last_name }}"`
- [Pass dictonaries by their key-value pairs](https://django-components.github.io/django-components/latest/concepts/fundamentals/template_tag_syntax#pass-dictonary-by-its-key-value-pairs) `attr:key=val`

```htmldjango
{% component "table"
    ...default_attrs
    title="Friend list for {{ user.name }}"
    headers=["Name", "Age", "Email"]
    data=[
        {
            "name": "John"|upper,
            "age": 30|add:1,
            "email": "john@example.com",
            "hobbies": ["reading"],
        },
        {
            "name": "Jane"|upper,
            "age": 25|add:1,
            "email": "jane@example.com",
            "hobbies": ["reading", "coding"],
        },
    ],
    attrs:class="py-4 ma-2 border-2 border-gray-300 rounded-md"
/ %}
```

You too can define template tags with these features by using
[`@template_tag()`](https://django-components.github.io/django-components/latest/reference/api/#django_components.template_tag)
or [`BaseNode`](https://django-components.github.io/django-components/latest/reference/api/#django_components.BaseNode).

Read more on [Custom template tags](https://django-components.github.io/django-components/latest/concepts/advanced/template_tags/).

### Full programmatic access

When you render a component, you can access everything about the component:

- Component input: [args, kwargs, slots and context](https://django-components.github.io/django-components/latest/concepts/fundamentals/render_api/#component-inputs)
- Component's template, CSS and JS
- Django's [context processors](https://django-components.github.io/django-components/latest/concepts/fundamentals/render_api/#request-and-context-processors)
- Unique [render ID](https://django-components.github.io/django-components/latest/concepts/fundamentals/render_api/#component-id)

```python
class Table(Component):
    js_file = "table.js"
    css_file = "table.css"

    template = """
        <div class="table">
            <span>{{ variable }}</span>
        </div>
    """

    def get_template_data(self, args, kwargs, slots, context):
        # Access component's ID
        assert self.id == "djc1A2b3c"

        # Access component's inputs and slots
        assert self.args == [123, "str"]
        assert self.kwargs == {"variable": "test", "another": 1}
        footer_slot = self.slots["footer"]
        some_var = self.context["some_var"]

        # Access the request object and Django's context processors, if available
        assert self.request.GET == {"query": "something"}
        assert self.context_processors_data['user'].username == "admin"

        return {
            "variable": kwargs["variable"],
        }

# Access component's HTML / JS / CSS
Table.template
Table.js
Table.css

# Render the component
rendered = Table.render(
    kwargs={"variable": "test", "another": 1},
    args=(123, "str"),
    slots={"footer": "MY_FOOTER"},
)
```

### Granular HTML attributes

Use the [`{% html_attrs %}`](https://django-components.github.io/django-components/latest/concepts/fundamentals/html_attributes/) template tag to render HTML attributes.

It supports:

- Defining attributes as whole dictionaries or keyword arguments
- Merging attributes from multiple sources
- Boolean attributes
- Appending attributes
- Removing attributes
- Defining default attributes

```django
<div
    {% html_attrs
        attrs
        defaults:class="default-class"
        class="extra-class"
    %}
>
```

[`{% html_attrs %}`](https://django-components.github.io/django-components/latest/concepts/fundamentals/html_attributes/) offers a Vue-like granular control for
[`class`](https://django-components.github.io/django-components/latest/concepts/fundamentals/html_attributes/#merging-class-attributes)
and [`style`](https://django-components.github.io/django-components/latest/concepts/fundamentals/html_attributes/#merging-style-attributes)
HTML attributes,
where you can use a dictionary to manage each class name or style property separately.

```django
{% html_attrs
    class="foo bar"
    class={
        "baz": True,
        "foo": False,
    }
    class="extra"
%}
```

```django
{% html_attrs
    style="text-align: center; background-color: blue;"
    style={
        "background-color": "green",
        "color": None,
        "width": False,
    }
    style="position: absolute; height: 12px;"
%}
```

Read more about [HTML attributes](https://django-components.github.io/django-components/latest/concepts/fundamentals/html_attributes/).

### HTML fragment support

`django-components` makes integration with HTMX, AlpineJS or jQuery easy by allowing components to be rendered as HTML fragments:

- Components's JS and CSS files are loaded automatically when the fragment is inserted into the DOM.

- Components can be [exposed as Django Views](https://django-components.github.io/django-components/latest/concepts/fundamentals/component_views_urls/) with `get()`, `post()`, `put()`, `patch()`, `delete()` methods

- Automatically create an endpoint for a component with [`Component.View.public`](https://django-components.github.io/django-components/latest/concepts/fundamentals/component_views_urls/#register-urls-automatically)

```py
# components/calendar/calendar.py
@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"

    class View:
        # Define handlers
        def get(self, request, *args, **kwargs):
            page = request.GET.get("page", 1)
            return Calendar.render_to_response(
                request=request,
                kwargs={
                    "page": page,
                },
            )

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "page": kwargs["page"],
        }

# Get auto-generated URL for the component
url = get_component_url(Calendar)

# Or define explicit URL in urls.py
path("calendar/", Calendar.as_view())
```

### Provide / Inject

`django-components` supports the provide / inject pattern, similarly to React's [Context Providers](https://react.dev/learn/passing-data-deeply-with-context) or Vue's [provide / inject](https://vuejs.org/guide/components/provide-inject):

- Use the [`{% provide %}`](https://django-components.github.io/django-components/latest/reference/template_tags/#provide) tag to provide data to the component tree
- Use the [`Component.inject()`](https://django-components.github.io/django-components/latest/reference/api/#django_components.Component.inject) method to inject data into the component

Read more about [Provide / Inject](https://django-components.github.io/django-components/latest/concepts/advanced/provide_inject).

```django
<body>
    {% provide "theme" variant="light" %}
        {% component "header" / %}
    {% endprovide %}
</body>
```

```djc_py
@register("header")
class Header(Component):
    template = "..."

    def get_template_data(self, args, kwargs, slots, context):
        theme = self.inject("theme").variant
        return {
            "theme": theme,
        }
```

### Input validation and static type hints

Avoid needless errors with [type hints and runtime input validation](https://django-components.github.io/django-components/latest/concepts/fundamentals/typing_and_validation/).

To opt-in to input validation, define types for component's args, kwargs, slots:

```py
from typing import NamedTuple, Optional
from django.template import Context
from django_components import Component, Slot, SlotInput

class Button(Component):
    class Args(NamedTuple):
        size: int
        text: str

    class Kwargs(NamedTuple):
        variable: str
        another: int
        maybe_var: Optional[int] = None  # May be omitted

    class Slots(NamedTuple):
        my_slot: Optional[SlotInput] = None
        another_slot: SlotInput

    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        args.size  # int
        kwargs.variable  # str
        slots.my_slot  # Slot[MySlotData]
```

To have type hints when calling
[`Button.render()`](https://django-components.github.io/django-components/latest/reference/api/#django_components.Component.render) or
[`Button.render_to_response()`](https://django-components.github.io/django-components/latest/reference/api/#django_components.Component.render_to_response),
wrap the inputs in their respective `Args`, `Kwargs`, and `Slots` classes:

```py
Button.render(
    # Error: First arg must be `int`, got `float`
    args=Button.Args(
        size=1.25,
        text="abc",
    ),
    # Error: Key "another" is missing
    kwargs=Button.Kwargs(
        variable="text",
    ),
)
```

### Extensions

Django-components functionality can be extended with [Extensions](https://django-components.github.io/django-components/latest/concepts/advanced/extensions/).
Extensions allow for powerful customization and integrations. They can:

- Tap into lifecycle events, such as when a component is created, deleted, or registered
- Add new attributes and methods to the components
- Add custom CLI commands
- Add custom URLs

Some of the extensions include:

- [Component caching](https://github.com/django-components/django-components/blob/master/src/django_components/extensions/cache.py)
- [Django View integration](https://github.com/django-components/django-components/blob/master/src/django_components/extensions/view.py)
- [Component defaults](https://github.com/django-components/django-components/blob/master/src/django_components/extensions/defaults.py)
- [Pydantic integration (input validation)](https://github.com/django-components/djc-ext-pydantic)

Some of the planned extensions include:

- AlpineJS integration
- Storybook integration
- Component-level benchmarking with asv

### Caching

- [Components can be cached](https://django-components.github.io/django-components/latest/concepts/advanced/component_caching/) using Django's cache framework.
- Caching rules can be configured on a per-component basis.
- Components are cached based on their input. Or you can write custom caching logic.

```py
from django_components import Component

class MyComponent(Component):
    class Cache:
        enabled = True
        ttl = 60 * 60 * 24  # 1 day

        def hash(self, *args, **kwargs):
            return hash(f"{json.dumps(args)}:{json.dumps(kwargs)}")
```

### Simple testing

- Write tests for components with [`@djc_test`](https://django-components.github.io/django-components/latest/concepts/advanced/testing/) decorator.
- The decorator manages global state, ensuring that tests don't leak.
- If using `pytest`, the decorator allows you to parametrize Django or Components settings.
- The decorator also serves as a stand-in for Django's [`@override_settings`](https://docs.djangoproject.com/en/5.2/topics/testing/tools/#django.test.override_settings).

```python
from django_components.testing import djc_test

from components.my_table import MyTable

@djc_test
def test_my_table():
    rendered = MyTable.render(
        kwargs={
            "title": "My table",
        },
    )
    assert rendered == "<table>My table</table>"
```

### Debugging features

- **Visual component inspection**: Highlight components and slots directly in your browser.
- **Detailed tracing logs to supply AI-agents with context**: The logs include component and slot names and IDs, and their position in the tree.

<div style="text-align: center;">
<img src="https://github.com/django-components/django-components/blob/master/docs/images/debug-highlight-slots.png?raw=true" alt="Component debugging visualization showing slot highlighting" width="500" style="margin: auto;">
</div>

### Sharing components

- Install and use third-party components from PyPI
- Or publish your own "component registry"
- Highly customizable - Choose how the components are called in the template (and more):

    ```htmldjango
    {% component "calendar" date="2024-11-06" %}
    {% endcomponent %}

    {% calendar date="2024-11-06" %}
    {% endcalendar %}
    ```
