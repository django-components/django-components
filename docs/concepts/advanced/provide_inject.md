_New in version 0.80_:

`django-components` supports the provide / inject pattern, similarly to React's [Context Providers](https://react.dev/learn/passing-data-deeply-with-context) or Vue's [provide / inject](https://vuejs.org/guide/components/provide-inject).

This is achieved with the combination of:

- [`{% provide %}`](../../../reference/template_tags/#provide) tag
- [`Component.inject()`](../../../reference/api/#django_components.Component.inject) method

## What is "prop drilling"

Prop drilling refers to a scenario in UI development where you need to pass data through many layers of a component tree to reach the nested components that actually need the data.

Normally, you'd use props to send data from a parent component to its children. However, this straightforward method becomes cumbersome and inefficient if the data has to travel through many levels or if several components scattered at different depths all need the same piece of information.

This results in a situation where the intermediate components, which don't need the data for their own functioning, end up having to manage and pass along these props. This clutters the component tree and makes the code verbose and harder to manage.

A neat solution to avoid prop drilling is using the "provide and inject" technique.

With provide / inject, a parent component acts like a data hub for all its descendants. This setup allows any component, no matter how deeply nested it is, to access the required data directly from this centralized provider without having to messily pass props down the chain. This approach significantly cleans up the code and makes it easier to maintain.

This feature is inspired by Vue's [Provide / Inject](https://vuejs.org/guide/components/provide-inject) and React's [Context / useContext](https://react.dev/learn/passing-data-deeply-with-context).

As the name suggest, using provide / inject consists of 2 steps

1. Providing data
2. Injecting provided data

For examples of advanced uses of provide / inject, [see this discussion](https://github.com/django-components/django-components/pull/506#issuecomment-2132102584).

## Providing data

First we use the [`{% provide %}`](../../../reference/template_tags/#provide) tag to define the data we want to "provide" (make available).

```django
{% provide "my_data" hello="hi" another=123 %}
    {% component "child" / %}  <--- Can access "my_data"
{% endprovide %}

{% component "child" / %}  <--- Cannot access "my_data"
```

The first argument to the [`{% provide %}`](../../../reference/template_tags/#provide) tag is the _key_ by which we can later access the data passed to this tag. The key in this case is `"my_data"`.

The key must resolve to a valid identifier (AKA a valid Python variable name).

Next you define the data you want to "provide" by passing them as keyword arguments. This is similar to how you pass data to the [`{% with %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#with) tag or the [`{% slot %}`](../../../reference/template_tags/#slot) tag.

!!! note

    Kwargs passed to `{% provide %}` are NOT added to the context.
    In the example below, the `{{ hello }}` won't render anything:

    ```django
    {% provide "my_data" hello="hi" another=123 %}
        {{ hello }}
    {% endprovide %}
    ```

Similarly to [slots and fills](../../fundamentals/slots/#dynamic-slots-and-fills), also provide's name argument can be set dynamically via a variable, a template expression, or a spread operator:

```django
{% with my_name="my_name" %}
    {% provide name=my_name ... %}
        ...
    {% endprovide %}
{% endwith %}
```

## Injecting data

To "inject" (access) the data defined on the [`{% provide %}`](../../../reference/template_tags/#provide) tag,
you can use the [`Component.inject()`](../../../reference/api/#django_components.Component.inject) method from within any other component methods.

For a component to be able to "inject" some data, the component ([`{% component %}`](../../../reference/template_tags/#component) tag) must be nested inside the [`{% provide %}`](../../../reference/template_tags/#provide) tag.

In the example from previous section, we've defined two kwargs: `hello="hi" another=123`. That means that if we now inject `"my_data"`, we get an object with 2 attributes - `hello` and `another`.

```py
class ChildComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        my_data = self.inject("my_data")
        print(my_data.hello)    # hi
        print(my_data.another)  # 123
        return {}
```

First argument to [`Component.inject()`](../../../reference/api/#django_components.Component.inject) is the _key_ (or _name_) of the provided data. This
must match the string that you used in the [`{% provide %}`](../../../reference/template_tags/#provide) tag.

If no provider with given key is found, [`inject()`](../../../reference/api/#django_components.Component.inject) raises a `KeyError`.

To avoid the error, you can pass a second argument to [`inject()`](../../../reference/api/#django_components.Component.inject). This will act as a default value similar to `dict.get(key, default)`:

```py
class ChildComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        my_data = self.inject("invalid_key", DEFAULT_DATA)
        assert my_data == DEFAULT_DATA
        return {}
```

!!! note

    The instance returned from [`inject()`](../../../reference/api/#django_components.Component.inject) is immutable (subclass of [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)). This ensures that the data returned from [`inject()`](../../../reference/api/#django_components.Component.inject) will always
    have all the keys that were passed to the [`{% provide %}`](../../../reference/template_tags/#provide) tag.

!!! warning

    [`inject()`](../../../reference/api/#django_components.Component.inject) works strictly only during render execution. If you try to call `inject()` from outside, it will raise an error.

## Full example

```djc_py
@register("child")
class ChildComponent(Component):
    template = """
        <div> {{ my_data.hello }} </div>
        <div> {{ my_data.another }} </div>
    """

    def get_template_data(self, args, kwargs, slots, context):
        my_data = self.inject("my_data", "default")
        return {"my_data": my_data}

template_str = """
    {% load component_tags %}
    {% provide "my_data" hello="hi" another=123 %}
        {% component "child" / %}
    {% endprovide %}
"""
```

renders:

```html
<div>hi</div>
<div>123</div>
```
