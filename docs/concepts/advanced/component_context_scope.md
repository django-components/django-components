By default, context variables are passed down the template as in regular Django - deeper scopes can access the variables from the outer scopes. So if you have several nested forloops, then inside the deep-most loop you can access variables defined by all previous loops.

With this in mind, the `{% component %}` tag behaves similarly to `{% include %}` tag - inside the component tag, you can access all variables that were defined outside of it.

And just like with `{% include %}`, if you don't want a specific component template to have access to the parent context, add `only` to the `{% component %}` tag:

```htmldjango
{% component "calendar" date="2015-06-19" only / %}
```

NOTE: `{% csrf_token %}` tags need access to the top-level context, and they will not function properly if they are rendered in a component that is called with the `only` modifier.

If you find yourself using the `only` modifier often, you can set the [context_behavior](#context-behavior) option to `"isolated"`, which automatically applies the `only` modifier. This is useful if you want to make sure that components don't accidentally access the outer context.

Components can also access the outer context in their context methods like `get_template_data` by accessing the property `self.outer_context`.

## Example of Accessing Outer Context

```django
<div>
  {% component "calender" / %}
</div>
```

Assuming that the rendering context has variables such as `date`, you can use `self.outer_context` to access them from within `get_template_data`. Here's how you might implement it:

```python
class Calender(Component):

    ...

    def get_template_data(self, args, kwargs, slots, context):
        outer_field = self.outer_context["date"]
        return {
            "date": outer_fields,
        }
```

However, as a best practice, it’s recommended not to rely on accessing the outer context directly through `self.outer_context`. Instead, explicitly pass the variables to the component. For instance, continue passing the variables in the component tag as shown in the previous examples.

## Context behavior

django_components supports both Django and Vue-like behavior when it comes to passing data to and through
components. This can be configured in [context_behavior](../../../reference/settings#context_behavior).

This has two modes:

- `"django"`

    The default Django template behavior.

    Inside the [`{% fill %}`](../../../reference/template_tags#fill) tag, the context variables
    you can access are a union of:

    - All the variables that were OUTSIDE the fill tag, including any\
      [`{% with %}`](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#with) tags.
    - Any loops ([`{% for ... %}`](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#cycle))
      that the `{% fill %}` tag is part of.
    - Data returned from [`Component.get_template_data()`](../../../reference/api#django_components.Component.get_template_data)
      of the component that owns the fill tag.

- `"isolated"`

    Similar behavior to [Vue](https://vuejs.org/guide/components/slots.html#render-scope) or React,
    this is useful if you want to make sure that components don't accidentally access variables defined outside
    of the component.

    Inside the [`{% fill %}`](../../../reference/template_tags#fill) tag, you can ONLY access variables from 2 places:

    - Any loops ([`{% for ... %}`](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#cycle))
      that the `{% fill %}` tag is part of.
    - [`Component.get_template_data()`](../../../reference/api#django_components.Component.get_template_data)
      of the component which defined the template (AKA the "root" component).

!!! warning

    Notice that the component whose `get_template_data()` we use inside
    [`{% fill %}`](../../../reference/template_tags#fill)
    is NOT the same across the two modes!

    Consider this example:

    ```djc_py
    class Outer(Component):
        template = """
          <div>
            {% component "inner" %}
              {% fill "content" %}
                {{ my_var }}
              {% endfill %}
            {% endcomponent %}
          </div>
        """
    ```

    - `"django"` - `my_var` has access to data from `get_template_data()` of both `Inner` and `Outer`.
      If there are variables defined in both, then `Inner` overshadows `Outer`.

    - `"isolated"` - `my_var` has access to data from `get_template_data()` of ONLY `Outer`.


### Example "django"

Given this template:

```djc_py
@register("root_comp")
class RootComp(Component):
    template = """
        {% with cheese="feta" %}
            {% component 'my_comp' %}
                {{ my_var }}  # my_var
                {{ cheese }}  # cheese
            {% endcomponent %}
        {% endwith %}
    """

    def get_template_data(self, args, kwargs, slots, context):
        return { "my_var": 123 }
```

Then if [`get_template_data()`](../../../reference/api#django_components.Component.get_template_data)
of the component `"my_comp"` returns following data:

```py
{ "my_var": 456 }
```

Then the template will be rendered as:

```django
456   # my_var
feta  # cheese
```

Because `"my_comp"` overshadows the outer variable `"my_var"`,
so `{{ my_var }}` equals `456`.

And variable `"cheese"` equals `feta`, because the fill CAN access
all the data defined in the outer layers, like the `{% with %}` tag.

### Example "isolated"

Given this template:

```djc_py
class RootComp(Component):
    template = """
        {% with cheese="feta" %}
            {% component 'my_comp' %}
                {{ my_var }}  # my_var
                {{ cheese }}  # cheese
            {% endcomponent %}
        {% endwith %}
    """

    def get_template_data(self, args, kwargs, slots, context):
        return { "my_var": 123 }
```

Then if [`get_template_data()`](../../../reference/api#django_components.Component.get_template_data)
of the component `"my_comp"` returns following data:

```py
{ "my_var": 456 }
```

Then the template will be rendered as:

```django
123   # my_var
    # cheese
```

Because variables `"my_var"` and `"cheese"` are searched only inside `RootComponent.get_template_data()`.
But since `"cheese"` is not defined there, it's empty.

!!! info

    Notice that the variables defined with the [`{% with %}`](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#with)
    tag are ignored inside the [`{% fill %}`](../../../reference/template_tags#fill) tag with the `"isolated"` mode.
