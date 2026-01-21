All template tags in django_component, like `{% component %}` or `{% slot %}`, and so on,
support extra syntax that makes it possible to write components like in Vue or React (JSX).

## Self-closing tags

When you have a tag like `{% component %}` or `{% slot %}`, but it has no content, you can simply append a forward slash `/` at the end, instead of writing out the closing tags like `{% endcomponent %}` or `{% endslot %}`:

So this:

```django
{% component "button" %}{% endcomponent %}
```

becomes

```django
{% component "button" / %}
```

## Special characters

_New in version 0.71_:

Keyword arguments can contain special characters `# @ . - _`, so keywords like
so are still valid:

```django
<body>
    {% component "calendar" my-date="2015-06-19" @click.native=do_something #some_id=True / %}
</body>
```

These can then be accessed inside `get_template_data` so:

```py
@register("calendar")
class Calendar(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs["my-date"],
            "id": kwargs["#some_id"],
            "on_click": kwargs["@click.native"]
        }
```

## Spread operator

_New in version 0.93_:

Instead of passing keyword arguments one-by-one:

```django
{% component "calendar" title="How to abc" date="2015-06-19" author="John Wick" / %}
```

You can use a spread operator `...dict` to apply key-value pairs from a dictionary:

```py
post_data = {
    "title": "How to...",
    "date": "2015-06-19",
    "author": "John Wick",
}
```

```django
{% component "calendar" ...post_data / %}
```

This behaves similar to [JSX's spread operator](https://kevinyckim33.medium.com/jsx-spread-operator-component-props-meaning-3c9bcadd2493)
or [Vue's `v-bind`](https://vuejs.org/api/built-in-directives.html#v-bind).

Spread operators are treated as keyword arguments, which means that:

1. Spread operators must come after positional arguments.
2. You cannot use spread operators for [positional-only arguments](https://martinxpn.medium.com/positional-only-and-keyword-only-arguments-in-python-37-100-days-of-python-310c311657b0).

Other than that, you can use spread operators multiple times, and even put keyword arguments in-between or after them:

```django
{% component "calendar" ...post_data id=post.id ...extra / %}
```

In a case of conflicts, the values added later (right-most) overwrite previous values.

## Nested templates

_New in version 0.93_

When passing data around, sometimes you may need to do light transformations, like negating booleans or filtering lists.

Normally, what you would have to do is to define ALL the variables
inside `get_template_data()`. But this can get messy if your components contain a lot of logic.

```py
@register("calendar")
class Calendar(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "editable": kwargs["editable"],
            "readonly": not kwargs["editable"],
            "input_id": f"input-{kwargs['id']}",
            "icon_id": f"icon-{kwargs['id']}",
            ...
        }
```

Instead, template tags in django_components (`{% component %}`, `{% slot %}`, `{% provide %}`, etc) allow you to treat literal string values as templates:

```django
{% component 'blog_post'
  "As positional arg {# yay #}"
  title="{{ person.first_name }} {{ person.last_name }}"
  id="{% random_int 10 20 %}"
  readonly="{{ editable|not }}"
  author="John Wick {# TODO: parametrize #}"
/ %}
```

In the example above, the component receives:

-  Positional argument `"As positional arg "` (Comment omitted)
- `title` - passed as `str`, e.g. `John Doe`
- `id` - passed as `int`, e.g. `15`
- `readonly` - passed as `bool`, e.g. `False`
- `author` - passed as `str`, e.g. `John Wick ` (Comment omitted)

This is inspired by [django-cotton](https://github.com/wrabit/django-cotton#template-expressions-in-attributes).

### Passing data as string vs original values

In the example above, the kwarg `id` was passed as an integer, NOT a string.

When the string literal contains only a single template tag, with no extra text (and no extra whitespace),
then the value is passed as the original type instead of a string.

Here, `page` is an integer:

```django
{% component 'blog_post' page="{% random_int 10 20 %}" / %}
```

Here, `page` is a string:

```django
{% component 'blog_post' page=" {% random_int 10 20 %} " / %}
```

And same applies to the `{{ }}` variable tags:

Here, `items` is a list:

```django
{% component 'cat_list' items="{{ cats|slice:':2' }}" / %}
```

Here, `items` is a string:

```django
{% component 'cat_list' items="{{ cats|slice:':2' }} See more" / %}
```

### Evaluating Python expressions in template

You can even go a step further and have a similar experience to Vue or React,
where you can evaluate arbitrary code expressions:

```jsx
<MyForm value={isEnabled ? inputValue : null} />
```

Similar is possible with [`django-expr`](https://pypi.org/project/django-expr/), which adds an `expr` tag and filter that you can use to evaluate Python expressions from within the template:

```django
{% component "my_form"
  value="{% expr 'input_value if is_enabled else None' %}"
/ %}
```

> Note: Never use this feature to mix business logic and template logic. Business logic should still be in the view!

## Pass dictonary by its key-value pairs

_New in version 0.74_:

Sometimes, a component may expect a dictionary as one of its inputs.

Most commonly, this happens when a component accepts a dictionary
of HTML attributes (usually called `attrs`) to pass to the underlying template.

In such cases, we may want to define some HTML attributes statically, and other dynamically.
But for that, we need to define this dictionary on Python side:

```djc_py
@register("my_comp")
class MyComp(Component):
    template = """
        {% component "other" attrs=attrs / %}
    """

    def get_template_data(self, args, kwargs, slots, context):
        attrs = {
            "class": "pa-4 flex",
            "data-some-id": kwargs["some_id"],
            "@click.stop": "onClickHandler",
        }
        return {"attrs": attrs}
```

But as you can see in the case above, the event handler `@click.stop` and styling `pa-4 flex`
are disconnected from the template. If the component grew in size and we moved the HTML
to a separate file, we would have hard time reasoning about the component's template.

Luckily, there's a better way.

When we want to pass a dictionary to a component, we can define individual key-value pairs
as component kwargs, so we can keep all the relevant information in the template. For that,
we prefix the key with the name of the dict and `:`. So key `class` of input `attrs` becomes
`attrs:class`. And our example becomes:

```djc_py
@register("my_comp")
class MyComp(Component):
    template = """
        {% component "other"
            attrs:class="pa-4 flex"
            attrs:data-some-id=some_id
            attrs:@click.stop="onClickHandler"
        / %}
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {"some_id": kwargs["some_id"]}
```

Sweet! Now all the relevant HTML is inside the template, and we can move it to a separate file with confidence:

```django
{% component "other"
    attrs:class="pa-4 flex"
    attrs:data-some-id=some_id
    attrs:@click.stop="onClickHandler"
/ %}
```

> Note: It is NOT possible to define nested dictionaries, so
> `attrs:my_key:two=2` would be interpreted as:
>
> ```py
> {"attrs": {"my_key:two": 2}}
> ```

## Multiline tags

By default, Django expects a template tag to be defined on a single line.

However, this can become unwieldy if you have a component with a lot of inputs:

```django
{% component "card" title="Joanne Arc" subtitle="Head of Kitty Relations" date_last_active="2024-09-03" ... %}
```

Instead, when you install django_components, it automatically configures Django
to suport multi-line tags.

So we can rewrite the above as:

```django
{% component "card"
    title="Joanne Arc"
    subtitle="Head of Kitty Relations"
    date_last_active="2024-09-03"
    ...
%}
```

Much better!

To disable this behavior, set [`COMPONENTS.multiline_tag`](#multiline_tags---enabledisable-multiline-support) to `False`
