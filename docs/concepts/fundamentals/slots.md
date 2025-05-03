_New in version 0.26_:

- The `slot` tag now serves only to declare new slots inside the component template.
  - To override the content of a declared slot, use the newly introduced `fill` tag instead.
- Whereas unfilled slots used to raise a warning, filling a slot is now optional by default.
  - To indicate that a slot must be filled, the new `required` option should be added at the end of the `slot` tag.

---

Components support something called 'slots'.
When a component is used inside another template, slots allow the parent template to override specific parts of the child component by passing in different content.
This mechanism makes components more reusable and composable.
This behavior is similar to [slots in Vue](https://vuejs.org/guide/components/slots.html).

In the example below we introduce two block tags that work hand in hand to make this work. These are...

- `{% slot <name> %}`/`{% endslot %}`: Declares a new slot in the component template.
- `{% fill <name> %}`/`{% endfill %}`: (Used inside a `{% component %}` tag pair.) Fills a declared slot with the specified content.

Let's update our calendar component to support more customization. We'll add `slot` tag pairs to its template, _template.html_.

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "header" %}Calendar header{% endslot %}
    </div>
    <div class="body">
        {% slot "body" %}Today's date is <span>{{ date }}</span>{% endslot %}
    </div>
</div>
```

When using the component, you specify which slots you want to fill and where you want to use the defaults from the template. It looks like this:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "body" %}
        Can you believe it's already <span>{{ date }}</span>??
    {% endfill %}
{% endcomponent %}
```

Since the 'header' fill is unspecified, it's taken from the base template. If you put this in a template, and pass in `date=2020-06-06`, this is what gets rendered:

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

### Named slots

As seen in the previouse section, you can use `{% fill slot_name %}` to insert content into a specific
slot.

You can define fills for multiple slot simply by defining them all within the `{% component %} {% endcomponent %}`
tags:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}
        Hi this is header!
    {% endfill %}
    {% fill "body" %}
        Can you believe it's already <span>{{ date }}</span>??
    {% endfill %}
{% endcomponent %}
```

You can also use `{% for %}`, `{% with %}`, or other non-component tags (even `{% include %}`)
to construct the `{% fill %}` tags, **as long as these other tags do not leave any text behind!**

```django
{% component "table" %}
  {% for slot_name in slots %}
    {% fill name=slot_name %}
      {{ slot_name }}
    {% endfill %}
  {% endfor %}

  {% with slot_name="abc" %}
    {% fill name=slot_name %}
      {{ slot_name }}
    {% endfill %}
  {% endwith %}
{% endcomponent %}
```

### Default slot

_Added in version 0.28_

As you can see, component slots lets you write reusable containers that you fill in when you use a component. This makes for highly reusable components that can be used in different circumstances.

It can become tedious to use `fill` tags everywhere, especially when you're using a component that declares only one slot. To make things easier, `slot` tags can be marked with an optional keyword: `default`.

When added to the tag (as shown below), this option lets you pass filling content directly in the body of a `component` tag pair – without using a `fill` tag. Choose carefully, though: a component template may contain at most one slot that is marked as `default`. The `default` option can be combined with other slot options, e.g. `required`.

Here's the same example as before, except with default slots and implicit filling.

The template:

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "header" %}Calendar header{% endslot %}
    </div>
    <div class="body">
        {% slot "body" default %}Today's date is <span>{{ date }}</span>{% endslot %}
    </div>
</div>
```

Including the component (notice how the `fill` tag is omitted):

```htmldjango
{% component "calendar" date="2020-06-06" %}
    Can you believe it's already <span>{{ date }}</span>??
{% endcomponent %}
```

The rendered result (exactly the same as before):

```html
<div class="calendar-component">
  <div class="header">Calendar header</div>
  <div class="body">Can you believe it's already <span>2020-06-06</span>??</div>
</div>
```

You may be tempted to combine implicit fills with explicit `fill` tags. This will not work. The following component template will raise an error when rendered.

```htmldjango
{# DON'T DO THIS #}
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}Totally new header!{% endfill %}
    Can you believe it's already <span>{{ date }}</span>??
{% endcomponent %}
```

Instead, you can use a named fill with name `default` to target the default fill:

```htmldjango
{# THIS WORKS #}
{% component "calendar" date="2020-06-06" %}
    {% fill "header" %}Totally new header!{% endfill %}
    {% fill "default" %}
        Can you believe it's already <span>{{ date }}</span>??
    {% endfill %}
{% endcomponent %}
```

NOTE: If you doubly-fill a slot, that is, that both `{% fill "default" %}` and `{% fill "header" %}`
would point to the same slot, this will raise an error when rendered.

#### Accessing default slot in Python

Since the default slot is stored under the slot name `default`, you can access the default slot
like so:

```py
class MyTable(Component):
    def get_template_data(self, args, kwargs, slots, context):
        default_slot = slots["default"]
        return {
            "default_slot": default_slot,
        }
```

### Render fill in multiple places

_Added in version 0.70_

You can render the same content in multiple places by defining multiple slots with
identical names:

