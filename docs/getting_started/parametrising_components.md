So far, our Calendar component will always render the date `1970-01-01`. Let's make it more useful and flexible
by being able to pass in custom date.

What we want is to be able to use the Calendar component within the template like so:

```htmldjango
{% component "calendar" date="2024-12-13" extra_class="text-red" / %}
```

### 1. Understading component inputs

In section [Create your first component](../your_first_component), we defined
the [`get_context_data()`](../../reference/api#django_components.Component.get_context_data) method
that defines what variables will be available within the template:

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    ...
    def get_context_data(self):
        return {
            "date": "1970-01-01",
        }
```

What we didn't say is that [`get_context_data()`](../../reference/api#django_components.Component.get_context_data)
actually receives the args and kwargs that were passed to a component.

So if we call a component with a `date` and `extra_class` keywords:

```htmldjango
{% component "calendar" date="2024-12-13" extra_class="text-red" / %}
```

This is the same as calling:

```py
Calendar.get_context_data(date="2024-12-13", extra_class="text-red")
```

And same applies to positional arguments, or mixing args and kwargs, where:

```htmldjango
{% component "calendar" "2024-12-13" extra_class="text-red" / %}
```

is same as

```py
Calendar.get_context_data("2024-12-13", extra_class="text-red")
```

### 2. Define inputs for `get_context_data`

Let's put this to test. We want to pass `date` and `extra_class` kwargs to the component.
And so, we can write the [`get_context_data()`](../../reference/api#django_components.Component.get_context_data)
method such that it expects those parameters:

```python title="[project root]/components/calendar/calendar.py"
from datetime import date

from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    ...
    def get_context_data(self, date: date, extra_class: str = "text-blue"):
        return {
            "date": date,
            "extra_class": extra_class,
        }
```

!!! info

    Since [`get_context_data()`](../../reference/api#django_components.Component.get_context_data)
    is just a regular Python function, type hints annotations work the same way as anywhere else.

!!! warning

    Since [`get_context_data()`](../../reference/api#django_components.Component.get_context_data)
    is just a regular Python function, it will raise TypeError if it receives incorrect parameters.

Since `extra_class` is optional in the function signature, it's optional also in the template.
So both following calls are valid:

```htmldjango
{% component "calendar" "2024-12-13" / %}
{% component "calendar" "2024-12-13" extra_class="text-red" / %}
```

However, `date` is required. Thus we MUST provide it. Same with regular Python functions,
`date` can be set either as positional or keyword argument. But either way it MUST be set:

```htmldjango
✅
{% component "calendar" "2024-12-13" / %}
{% component "calendar" extra_class="text-red" date="2024-12-13" / %}

❌
{% component "calendar" extra_class="text-red" / %}
```

### 3. Process inputs in `get_context_data`

The [`get_context_data()`](../../reference/api#django_components.Component.get_context_data)
method is powerful, because it allows us to decouple
component inputs from the template variables. In other words, we can pre-process
the component inputs, and massage them into a shape that's most appropriate for
what the template needs. And it also allows us to pass in static data into the template.

Imagine our component receives data from the database that looks like below
([taken from Django](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#regroup)).

```py
cities = [
    {"name": "Mumbai", "population": "19,000,000", "country": "India"},
    {"name": "Calcutta", "population": "15,000,000", "country": "India"},
    {"name": "New York", "population": "20,000,000", "country": "USA"},
    {"name": "Chicago", "population": "7,000,000", "country": "USA"},
    {"name": "Tokyo", "population": "33,000,000", "country": "Japan"},
]
```

We need to group the list items by size into following buckets by population:

- 0-10,000,000
- 10,000,001-20,000,000
- 20,000,001-30,000,000
- +30,000,001

So we want to end up with following data:

```py
cities_by_pop = [
    {
      "name": "0-10,000,000",
      "items": [
          {"name": "Chicago", "population": "7,000,000", "country": "USA"},
      ]
    },
    {
      "name": "10,000,001-20,000,000",
      "items": [
          {"name": "Calcutta", "population": "15,000,000", "country": "India"},
          {"name": "Mumbai", "population": "19,000,000", "country": "India"},
          {"name": "New York", "population": "20,000,000", "country": "USA"},
      ]
    },
    {
      "name": "30,000,001-40,000,000",
      "items": [
          {"name": "Tokyo", "population": "33,000,000", "country": "Japan"},
      ]
    },
]
```

Without the `get_context_data()` method, we'd have to either:

1. Pre-process the data in Python before passing it to the components.
2. Define a Django filter or template tag to take the data and process it on the spot.

Instead, with `get_context_data()`, we can keep this transformation private to this component,
and keep the rest of the codebase clean.

```py
def group_by_pop(data):
    ...

@register("population_table")
class PopulationTable(Component):
    template_file = "population_table.html"

    def get_context_data(self, data):
        return {
            "data": group_by_pop(data),
        }
```

Similarly we can make use of `get_context_data()` to pre-process the date that was given to the component:

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
    def get_context_data(self, date: date, extra_class: str = "text-blue"):
        workweek_date = to_workweek_date(date)  # <--- new
        return {
            "date": workweek_date,  # <--- changed
            "extra_class": extra_class,
        }
```

### 4. Pass inputs to components

Once we're happy with `Calendar.get_contex_data()`, we can update our templates to use
the parametrized version of the component:

```htmldjango
<div>
  {% component "calendar" date="2024-12-13" / %}
  {% component "calendar" date="1970-01-01" / %}
</div>
```

---

Next, you will learn [how to use slots give your components even more flexibility ➡️](./adding_slots.md)

### 5. Add defaults

In our example, we've set the `extra_class` to default to `"text-blue"` by setting it in the
[`get_context_data()`](../../reference/api#django_components.Component.get_context_data)
method.

However, you may want to use the same default value in multiple methods, like
[`get_js_data()`](../../reference/api#django_components.Component.get_js_data)
or [`get_css_data()`](../../reference/api#django_components.Component.get_css_data).

To make things easier, Components can specify their defaults. Defaults are used when
no value is provided, or when the value is set to `None` for a particular input.

To define defaults for a component, you create a nested `Defaults` class within your
[`Component`](../../reference/api#django_components.Component) class.
Each attribute in the `Defaults` class represents a default value for a corresponding input.

```py
from django_components import Component, Default, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"

    class Defaults:  # <--- new
        extra_class = "text-blue"

    def get_context_data(self, date: date, extra_class: str):  # <--- changed
        workweek_date = to_workweek_date(date)
        return {
            "date": workweek_date,
            "extra_class": extra_class,
        }
```
