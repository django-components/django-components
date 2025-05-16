django-components has the most extensive slot system of all the popular Python templating engines.

The slot system is based on [Vue](https://vuejs.org/guide/components/slots.html), and works across both Django templates and Python code.

## What are slots?

Components support something called 'slots'.

When you write a component, you define its template. The template will always be
the same each time you render the component.

However, sometimes you may want to customize the component slightly to change the
content of the component. This is where slots come in.

Slots allow you to insert parts of HTML into the component.
This makes components more reusable and composable.

```django
<div class="calendar-component">
    <div class="header">
        {# This is where the component will insert the content #}
        {% slot "header" / %}
    </div>
</div>
```

## Slot anatomy

Slots consists of two parts:

1. [`{% slot %}`](../../../reference/template_tags#slot) tag - Inside your component you decide where you want to insert the content.
2. [`{% fill %}`](../../../reference/template_tags#fill) tag - In the parent template (outside the component) you decide what content to insert into the slot.
   It "fills" the slot with the specified content.

Let's look at an example:

First, we define the component template. This component contains two slots, `header` and `body`.

```htmldjango
<!-- calendar.html -->
<div class="calendar-component">
    <div class="header">
        {% slot "header" %}
            Calendar header
        {% endslot %}
    </div>
    <div class="body">
        {% slot "body" %}
            Today's date is <span>{{ date }}</span>
        {% endslot %}
    </div>
</div>
```

Next, when using the component, we can insert our own content into the slots. It looks like this:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "body" %}
        Can you believe it's already
        <span>{{ date }}</span>??
    {% endfill %}
{% endcomponent %}
```

Since the `'header'` fill is unspecified, it's [default value](#default-slot) is used.

When rendered, notice that:

- The body is filled with the content we specified,
- The header is still the default value we defined in the component template.

```htmldjango
<div class="calendar-component">
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Can you believe it's already <span>2020-06-06</span>??
    </div>
</div>
```

## Slots overview

### Slot definition

Slots are defined with the [`{% slot %}`](../../../reference/template_tags#slot) tag:

```django
{% slot "name" %}
    Default content
{% endslot %}
```

Single component can have multiple slots:

```django
{% slot "name" %}
    Default content
{% endslot %}

{% slot "other_name" / %}
```

And you can even define the same slot in multiple places:

```django
<div>
    {% slot "name" %}
        First content
    {% endslot %}
</div>
<div>
    {% slot "name" %}
        Second content
    {% endslot %}
</div>
```

!!! info

    If you define the same slot in multiple places, you must mark each slot individually
    when setting `default` or `required` flags, e.g.:

    ```htmldjango
    <div class="calendar-component">
        <div class="header">
            {% slot "image" default required %}Image here{% endslot %}
        </div>
        <div class="body">
            {% slot "image" default required %}Image here{% endslot %}
        </div>
    </div>
    ```

### Slot filling

Fill can be defined with the [`{% fill %}`](../../../reference/template_tags#fill) tag:

```django
{% component "calendar" %}
    {% fill "name" %}
        Filled content
    {% endfill %}
    {% fill "other_name" %}
        Filled content
    {% endfill %}
{% endcomponent %}
```

Or in Python with the [`slots`](../../../reference/api#django_components.Component.render) argument:

```py
Calendar.render(
    slots={
        "name": "Filled content",
        "other_name": "Filled content",
    },
)
```

### Default slot

You can make the syntax shorter by marking the slot as [`default`](../../../reference/template_tags#slot):

```django
{% slot "name" default %}
    Default content
{% endslot %}
```

This allows you to fill the slot directly in the [`{% component %}`](../../../reference/template_tags#component) tag,
omitting the `{% fill %}` tag:

```django
{% component "calendar" %}
    Filled content
{% endcomponent %}
```

To target the default slot in Python, you can use the `"default"` slot name:

```py
Calendar.render(
    slots={"default": "Filled content"},
)
```

!!! info "Accessing default slot in Python"

    Since the default slot is stored under the slot name `default`, you can access the default slot
    in Python under the `"default"` key:

    ```py
    class MyTable(Component):
        def get_template_data(self, args, kwargs, slots, context):
            default_slot = slots["default"]
            return {
                "default_slot": default_slot,
            }
    ```

!!! warning

    Only one [`{% slot %}`](../../../reference/template_tags#slot) can be marked as `default`.
    But you can have multiple slots with the same name all marked as `default`.

    If you define multiple **different** slots as `default`, this will raise an error.

    ❌ Don't do this

    ```django
    {% slot "name" default %}
        Default content
    {% endslot %}
    {% slot "other_name" default %}
        Default content
    {% endslot %}
    ```

    ✅ Do this instead

    ```django
    {% slot "name" default %}
        Default content
    {% endslot %}
    {% slot "name" default %}
        Default content
    {% endslot %}
    ```

!!! warning

    Do NOT combine default fills with explicit named [`{% fill %}`](../../../reference/template_tags#fill) tags.

    The following component template will raise an error when rendered:

    ❌ Don't do this

    ```django
    {% component "calendar" date="2020-06-06" %}
        {% fill "header" %}Totally new header!{% endfill %}
        Can you believe it's already <span>{{ date }}</span>??
    {% endcomponent %}
    ```

    ✅ Do this instead

    ```django
    {% component "calendar" date="2020-06-06" %}
        {% fill "header" %}Totally new header!{% endfill %}
        {% fill "default" %}
            Can you believe it's already <span>{{ date }}</span>??
        {% endfill %}
    {% endcomponent %}
    ```

!!! warning

    You cannot double-fill a slot.

    That is, if both `{% fill "default" %}` and `{% fill "header" %}` point to the same slot,
    this will raise an error when rendered.

### Required slot

You can make the slot required by adding the [`required`](../../../reference/template_tags#slot) keyword:

```django
{% slot "name" required %}
    Default content
{% endslot %}
```

This will raise an error if the slot is not filled.

### Access fills

You can access the fills with the
[`{{ component_vars.slots.<name> }}`](../../../reference/template_vars#slots) template variable:

```django
{% if component_vars.slots.my_slot %}
    <div>
        {% fill "my_slot" %}
            Filled content
        {% endfill %}
    </div>
{% endif %}
```

And in Python with the [`Component.slots`](../../../reference/api#django_components.Component.slots) property:

```py
class Calendar(Component):
    # `get_template_data` receives the `slots` argument directly
    def get_template_data(self, args, kwargs, slots, context):
        if "my_slot" in slots:
            content = "Filled content"
        else:
            content = "Default content"

        return {
            "my_slot": content,
        }

    # But in other methods you can still access the slots with `Component.slots`
    def on_render_before(self, *args, **kwargs):
        if "my_slot" in self.slots:
            # Do something
```

### Dynamic fills

The slot and fill names can be set as variables. This way you can fill slots dynamically:

```django
{% with "body" as slot_name %}
    {% component "calendar" %}
        {% fill slot_name %}
            Filled content
        {% endfill %}
    {% endcomponent %}
{% endwith %}
```

You can even use [`{% if %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#std-templatetag-if)
and [`{% for %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#std-templatetag-for)
tags inside the [`{% component %}`](../../../reference/template_tags#component) tag to fill slots with more control:

```django
{% component "calendar" %}
    {% if condition %}
        {% fill "name" %}
            Filled content
        {% endfill %}
    {% endif %}

    {% for item in items %}
        {% fill item.name %}
            Item: {{ item.value }}
        {% endfill %}
    {% endfor %}
{% endcomponent %}
```

You can also use [`{% with %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#std-templatetag-with)
or even custom tags to generate the fills dynamically:

```django
{% component "calendar" %}
    {% with item.name as name %}
        {% fill name %}
            Item: {{ item.value }}
        {% endfill %}
    {% endwith %}
{% endcomponent %}
```

!!! warning

    If you dynamically generate `{% fill %}` tags, be careful to render text only inside the `{% fill %}` tags.

    Any text rendered outside `{% fill %}` tags will be considered a default fill and will raise an error
    if combined with explicit fills. (See [Default slot](#default-slot))

### Slot data

Sometimes the slots need to access data from the component. Imagine an HTML table component
which has a slot to configure how to render the rows. Each row has a different data, so you need
to pass the data to the slot.

Similarly to [Vue's scoped slots](https://vuejs.org/guide/components/slots#scoped-slots),
you can pass data to the slot, and then access it in the fill.

This consists of two steps:

1. Passing data to [`{% slot %}`](../../../reference/template_tags#slot) tag
2. Accessing data in [`{% fill %}`](../../../reference/template_tags#fill) tag

The data is passed to the slot as extra keyword arguments. Below we set two extra arguments: `first_name` and `job`.

```django
{# Pass data to the slot #}
{% slot "name" first_name="John" job="Developer" %}
    {# Fallback implementation #}
    Name: {{ first_name }}
    Job: {{ job }}
{% endslot %}
```

!!! note

    `name` kwarg is already used for slot name, so you cannot pass it as slot data.

To access the slot's data in the fill, use the [`data`](../../../reference/template_tags#fill) keyword. This sets the name
of the variable that holds the data in the fill:

```django
{# Access data in the fill #}
{% component "profile" %}
    {% fill "name" data="d" %}
        Hello, my name is <h1>{{ d.first_name }}</h1>
        and I'm a <h2>{{ d.job }}</h2>
    {% endfill %}
{% endcomponent %}
```

To access the slot data in Python, use the `data` attribute in [slot functions](#slot-functions).

```py
def my_slot(ctx):
    return f"""
        Hello, my name is <h1>{ctx.data["first_name"]}</h1>
        and I'm a <h2>{ctx.data["job"]}</h2>
    """

Profile.render(
    slots={
        "name": my_slot,
    },
)
```

Slot data can be set also when rendering a slot in Python:

```py
slot = Slot(lambda ctx: f"Hello, {ctx.data['name']}!")

# Render the slot
html = slot({"name": "John"})
```

!!! info

    To access slot data on a [default slot](#default-slot), you have to explictly define the `{% fill %}` tags
    with name `"default"`.

    ```django
    {% component "my_comp" %}
        {% fill "default" data="slot_data" %}
            {{ slot_data.input }}
        {% endfill %}
    {% endcomponent %}
    ```

!!! warning

    You cannot set the `data` attribute and
    [`fallback` attribute](#slot-fallback)
    to the same name. This raises an error:

    ```django
    {% component "my_comp" %}
        {% fill "content" data="slot_var" fallback="slot_var" %}
            {{ slot_var.input }}
        {% endfill %}
    {% endcomponent %}
    ```

### Slot fallback

The content between the `{% slot %}..{% endslot %}` tags is the *fallback* content that
will be rendered if no fill is given for the slot.

```django
{% slot "name" %}
    Hello, my name is {{ name }}  <!-- Fallback content -->
{% endslot %}
```

Sometimes you may want to keep the fallback content, but only wrap it in some other content.

To do so, you can access the fallback content via the [`fallback`](../../../reference/template_tags#fill) kwarg.
This sets the name of the variable that holds the fallback content in the fill:

```django
{% component "profile" %}
    {% fill "name" fallback="fb" %}
        Original content:
        <div>
            {{ fb }}  <!-- fb = 'Hello, my name...' -->
        </div>
    {% endfill %}
{% endcomponent %}
```

To access the fallback content in Python, use the [`fallback`](../../../reference/api#django_components.SlotContext.fallback)
attribute in [slot functions](#slot-functions).

The fallback value is rendered lazily. Coerce the fallback to a string to render it.

```py
def my_slot(ctx):
    # Coerce the fallback to a string
    fallback = str(ctx.fallback)
    return f"Original content: " + fallback

Profile.render(
    slots={
        "name": my_slot,
    },
)
```

Fallback can be set also when rendering a slot in Python:

```py
slot = Slot(lambda ctx: f"Hello, {ctx.data['name']}!")

# Render the slot
html = slot({"name": "John"}, fallback="Hello, world!")
```

!!! info

    To access slot fallback on a [default slot](#default-slot), you have to explictly define the `{% fill %}` tags
    with name `"default"`.

    ```django
    {% component "my_comp" %}
        {% fill "default" fallback="fallback" %}
            {{ fallback }}
        {% endfill %}
    {% endcomponent %}
    ```

!!! warning

    You cannot set the [`data`](#slot-data) attribute and
    `fallback` attribute
    to the same name. This raises an error:

    ```django
    {% component "my_comp" %}
        {% fill "content" data="slot_var" fallback="slot_var" %}
            {{ slot_var.input }}
        {% endfill %}
    {% endcomponent %}
    ```

### Slot functions

In Python code, slot fills can be defined as strings, functions, or
[`Slot`](../../../reference/api#django_components.Slot) instances that wrap the two.
Slot functions have access to slot [`data`](../../../reference/api#django_components.SlotContext.data),
[`fallback`](../../../reference/api#django_components.SlotContext.fallback),
and [`context`](../../../reference/api#django_components.SlotContext.context).

```py
def row_slot(ctx):
    if ctx.data["disabled"]:
        return ctx.fallback

    item = ctx.data["item"]
    if ctx.data["type"] == "table":
        return f"<tr><td>{item}</td></tr>"
    else:
        return f"<li>{item}</li>"

Table.render(
    slots={
        "prepend": "Ice cream selection:",
        "append": Slot("© 2025"),
        "row": row_slot,
        "column_title": Slot(lambda ctx: f"<th>{ctx.data['name']}</th>"),
    },
)
```

Inside the component, these will all be normalized to [`Slot`](../../../reference/api#django_components.Slot) instances:

```py
class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        assert isinstance(slots["prepend"], Slot)
        assert isinstance(slots["row"], Slot)
        assert isinstance(slots["header"], Slot)
        assert isinstance(slots["footer"], Slot)
```

You can render [`Slot`](../../../reference/api#django_components.Slot) instances by simply calling them with data:

```py
class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        prepend_slot = slots["prepend"]
        return {
            "prepend": prepend_slot({"item": "ice cream"}),
        }
```

### Filling slots with functions

You can "fill" slots by passing a string or
[`Slot`](../../../reference/api#django_components.Slot) instance
directly to the [`{% fill %}`](../../../reference/template_tags#fill) tag:

```py
class Table(Component):
    def get_template_data(self, args, kwargs, slots, context):
        def my_fill(ctx):
            return f"Hello, {ctx.data['name']}!"

        return {
            "my_fill": Slot(my_fill),
        }
```

```django
{% component "table" %}
    {% fill "name" body=my_fill / %}
{% endcomponent %}
```

!!! note

    Django automatically executes functions when it comes across them in templates.

    Because of this you MUST wrap the function in [`Slot`](../../../reference/api#django_components.Slot)
    instance to prevent it from being called.

    Read more about Django's [`do_not_call_in_templates`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#variables-and-lookups).

## Slot class

The [`Slot`](../../../reference/api#django_components.Slot) class is a wrapper around a function that can be used to fill a slot.

```py
from django_components import Component, Slot

def footer(ctx):
    return f"Hello, {ctx.data['name']}!"

Table.render(
    slots={
        "footer": Slot(footer),
    },
)
```

Slot class can be instantiated with a function, a string, or from another
[`Slot`](../../../reference/api#django_components.Slot) instance:

```py
slot1 = Slot(lambda ctx: f"Hello, {ctx.data['name']}!")
slot2 = Slot("Hello, world!")
slot3 = Slot(slot1)
```

### Rendering slots

**Python**

You can render a [`Slot`](../../../reference/api#django_components.Slot) instance by simply calling it with data:

```py
slot = Slot(lambda ctx: f"Hello, {ctx.data['name']}!")

# Render the slot with data
html = slot({"name": "John"})
```

Optionally you can pass the [fallback](#slot-fallback) value to the slot. Fallback should be a string.

```py
html = slot({"name": "John"}, fallback="Hello, world!")
```

**Template**

Alternatively, you can pass the [`Slot`](../../../reference/api#django_components.Slot) instance to the
[`{% fill %}`](../../../reference/template_tags#fill) tag:

```django
{% fill "name" body=slot / %}
```

### Slot context

If a slot function is rendered by the [`{% slot %}`](../../../reference/template_tags#slot) tag,
you can access the current [Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
using the `context` attribute.

```py
class Table(Component):
    template = """
        {% with "abc" as my_var %}
            {% slot "name" %}
                Hello!
            {% endslot %}
        {% endwith %}
    """

def slot_func(ctx):
    return f"Hello, {ctx.context['my_var']}!"

slot = Slot(slot_func)
html = slot()
```

!!! warning

    While available, try to avoid using the `context` attribute in slot functions.

    Instead, prefer using the `data` and `fallback` attributes.

    <!-- TODO_v2: Check if still applicable -->
    Access to `context` may be removed in future versions (v2, v3).

### Slot metadata

When accessing slots from within [`Component`](../../../reference/api#django_components.Component) methods,
the [`Slot`](../../../reference/api#django_components.Slot) instances are populated
with extra metadata [`component_name`](../../../reference/api#django_components.Slot.component_name)
and [`slot_name`](../../../reference/api#django_components.Slot.slot_name).

These are used solely for debugging.

In fact, you can set these fields too when creating new slots:

```py
# Either at slot creation
slot = Slot(
    lambda ctx: f"Hello, {ctx.data['name']}!",
    component_name="table",
    slot_name="name",
)

# Or later
slot.component_name = "table"
slot.slot_name = "name"
```

### Slot contents

Whether you create a slot from a function, a string, or from the [`{% fill %}`](../../../reference/template_tags#fill) tags,
the [`Slot`](../../../reference/api#django_components.Slot) class normalizes its contents to a function.

Use [`Slot.contents`](../../../reference/api#django_components.Slot.contents) to access the original value that was passed to the Slot constructor.

```py
slot = Slot("Hello!")
print(slot.contents)  # "Hello!"
```

If the slot was created from a string or from the [`{% fill %}`](../../../reference/template_tags#fill) tags,
the contents will be accessible also as a Nodelist under [`Slot.nodelist`](../../../reference/api#django_components.Slot.nodelist).

```py
slot = Slot("Hello!")
print(slot.nodelist)  # <django.template.Nodelist: ['Hello!']>
```

!!! info

    If you pass a [`Slot`](../../../reference/api#django_components.Slot) instance to the constructor,
    the inner slot will be "unwrapped" and its `Slot.contents` will be used instead.

    ```py
    slot = Slot("Hello")
    print(slot.contents)  # "Hello"

    slot2 = Slot(slot)
    print(slot2.contents)  # "Hello"
    ```

### Escaping slots content

Slots content are automatically escaped by default to prevent XSS attacks.

In other words, it's as if you would be using Django's [`mark_safe()`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.mark_safe) function on the slot content:

```python
from django.utils.safestring import mark_safe

class Calendar(Component):
    template = """
        <div>
            {% slot "date" default date=date / %}
        </div>
    """

Calendar.render(
    slots={
        "date": mark_safe("<b>Hello</b>"),
    }
)
```

To disable escaping, you can pass `escape_slots_content=False` to
[`Component.render()`](../../../reference/api#django_components.Component.render)
or [`Component.render_to_response()`](../../../reference/api#django_components.Component.render_to_response)
methods.

!!! warning

    If you disable escaping, you should make sure that any content you pass to the slots is safe,
    especially if it comes from user input!

!!! info

    If you're planning on passing an HTML string, check Django's use of
    [`format_html`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.html.format_html)
    and [`mark_safe`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.mark_safe).

## Examples

### Pass through all the slots

You can dynamically pass all slots to a child component. This is similar to
[passing all slots in Vue](https://vue-land.github.io/faq/forwarding-slots#passing-all-slots):

```djc_py
class MyTable(Component):
    template = """
        <div>
          {% component "child" %}
            {% for slot_name, slot in component_vars.slots.items %}
              {% fill name=slot_name body=slot / %}
            {% endfor %}
          {% endcomponent %}
        </div>
    """
```

### Required and default slots

Since each [`{% slot %}`](../../../reference/template_tags#slot) is tagged
with [`required`](#required-slot) and [`default`](#default-slot) individually, you can have multiple slots
with the same name but different conditions.

In this example, we have a component that renders a user avatar - a small circular image with a profile picture or name initials.

If the component is given `image_src` or `name_initials` variables,
the `image` slot is optional.

But if neither of those are provided, you MUST fill the `image` slot.

```htmldjango
<div class="avatar">
    {# Image given, so slot is optional #}
    {% if image_src %}
        {% slot "image" default %}
            <img src="{{ image_src }}" />
        {% endslot %}

    {# Image not given, but we can make image from initials, so slot is optional #}    
    {% elif name_initials %}
        {% slot "image" default %}
            <div style="
                border-radius: 25px;
                width: 50px;
                height: 50px;
                background: blue;
            ">
                {{ name_initials }}
            </div>
        {% endslot %}
    
    {# Neither image nor initials given, so slot is required #}
    {% else %}
        {% slot "image" default required / %}
    {% endif %}
</div>
```

### Dynamic slots in table component

Sometimes you may want to generate slots based on the given input. One example of this is [Vuetify's table component](https://vuetifyjs.com/en/api/v-data-table/), which creates a header and an item slots for each user-defined column.

So if you pass columns named `name` and `age` to the table component:

```py
[
    {"key": "name", "title": "Name"},
    {"key": "age", "title": "Age"},
]
```

Then the component will accept fills named `header-name` and `header-age` (among others):

```django
{% fill "header-name" data="data" %}
    <b>{{ data.value }}</b>
{% endfill %}

{% fill "header-age" data="data" %}
    <b>{{ data.value }}</b>
{% endfill %}
```

In django-components you can achieve the same, simply by using a variable or a [template expression](../template_tag_syntax#template-tags-inside-literal-strings) instead of a string literal:

```django
<table>
  <tr>
    {% for header in headers %}
      <th>
        {% slot "header-{{ header.key }}" value=header.title %}
          {{ header.title }}
        {% endslot %}
      </th>
    {% endfor %}
  </tr>
</table>
```

When using the component, you can either set the fill explicitly:

```django
{% component "table" headers=headers items=items %}
    {% fill "header-name" data="data" %}
        <b>{{ data.value }}</b>
    {% endfill %}
{% endcomponent %}
```

Or also use a variable:

```django
{% component "table" headers=headers items=items %}
    {% fill "header-{{ active_header_name }}" data="data" %}
        <b>{{ data.value }}</b>
    {% endfill %}
{% endcomponent %}
```

!!! note

    It's better to use literal slot names whenever possible for clarity.
    The dynamic slot names should be reserved for advanced use only.

### Spread operator

Lastly, you can also pass the slot name through the [spread operator](../template_tag_syntax#spread-operator).

When you define a slot name, it's actually a shortcut for a `name` keyword argument.

So this:

```django
{% slot "content" / %}
```

is the same as:

```django
{% slot name="content" / %}
```

So it's possible to define a `name` key on a dictionary, and then spread that onto the slot tag:

```django
{# slot_props = {"name": "content"} #}
{% slot ...slot_props / %}
```

Full example:

```djc_py
class MyTable(Component):
    template = """
        {% slot ...slot_props / %}
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "slot_props": {"name": "content", "extra_field": 123},
        }
```

!!! info

    This applies for both [`{% slot %}`](../../../reference/template_tags#slot)
    and [`{% fill %}`](../../../reference/template_tags#fill) tags.

<!-- TODO_V1: Remove this section -->

## Legacy conditional slots

> Since version 0.70, you could check if a slot was filled with
>
> `{{ component_vars.is_filled.<name> }}`
>
> Since version 0.140, this has been deprecated and superseded with
>
> [`{% component_vars.slots.<name> %}`](../../../reference/template_vars#slots)
>
> The `component_vars.is_filled` variable is still available, but will be removed in v1.0.
>
> NOTE: `component_vars.slots` no longer escapes special characters in slot names.

You can use `{{ component_vars.is_filled.<name> }}` together with Django's `{% if / elif / else / endif %}` tags
to define a block whose contents will be rendered only if the component slot with the corresponding 'name' is filled.

This is what our example looks like with `component_vars.is_filled`.

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}
            Title
        {% endslot %}
    </div>
    {% if component_vars.is_filled.subtitle %}
        <div class="subtitle">
            {% slot "subtitle" %}
                {# Optional subtitle #}
            {% endslot %}
        </div>
    {% elif component_vars.is_filled.title %}
        ...
    {% elif component_vars.is_filled.<name> %}
        ...
    {% endif %}
</div>
```

### Accessing `is_filled` of slot names with special characters

To be able to access a slot name via `component_vars.is_filled`, the slot name needs to be composed of only alphanumeric characters and underscores (e.g. `this__isvalid_123`).

However, you can still define slots with other special characters. In such case, the slot name in `component_vars.is_filled` is modified to replace all invalid characters into `_`.

So a slot named `"my super-slot :)"` will be available as `component_vars.is_filled.my_super_slot___`.

Same applies when you are accessing `is_filled` from within the Python, e.g.:

```py
class MyTable(Component):
    def on_render_before(self, context, template) -> None:
        # ✅ Works
        if self.is_filled["my_super_slot___"]:
            # Do something

        # ❌ Does not work
        if self.is_filled["my super-slot :)"]:
            # Do something
```