```htmldjango
<div class="calendar-component">
    <div class="header">
        {% slot "image" %}Image here{% endslot %}
    </div>
    <div class="body">
        {% slot "image" %}Image here{% endslot %}
    </div>
</div>
```

So if used like:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "image" %}
        <img src="..." />
    {% endfill %}
{% endcomponent %}
```

This renders:

```htmldjango
<div class="calendar-component">
    <div class="header">
        <img src="..." />
    </div>
    <div class="body">
        <img src="..." />
    </div>
</div>
```

#### Default and required slots

If you use a slot multiple times, you can still mark the slot as `default` or `required`.
For that, you must mark each slot individually, e.g.:

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

Which you can then use as regular default slot:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    <img src="..." />
{% endcomponent %}
```

Since each slot is tagged individually, you can have multiple slots
with the same name but different conditions.

E.g. in this example, we have a component that renders a user avatar - a small circular image with a profile picture or name initials.

If the component is given `image_src` or `name_initials` variables,
the `image` slot is optional. But if neither of those are provided,
you MUST fill the `image` slot.

```htmldjango
<div class="avatar">
    {% if image_src %}
        {% slot "image" default %}
            <img src="{{ image_src }}" />
        {% endslot %}
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
    {% else %}
        {% slot "image" default required / %}
    {% endif %}
</div>
```

### Accessing original content of slots

_Added in version 0.26_

> NOTE: In version 0.77, the syntax was changed from
>
> ```django
> {% fill "my_slot" as "alias" %} {{ alias.default }}
> ```
>
> to
>
> ```django
> {% fill "my_slot" default="slot_default" %} {{ slot_default }}
> ```

Sometimes you may want to keep the original slot, but only wrap or prepend/append content to it. To do so, you can access the default slot via the `default` kwarg.

Similarly to the `data` attribute, you specify the variable name through which the default slot will be made available.

For instance, let's say you're filling a slot called 'body'. To render the original slot, assign it to a variable using the `'default'` keyword. You then render this variable to insert the default content:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "body" default="body_default" %}
        {{ body_default }}. Have a great day!
    {% endfill %}
{% endcomponent %}
```

This produces:

```htmldjango
<div class="calendar-component">
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Today's date is <span>2020-06-06</span>. Have a great day!
    </div>
</div>
```

To access the original content of a default slot, set the name to `default`:

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "default" default="slot_default" %}
        {{ slot_default }}. Have a great day!
    {% endfill %}
{% endcomponent %}
```

### Conditional slots

_Added in version 0.26._

