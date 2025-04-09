_New in version 0.74_:

You can use the [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag to render various data
as `key="value"` HTML attributes.

[`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag is versatile, allowing you to define HTML attributes however you need:

- Define attributes within the HTML template
- Define attributes in Python code
- Merge attributes from multiple sources
- Boolean attributes
- Append attributes
- Remove attributes
- Define default attributes

From v0.135 onwards, [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag also supports merging [`style`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/style) and [`class`](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/class) attributes
the same way [how Vue does](https://vuejs.org/guide/essentials/class-and-style).

To get started, let's consider a simple example. If you have a template:

```django
<div class="{{ classes }}" data-id="{{ my_id }}">
</div>
```

You can rewrite it with the [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag:

```django
<div {% html_attrs class=classes data-id=my_id %}>
</div>
```

The [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag accepts any number of keyword arguments, which will be merged and rendered as HTML attributes:

```django
<div class="text-red" data-id="123">
</div>
```

Moreover, the [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag accepts two positional arguments:

- `attrs` - a dictionary of attributes to be rendered
- `defaults` - a dictionary of default attributes

You can use this for example to allow users of your component to add extra attributes. We achieve this by capturing the extra attributes and passing them to the [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag as a dictionary:

```djc_py
@register("my_comp")
class MyComp(Component):
    # Capture extra kwargs in `attrs`
    def get_context_data(self, **attrs):
        return {
            "attrs": attrs,
            "classes": "text-red",
            "my_id": 123,
        }

    template: t.django_html = """
        {# Pass the extra attributes to `html_attrs` #}
        <div {% html_attrs attrs class=classes data-id=my_id %}>
        </div>
    """
```

This way you can render `MyComp` with extra attributes:

Either via Django template:

```django
{% component "my_comp"
  id="example"
  class="pa-4"
  style="color: red;"
%}
```

Or via Python:

```py
MyComp.render(
    kwargs={
        "id": "example",
        "class": "pa-4",
        "style": "color: red;",
    }
)
```

In both cases, the attributes will be merged and rendered as:

```html
<div id="example" class="text-red pa-4" style="color: red;" data-id="123"></div>
```

### Summary

1. The two arguments, `attrs` and `defaults`, can be passed as positional args:

    ```django
    {% html_attrs attrs defaults key=val %}
    ```

    or as kwargs:

    ```django
    {% html_attrs key=val defaults=defaults attrs=attrs %}
    ```

2. Both `attrs` and `defaults` are optional and can be omitted.

3. Both `attrs` and `defaults` are dictionaries. As such, there's multiple ways to define them:

    - By referencing a variable:

        ```django
        {% html_attrs attrs=attrs %}
        ```

    - By defining a literal dictionary:

        ```django
        {% html_attrs attrs={"key": value} %}
        ```

    - Or by defining the [dictionary keys](../template_tag_syntax/#pass-dictonary-by-its-key-value-pairs):

        ```django
        {% html_attrs attrs:key=value %}
        ```

4. All other kwargs are merged and can be repeated.

    ```django
    {% html_attrs class="text-red" class="pa-4" %}
    ```

    Will render:

    ```html
    <div class="text-red pa-4"></div>
    ```

## Usage

### Boolean attributes

In HTML, boolean attributes are usually rendered with no value. Consider the example below where the first button is disabled and the second is not:

```html
<button disabled>Click me!</button>
<button>Click me!</button>
```

HTML rendering with [`html_attrs`](../../../reference/template_tags#html_attrs) tag or [`format_attributes`](../../../reference/api#django_components.format_attributes) works the same way - an attribute set to `True` is rendered without the value, and an attribute set to `False` is not rendered at all.

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

### Removing attributes

Given how the boolean attributes work, you can "remove" or prevent an attribute from being rendered by setting it to `False` or `None`.

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

### Default attributes

Sometimes you may want to specify default values for attributes. You can pass a second positional argument to set the defaults.

```django
<div {% html_attrs attrs defaults %}>
    ...
</div>
```

In the example above, if `attrs` contains a certain key, e.g. the `class` key, [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) will render:

```html
<div class="{{ attrs.class }}">
    ...
</div>
```

Otherwise, [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) will render:

```html
<div class="{{ defaults.class }}">
    ...
</div>
```

### Appending attributes

For the `class` HTML attribute, it's common that we want to _join_ multiple values,
instead of overriding them.

For example, if you're authoring a component, you may
want to ensure that the component will ALWAYS have a specific class. Yet, you may
want to allow users of your component to supply their own `class` attribute.

We can achieve this by adding extra kwargs. These values
will be appended, instead of overwriting the previous value.

So if we have a variable `attrs`:

```py
attrs = {
    "class": "my-class pa-4",
}
```

And on [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag, we set the key `class`:

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

### Merging `class` attributes

The `class` attribute can be specified as a string of class names as usual.

If you want granular control over individual class names, you can use a dictionary.

- **String**: Used as is.

    ```django
    {% html_attrs class="my-class other-class" %}
    ```

    Renders:

    ```html
    <div class="my-class other-class"></div>
    ```

- **Dictionary**: Keys are the class names, and values are booleans. Only keys with truthy values are rendered.

    ```django
    {% html_attrs class={
        "extra-class": True,
        "other-class": False,
    } %}
    ```

    Renders:

    ```html
    <div class="extra-class"></div>
    ```

If a certain class is specified multiple times, it's the last instance that decides whether the class is rendered or not.

**Example:**

In this example, the `other-class` is specified twice. The last instance is `{"other-class": False}`, so the class is not rendered.

```django
{% html_attrs
    class="my-class other-class"
    class={"extra-class": True, "other-class": False}
%}
```

Renders:

```html
<div class="my-class extra-class"></div>
```

### Merging `style` attributes

The `style` attribute can be specified as a string of style properties as usual.

If you want granular control over individual style properties, you can use a dictionary.

- **String**: Used as is.

    ```django
    {% html_attrs style="color: red; background-color: blue;" %}
    ```

    Renders:

    ```html
    <div style="color: red; background-color: blue;"></div>
    ```

- **Dictionary**: Keys are the style properties, and values are their values.

    ```django
    {% html_attrs style={
        "color": "red",
        "background-color": "blue",
    } %}
    ```

    Renders:

    ```html
    <div style="color: red; background-color: blue;"></div>
    ```

If a style property is specified multiple times, the last value is used.

- Properties set to `None` are ignored.
- If the last non-`None` instance of the property is set to `False`, the property is removed.

**Example:**

In this example, the `width` property is specified twice. The last instance is `{"width": False}`, so the property is removed.

Secondly, the `background-color` property is also set twice. But the second time it's set to `None`, so that instance is ignored, leaving us only with `background-color: blue`.

The `color` property is set to a valid value in both cases, so the latter (`green`) is used.

```django
{% html_attrs
    style="color: red; background-color: blue; width: 100px;"
    style={"color": "green", "background-color": None, "width": False}
%}
```

Renders:

```html
<div style="color: green; background-color: blue;"></div>
```

## Usage outside of templates

In some cases, you want to prepare HTML attributes outside of templates.

To achieve the same behavior as [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag, you can use the [`merge_attributes()`](../../../reference/api#django_components.merge_attributes) and [`format_attributes()`](../../../reference/api#django_components.format_attributes) helper functions.

### Merging attributes

[`merge_attributes()`](../../../reference/api#django_components.merge_attributes) accepts any number of dictionaries and merges them together, using the same merge strategy as [`{% html_attrs %}`](../../../reference/template_tags#html_attrs).

```python
from django_components import merge_attributes

merge_attributes(
    {"class": "my-class", "data-id": 123},
    {"class": "extra-class"},
    {"class": {"cool-class": True, "uncool-class": False} },
)
```

Which will output:

```python
{
    "class": "my-class extra-class cool-class",
    "data-id": 123,
}
```

!!! warning

    Unlike [`{% html_attrs %}`](../../../reference/template_tags#html_attrs), where you can pass extra kwargs, [`merge_attributes()`](../../../reference/api#django_components.merge_attributes) requires each argument to be a dictionary.

### Formatting attributes

[`format_attributes()`](../../../reference/api#django_components.format_attributes) serializes attributes the same way as [`{% html_attrs %}`](../../../reference/template_tags#html_attrs) tag does.

```py
from django_components import format_attributes

format_attributes({
    "class": "my-class text-red pa-4",
    "data-id": 123,
    "required": True,
    "disabled": False,
    "ignored-attr": None,
})
```

Which will output:

```python
'class="my-class text-red pa-4" data-id="123" required'
```

!!! note

    Prior to v0.135, the `format_attributes()` function was named `attributes_to_string()`.

    This function is now deprecated and will be removed in v1.0.

## Cheat sheet

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

- **Empty tag**
  
    ```django
    <div {% html_attr %}></div>
    ```

    renders nothing:

    ```html
    <div></div>
    ```

- **Only kwargs**
  
    ```django
    <div {% html_attr class="some-class" class=class_from_var data-id="123" %}></div>
    ```

    renders:

    ```html
    <div class="some-class from-var" data-id="123"></div>
    ```

- **Only attrs**

    ```django
    <div {% html_attr attrs %}></div>
    ```

    renders:

    ```html
    <div class="from-attrs" type="submit"></div>
    ```

- **Attrs as kwarg**

    ```django
    <div {% html_attr attrs=attrs %}></div>
    ```

    renders:

    ```html
    <div class="from-attrs" type="submit"></div>
    ```

- **Only defaults (as kwarg)**

    ```django
    <div {% html_attr defaults=defaults %}></div>
    ```

    renders:

    ```html
    <div class="from-defaults" role="button"></div>
    ```

- **Attrs using the `prefix:key=value` construct**

    ```django
    <div {% html_attr attrs:class="from-attrs" attrs:type="submit" %}></div>
    ```

    renders:

    ```html
    <div class="from-attrs" type="submit"></div>
    ```

- **Defaults using the `prefix:key=value` construct**

    ```django
    <div {% html_attr defaults:class="from-defaults" %}></div>
    ```

    renders:

    ```html
    <div class="from-defaults" role="button"></div>
    ```

- **All together (1) - attrs and defaults as positional args:**

    ```django
    <div {% html_attrs attrs defaults class="added_class" class=class_from_var data-id=123 %}></div>
    ```

    renders:

    ```html
    <div class="from-attrs added_class from-var" type="submit" role="button" data-id=123></div>
    ```

- **All together (2) - attrs and defaults as kwargs args:**

    ```django
    <div {% html_attrs class="added_class" class=class_from_var data-id=123 attrs=attrs defaults=defaults %}></div>
    ```

    renders:

    ```html
    <div class="from-attrs added_class from-var" type="submit" role="button" data-id=123></div>
    ```

- **All together (3) - mixed:**

    ```django
    <div {% html_attrs attrs defaults:class="default-class" class="added_class" class=class_from_var data-id=123 %}></div>
    ```

    renders:

    ```html
    <div class="from-attrs added_class from-var" type="submit" data-id=123></div>
    ```

## Full example

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

```
defaults:class="pa-4 text-red"
```

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
