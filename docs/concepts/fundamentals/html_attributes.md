_New in version 0.74_:

You can use the `html_attrs` tag to render HTML attributes, given a dictionary
of values.

So if you have a template:

```django
<div class="{{ classes }}" data-id="{{ my_id }}">
</div>
```

You can simplify it with `html_attrs` tag:

```django
<div {% html_attrs attrs %}>
</div>
```

where `attrs` is:

```py
attrs = {
    "class": classes,
    "data-id": my_id,
}
```

This feature is inspired by [`merge_attrs` tag of django-web-components](https://github.com/Xzya/django-web-components/tree/master?tab=readme-ov-file#default--merged-attributes) and
["fallthrough attributes" feature of Vue](https://vuejs.org/guide/components/attrs).

## Removing atttributes

Attributes that are set to `None` or `False` are NOT rendered.

So given this input:

```py
attrs = {
    "class": "text-green",
    "required": False,
    "data-id": None,
}
```

And template:

```django
<div {% html_attrs attrs %}>
</div>
```

Then this renders:

```html
<div class="text-green"></div>
```

## Boolean attributes

In HTML, boolean attributes are usually rendered with no value. Consider the example below where the first button is disabled and the second is not:

```html
<button disabled>Click me!</button> <button>Click me!</button>
```

HTML rendering with `html_attrs` tag or `attributes_to_string` works the same way, where `key=True` is rendered simply as `key`, and `key=False` is not render at all.

So given this input:

```py
attrs = {
    "disabled": True,
    "autofocus": False,
}
```

And template:

```django
<div {% html_attrs attrs %}>
</div>
```

Then this renders:

```html
<div disabled></div>
```

## Default attributes

Sometimes you may want to specify default values for attributes. You can pass a second argument (or kwarg `defaults`) to set the defaults.

```django
<div {% html_attrs attrs defaults %}>
    ...
</div>
```

In the example above, if `attrs` contains e.g. the `class` key, `html_attrs` will render:

`class="{{ attrs.class }}"`

Otherwise, `html_attrs` will render:

`class="{{ defaults.class }}"`

## Appending attributes

For the `class` HTML attribute, it's common that we want to _join_ multiple values,
instead of overriding them. For example, if you're authoring a component, you may
want to ensure that the component will ALWAYS have a specific class. Yet, you may
want to allow users of your component to supply their own classes.

We can achieve this by adding extra kwargs. These values
will be appended, instead of overwriting the previous value.

So if we have a variable `attrs`:

```py
attrs = {
    "class": "my-class pa-4",
}
```

And on `html_attrs` tag, we set the key `class`:

```django
<div {% html_attrs attrs class="some-class" %}>
</div>
```

Then these will be merged and rendered as:

```html
<div data-value="my-class pa-4 some-class"></div>
```

To simplify merging of variables, you can supply the same key multiple times, and these will be all joined together:

```django
{# my_var = "class-from-var text-red" #}
<div {% html_attrs attrs class="some-class another-class" class=my_var %}>
</div>
```

Renders:

```html
<div
  data-value="my-class pa-4 some-class another-class class-from-var text-red"
></div>
```

## Rules for `html_attrs`

1. Both `attrs` and `defaults` can be passed as positional args

   `{% html_attrs attrs defaults key=val %}`

   or as kwargs

   `{% html_attrs key=val defaults=defaults attrs=attrs %}`

2. Both `attrs` and `defaults` are optional (can be omitted)

3. Both `attrs` and `defaults` are dictionaries, and we can define them the same way [we define dictionaries for the `component` tag](#pass-dictonary-by-its-key-value-pairs). So either as `attrs=attrs` or `attrs:key=value`.

4. All other kwargs are appended and can be repeated.

## Examples for `html_attrs`

Assuming that:

```py
class_from_var = "from-var"

attrs = {
    "class": "from-attrs",
    "type": "submit",
}

defaults = {
    "class": "from-defaults",
    "role": "button",
}
```

Then:

- Empty tag <br/>
  `{% html_attr %}`

  renders (empty string): <br/>
  ` `

- Only kwargs <br/>
  `{% html_attr class="some-class" class=class_from_var data-id="123" %}`

  renders: <br/>
  `class="some-class from-var" data-id="123"`

- Only attrs <br/>
  `{% html_attr attrs %}`

  renders: <br/>
  `class="from-attrs" type="submit"`

- Attrs as kwarg <br/>
  `{% html_attr attrs=attrs %}`

  renders: <br/>
  `class="from-attrs" type="submit"`

- Only defaults (as kwarg) <br/>
  `{% html_attr defaults=defaults %}`

  renders: <br/>
  `class="from-defaults" role="button"`

- Attrs using the `prefix:key=value` construct <br/>
  `{% html_attr attrs:class="from-attrs" attrs:type="submit" %}`

  renders: <br/>
  `class="from-attrs" type="submit"`

- Defaults using the `prefix:key=value` construct <br/>
  `{% html_attr defaults:class="from-defaults" %}`

  renders: <br/>
  `class="from-defaults" role="button"`

- All together (1) - attrs and defaults as positional args: <br/>
  `{% html_attrs attrs defaults class="added_class" class=class_from_var data-id=123 %}`

  renders: <br/>
  `class="from-attrs added_class from-var" type="submit" role="button" data-id=123`

- All together (2) - attrs and defaults as kwargs args: <br/>
  `{% html_attrs class="added_class" class=class_from_var data-id=123 attrs=attrs defaults=defaults %}`

  renders: <br/>
  `class="from-attrs added_class from-var" type="submit" role="button" data-id=123`

- All together (3) - mixed: <br/>
  `{% html_attrs attrs defaults:class="default-class" class="added_class" class=class_from_var data-id=123 %}`

  renders: <br/>
  `class="from-attrs added_class from-var" type="submit" data-id=123`

## Full example for `html_attrs`

```djc_py
@register("my_comp")
class MyComp(Component):
    template: t.django_html = """
        <div
            {% html_attrs attrs
                defaults:class="pa-4 text-red"
                class="my-comp-date"
                class=class_from_var
                data-id="123"
            %}
        >
            Today's date is <span>{{ date }}</span>
        </div>
    """

    def get_context_data(self, date: Date, attrs: dict):
        return {
            "date": date,
            "attrs": attrs,
            "class_from_var": "extra-class"
        }

@register("parent")
class Parent(Component):
    template: t.django_html = """
        {% component "my_comp"
            date=date
            attrs:class="pa-0 border-solid border-red"
            attrs:data-json=json_data
            attrs:@click="(e) => onClick(e, 'from_parent')"
        / %}
    """

    def get_context_data(self, date: Date):
        return {
            "date": datetime.now(),
            "json_data": json.dumps({"value": 456})
        }
```

Note: For readability, we've split the tags across multiple lines.

Inside `MyComp`, we defined a default attribute

`defaults:class="pa-4 text-red"`

So if `attrs` includes key `class`, the default above will be ignored.

`MyComp` also defines `class` key twice. It means that whether the `class`
attribute is taken from `attrs` or `defaults`, the two `class` values
will be appended to it.

So by default, `MyComp` renders:

```html
<div class="pa-4 text-red my-comp-date extra-class" data-id="123">...</div>
```

Next, let's consider what will be rendered when we call `MyComp` from `Parent`
component.

`MyComp` accepts a `attrs` dictionary, that is passed to `html_attrs`, so the
contents of that dictionary are rendered as the HTML attributes.

In `Parent`, we make use of passing dictionary key-value pairs as kwargs to define
individual attributes as if they were regular kwargs.

So all kwargs that start with `attrs:` will be collected into an `attrs` dict.

```django
    attrs:class="pa-0 border-solid border-red"
    attrs:data-json=json_data
    attrs:@click="(e) => onClick(e, 'from_parent')"
```

And `get_context_data` of `MyComp` will receive `attrs` input with following keys:

```py
attrs = {
    "class": "pa-0 border-solid",
    "data-json": '{"value": 456}',
    "@click": "(e) => onClick(e, 'from_parent')",
}
```

`attrs["class"]` overrides the default value for `class`, whereas other keys
will be merged.

So in the end `MyComp` will render:

```html
<div
  class="pa-0 border-solid my-comp-date extra-class"
  data-id="123"
  data-json='{"value": 456}'
  @click="(e) => onClick(e, 'from_parent')"
>
  ...
</div>
```

## Rendering HTML attributes outside of templates

If you need to use serialize HTML attributes outside of Django template and the `html_attrs` tag, you can use `attributes_to_string`:

```py
from django_components.attributes import attributes_to_string

attrs = {
    "class": "my-class text-red pa-4",
    "data-id": 123,
    "required": True,
    "disabled": False,
    "ignored-attr": None,
}

attributes_to_string(attrs)
# 'class="my-class text-red pa-4" data-id="123" required'
```