> NOTE: In version 0.70, `{% if_filled %}` tags were replaced with `{{ component_vars.is_filled }}` variables. If your slot name contained special characters, see the section [Accessing `is_filled` of slot names with special characters](#accessing-is_filled-of-slot-names-with-special-characters).

In certain circumstances, you may want the behavior of slot filling to depend on
whether or not a particular slot is filled.

For example, suppose we have the following component template:

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
</div>
```

By default the slot named 'subtitle' is empty. Yet when the component is used without
explicit fills, the div containing the slot is still rendered, as shown below:

```html
<div class="frontmatter-component">
  <div class="title">Title</div>
  <div class="subtitle"></div>
</div>
```

This may not be what you want. What if instead the outer 'subtitle' div should only
be included when the inner slot is in fact filled?

The answer is to use the `{{ component_vars.is_filled.<name> }}` variable. You can use this together with Django's `{% if/elif/else/endif %}` tags to define a block whose contents will be rendered only if the component slot with
the corresponding 'name' is filled.

This is what our example looks like with `component_vars.is_filled`.

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    {% if component_vars.is_filled.subtitle %}
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
    {% endif %}
</div>
```

Here's our example with more complex branching.

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    {% if component_vars.is_filled.subtitle %}
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
    {% elif component_vars.is_filled.title %}
        ...
    {% elif component_vars.is_filled.<name> %}
        ...
    {% endif %}
</div>
```

Sometimes you're not interested in whether a slot is filled, but rather that it _isn't_.
To negate the meaning of `component_vars.is_filled`, simply treat it as boolean and negate it with `not`:

```htmldjango
{% if not component_vars.is_filled.subtitle %}
<div class="subtitle">
    {% slot "subtitle" / %}
</div>
{% endif %}
```

#### Accessing `is_filled` of slot names with special characters

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

### Conditional fills

Similarly, you can use `{% if %}` and `{% for %}` when defining the `{% fill %}` tags, to conditionally fill the slots when using the componnet:

In the example below, the `{% fill "footer" %}` fill is used only if the condition is true. If falsy, the fill is ignored, and so the `my_table` component will use its default content for the `footer` slot.

```django_html
{% component "my_table" %}
    {% if editable %}
        {% fill "footer" %}
            <input name="name" />
        {% endfill %}
    {% endif %}
{% endcomponent %}
```

You can even combine `{% if %}` and `{% for %}`:

```django_html
{% component "my_table" %}
    {% for header in headers %}
        {% if header != "hyperlink" %}
            {# Generate fill name like `header.my_column` #}
            {% fill name="header."|add:header" %}
                <b>{{ header }}</b>
            {% endfill %}
        {% endif %}
    {% endfor %}
{% endcomponent %}
```

### Scoped slots

_Added in version 0.76_:

Consider a component with slot(s). This component may do some processing on the inputs, and then use the processed variable in the slot's default template:

```djc_py
@register("my_comp")
class MyComp(Component):
    template = """
        <div>
            {% slot "content" default %}
                input: {{ input }}
            {% endslot %}
        </div>
    """

    def get_template_data(self, args, kwargs, slots, context):
        processed_input = do_something(kwargs["input"])
        return {"input": processed_input}
```

You may want to design a component so that users of your component can still access the `input` variable, so they don't have to recompute it.

This behavior is called "scoped slots". This is inspired by [Vue scoped slots](https://vuejs.org/guide/components/slots.html#scoped-slots) and [scoped slots of django-web-components](https://github.com/Xzya/django-web-components/tree/master?tab=readme-ov-file#scoped-slots).

Using scoped slots consists of two steps:

1. Passing data to `slot` tag
2. Accessing data in `fill` tag

#### Passing data to slots

To pass the data to the `slot` tag, simply pass them as keyword attributes (`key=value`):

```djc_py
@register("my_comp")
class MyComp(Component):
    template = """
        <div>
            {% slot "content" default input=input %}
                input: {{ input }}
            {% endslot %}
        </div>
    """

    def get_template_data(self, args, kwargs, slots, context):
        processed_input = do_something(kwargs["input"])
        return {
            "input": processed_input,
        }
```

#### Accessing slot data in fill

Next, we head over to where we define a fill for this slot. Here, to access the slot data
we set the `data` attribute to the name of the variable through which we want to access
the slot data. In the example below, we set it to `data`:

```django
{% component "my_comp" %}
    {% fill "content" data="slot_data" %}
        {{ slot_data.input }}
    {% endfill %}
{% endcomponent %}
```

To access slot data on a default slot, you have to explictly define the `{% fill %}` tags.

So this works:

```django
{% component "my_comp" %}
    {% fill "content" data="slot_data" %}
        {{ slot_data.input }}
    {% endfill %}
{% endcomponent %}
```

While this does not:

```django
{% component "my_comp" data="data" %}
    {{ data.input }}
{% endcomponent %}
```

Note: You cannot set the `data` attribute and
[`default` attribute)](#accessing-original-content-of-slots)
to the same name. This raises an error:

```django
{% component "my_comp" %}
    {% fill "content" data="slot_var" default="slot_var" %}
        {{ slot_var.input }}
    {% endfill %}
{% endcomponent %}
```

#### Slot data of default slots

To access data of a default slot, you can specify `{% fill name="default" %}`:

```htmldjango
{% component "my_comp" %}
    {% fill "default" data="slot_data" %}
        {{ slot_data.input }}
    {% endfill %}
{% endcomponent %}
```

### Dynamic slots and fills

Until now, we were declaring slot and fill names statically, as a string literal, e.g.

```django
{% slot "content" / %}
```

However, sometimes you may want to generate slots based on the given input. One example of this is [a table component like that of Vuetify](https://vuetifyjs.com/en/api/v-data-table/), which creates a header and an item slots for each user-defined column.

In django_components you can achieve the same, simply by using a variable (or a [template expression](#use-template-tags-inside-component-inputs)) instead of a string literal:

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
  {# Make only the active column bold #}
  {% fill "header-{{ active_header_name }}" data="data" %}
    <b>{{ data.value }}</b>
  {% endfill %}
{% endcomponent %}
```

> NOTE: It's better to use static slot names whenever possible for clarity. The dynamic slot names should be reserved for advanced use only.

Lastly, in rare cases, you can also pass the slot name via [the spread operator](#spread-operator). This is possible, because the slot name argument is actually a shortcut for a `name` keyword argument.

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

### Pass through all the slots

You can dynamically pass all slots to a child component. This is similar to
[passing all slots in Vue](https://vue-land.github.io/faq/forwarding-slots#passing-all-slots):

```djc_py
class MyTable(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "slots": slots,
        }

    template = """
    <div>
      {% component "child" %}
        {% for slot_name in slots %}
          {% fill name=slot_name data="data" %}
            {% slot name=slot_name ...data / %}
          {% endfill %}
        {% endfor %}
      {% endcomponent %}
    </div>
    """
```

### Escaping slots content

Slots content are automatically escaped by default to prevent XSS attacks.

In other words, it's as if you would be using Django's [`mark_safe()`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.safestring.mark_safe) function on the slot content:

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
[`Component.render()`](../../reference/api#django_components.Component.render)
or [`Component.render_to_response()`](../../reference/api#django_components.Component.render_to_response)
methods.

!!! warning

    If you disable escaping, you should make sure that any content you pass to the slots is safe,
    especially if it comes from user input!

!!! info

    If you're planning on passing an HTML string, check Django's use of
    [`format_html`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.html.format_html)
    and [`mark_safe`](https://docs.djangoproject.com/en/5.0/ref/utils/#django.utils.safestring.mark_safe).
