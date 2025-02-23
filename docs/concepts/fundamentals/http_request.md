The most common use of django-components is to render HTML for a given request. As such,
there are a few features that are dependent on the request object.

## Passing and accessing HttpRequest

In regular Django templates, the request object is available only within the `RequestContext`.

In Components, you can either use `RequestContext`, or pass the `request` object
explicitly to [`Component.render()`](../../../reference/api#django_components.Component.render) and
[`Component.render_to_response()`](../../../reference/api#django_components.Component.render_to_response).

When a component is nested in another, the child component uses parent's `request` object.

You can access the request object under [`Component.request`](../../../reference/api#django_components.Component.request):

```python
class MyComponent(Component):
    def get_context_data(self):
        return {
            'user_id': self.request.GET['user_id'],
        }

# ✅ With request
MyComponent.render(request=request)
MyComponent.render(context=RequestContext(request, {}))

# ❌ Without request
MyComponent.render()
MyComponent.render(context=Context({}))
```

## Context Processors

Components support Django's [context processors](https://docs.djangoproject.com/en/5.1/ref/templates/api/#using-requestcontext).

In regular Django templates, the context processors are applied only when the template is rendered with `RequestContext`.

Components allow you to pass the `request` object explicitly. Thus, the context processors are applied to components either when:

- The component is rendered with `RequestContext` (Regular Django behavior)
- The component is rendered with a regular `Context` (or none), but you set the `request` kwarg
    of [`Component.render()`](../../../reference/api#django_components.Component.render).
- The component is nested in another component that matches one of the two conditions above.

```python
# ❌ No context processors
rendered = MyComponent.render()
rendered = MyComponent.render(Context({}))

# ✅ With context processors
rendered = MyComponent.render(request=request)
rendered = MyComponent.render(Context({}), request=request)
rendered = MyComponent.render(RequestContext(request, {}))
```

When a component is rendered within a template with [`{% component %}`](../../../reference/template_tags#component) tag, context processors are available depending on whether the template is rendered with `RequestContext` or not.

```python
template = Template("""
<div>
  {% component "MyComponent" / %}
</div>
""")

# ❌ No context processors
rendered = template.render(Context({}))

# ✅ With context processors
rendered = template.render(RequestContext(request, {}))
```

### Accessing context processors data

The data from context processors is automatically available within the component's template.

```djc_py
class MyComponent(Component):
    template = """
        <div>
            {{ csrf_token }}
        </div>
    """

MyComponent.render(request=request)
```

You can also access the context processors data from within [`get_context_data()`](../../../reference/api#django_components.Component.get_context_data) and other methods under [`Component.context_processors_data`](../../../reference/api#django_components.Component.context_processors_data).

```python
class MyComponent(Component):
    def get_context_data(self):
        csrf_token = self.context_processors_data['csrf_token']
        return {
            'csrf_token': csrf_token,
        }
```
