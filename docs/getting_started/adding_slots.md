Our calendar component's looking great! But we just got a new assignment from
our colleague - The calendar date needs to be shown on 3 different pages:

1. On one page, it needs to be shown as is
2. On the second, the date needs to be **bold**
3. On the third, the date needs to be in _italics_

As a reminder, this is what the component's template looks like:

```htmldjango
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

There's many ways we could approach this:

- Expose the date in a slot
- Style `.calendar > span` differently on different pages
- Pass a variable to the component that decides how the date is rendered
- Create a new component

First two options are more flexible, because the custom styling is not baked into a component's
implementation. And for the sake of demonstration, we'll solve this challenge with slots.

### 1. What are slots

Components support something called [Slots](../concepts/fundamentals/slots.md).

When a component is used inside another template, slots allow the parent template
to override specific parts of the child component by passing in different content.

This mechanism makes components more reusable and composable.

This behavior is similar to [slots in Vue](https://vuejs.org/guide/components/slots.html).

In the example below we introduce two tags that work hand in hand to make this work. These are...

- `{% slot <name> %}`/`{% endslot %}`: Declares a new slot in the component template.
- `{% fill <name> %}`/`{% endfill %}`: (Used inside a [`{% component %}`](../reference/template_tags.md#component)
  tag pair.) Fills a declared slot with the specified content.

### 2. Add a slot tag

Let's update our calendar component to support more customization. We'll add
[`{% slot %}`](../reference/template_tags.md#slot) tag to the template:

```htmldjango
<div class="calendar">
  Today's date is
  {% slot "date" default %}  {# <--- new #}
    <span>{{ date }}</span>
  {% endslot %}
</div>
```

Notice that:

1. We named the slot `date` - so we can fill this slot by using `{% fill "date" %}`

2. We also made it the [default slot](../concepts/fundamentals/slots.md#default-slot).

3. We placed our original implementation inside the [`{% slot %}`](../reference/template_tags.md#slot)
   tag - this is what will be rendered when the slot is NOT overriden.

### 3. Add fill tag

Now we can use [`{% fill %}`](../reference/template_tags.md#fill) tags inside the
[`{% component %}`](../reference/template_tags.md#component) tags to override the `date` slot
to generate the bold and italics variants:

```htmldjango
{# Default #}
{% component "calendar" date="2024-12-13" / %}

{# Bold #}
{% component "calendar" date="2024-12-13" %}
  <b> 2024-12-13 </b>
{% endcomponent %}

{# Italics #}
{% component "calendar" date="2024-12-13" %}
  <i> 2024-12-13 </i>
{% endcomponent %}
```

Which will render as:

```html
<!-- Default -->
<div class="calendar">
  Today's date is <span>2024-12-13</span>
</div>

<!-- Bold -->
<div class="calendar">
  Today's date is <b>2024-12-13</b>
</div>

<!-- Italics -->
<div class="calendar">
  Today's date is <i>2024-12-13</i>
</div>
```

!!! info

    Since we used the `default` flag on `{% slot "date" %}` inside our calendar component,
    we can target the `date` component in multiple ways:

    1. Explicitly by it's name
        ```htmldjango
        {% component "calendar" date="2024-12-13" %}
          {% fill "date" %}
            <i> 2024-12-13 </i>
          {% endfill %}
        {% endcomponent %}
        ```

    2. Implicitly as the [default slot](../concepts/fundamentals/slots.md#default-slot) (Omitting the
        [`{% fill %}`](../reference/template_tags.md#fill) tag)
        ```htmldjango
        {% component "calendar" date="2024-12-13" %}
          <i> 2024-12-13 </i>
        {% endcomponent %}
        ```

    3. Explicitly as the [default slot](../concepts/fundamentals/slots.md#default-slot) (Setting fill name to `default`)
        ```htmldjango
        {% component "calendar" date="2024-12-13" %}
          {% fill "default" %}
            <i> 2024-12-13 </i>
          {% endfill %}
        {% endcomponent %}
        ```

### 4. Wait, there's a bug

There is a mistake in our code! `2024-12-13` is Friday, so that's fine. But if we updated
the to `2024-12-14`, which is Saturday, our template from previous step would render this:

```html
<!-- Default -->
<div class="calendar">
  Today's date is <span>2024-12-16</span>
</div>

<!-- Bold -->
<div class="calendar">
  Today's date is <b>2024-12-14</b>
</div>

<!-- Italics -->
<div class="calendar">
  Today's date is <i>2024-12-14</i>
</div>
```

The first instance rendered `2024-12-16`, while the rest rendered `2024-12-14`!

Why? Remember that in the [`get_template_data()`](../reference/api.md#django_components.Component.get_template_data)
method of our Calendar component, we pre-process the date. If the date falls on Saturday or Sunday, we shift it to next Monday:

```python title="[project root]/components/calendar/calendar.py"
from datetime import date

from django_components import Component, register

# If date is Sat or Sun, shift it to next Mon, so the date is always workweek.
def to_workweek_date(d: date):
    ...

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    ...
    def get_template_data(self, args, kwargs, slots, context):
        workweek_date = to_workweek_date(kwargs["date"])
        return {
            "date": workweek_date,
            "extra_class": kwargs.get("extra_class", "text-blue"),
        }
```

And the issue is that in our template, we used the `date` value that we used _as input_,
which is NOT the same as the `date` variable used inside Calendar's template.

### 5. Adding data to slots

We want to use the same `date` variable that's used inside Calendar's template.

Luckily, django-components allows [passing data to slots](../concepts/fundamentals/slots.md#slot-data),
also known as [Scoped slots](https://vuejs.org/guide/components/slots#scoped-slots).

This consists of two steps:

1. Pass the `date` variable to the [`{% slot %}`](../reference/template_tags.md#slot) tag
2. Access the `date` variable in the [`{% fill %}`](../reference/template_tags.md#fill)
   tag by using the special `data` kwarg

Let's update the Calendar's template:

```htmldjango
<div class="calendar">
  Today's date is
  {% slot "date" default date=date %}  {# <--- changed #}
    <span>{{ date }}</span>
  {% endslot %}
</div>
```

!!! info

    The [`{% slot %}`](../reference/template_tags.md#slot) tag has one special kwarg, `name`. When you write

    ```htmldjango
    {% slot "date" / %}
    ```

    It's the same as:

    ```htmldjango
    {% slot name="date" / %}
    ```

    Other than the `name` kwarg, you can pass any extra kwargs to the [`{% slot %}`](../reference/template_tags.md#slot) tag,
    and these will be exposed as the slot's data.

    ```htmldjango
    {% slot name="date" kwarg1=123 kwarg2="text" kwarg3=my_var / %}
    ```

### 6. Accessing slot data in fills

Now, on the [`{% fill %}`](../reference/template_tags.md#fill) tags, we can use the `data` kwarg to specify the variable under which
the slot data will be available.

The variable from the `data` kwarg contains all the extra kwargs passed to the [`{% slot %}`](../reference/template_tags.md#slot) tag.

So if we set `data="slot_data"`, then we can access the date variable under `slot_data.date`:

```htmldjango
{# Default #}
{% component "calendar" date="2024-12-13" / %}

{# Bold #}
{% component "calendar" date="2024-12-13" %}
  {% fill "date" data="slot_data" %}
    <b> {{ slot_data.date }} </b>
  {% endfill %}
{% endcomponent %}

{# Italics #}
{% component "calendar" date="2024-12-13" %}
  {% fill "date" data="slot_data" %}
    <i> {{ slot_data.date }} </i>
  {% endfill %}
{% endcomponent %}
```

By using the `date` variable from the slot, we'll render the correct date
each time:

```html
<!-- Default -->
<div class="calendar">
  Today's date is <span>2024-12-16</span>
</div>

<!-- Bold -->
<div class="calendar">
  Today's date is <b>2024-12-16</b>
</div>

<!-- Italics -->
<div class="calendar">
  Today's date is <i>2024-12-16</i>
</div>
```

!!! info

    **When to use slots vs variables?**

    Generally, slots are more flexible - you can access the slot data, even the original slot content.
    Thus, slots behave more like functions that render content based on their context.

    On the other hand, variables are simpler - the variable you pass to a component is what will be used.

    Moreover, slots are treated as part of the template - for example the CSS scoping (work in progress)
    is applied to the slot content too.

---

So far we've rendered components using template tag. [Next, let’s explore other ways to render components ➡️](./rendering_components.md)
