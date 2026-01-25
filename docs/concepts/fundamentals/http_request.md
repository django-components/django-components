The most common use of django-components is to render HTML when the server receives a request. As such,
there are a few features that are dependent on the request object.

## Passing the HttpRequest object

In regular Django templates, the request object is available only within the [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext).

In Components, you can either use [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext), or pass the `request` object
explicitly to [`Component.render()`](../../reference/api.md#django_components.Component.render) and
[`Component.render_to_response()`](../../reference/api.md#django_components.Component.render_to_response).

So the request object is available to components either when:

- The component is rendered with [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext) (Regular Django behavior)
- The component is rendered with a regular [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context) (or none), but you set the `request` kwarg
    of [`Component.render()`](../../reference/api.md#django_components.Component.render).
- The component is nested and the parent has access to the request object.

```python
# ✅ With request
MyComponent.render(request=request)
MyComponent.render(context=RequestContext(request, {}))

# ❌ Without request
MyComponent.render()
MyComponent.render(context=Context({}))
```

When a component is rendered within a template with [`{% component %}`](../../reference/template_tags.md#component) tag, the request object is available depending on whether the template is rendered with [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext) or not.

```python
template = Template("""
<div>
  {% component "MyComponent" / %}
</div>
""")

# ❌ No request
rendered = template.render(Context({}))

# ✅ With request
rendered = template.render(RequestContext(request, {}))
```

## Accessing the HttpRequest object

When the component has access to the `request` object, the request object will be available in [`Component.request`](../../reference/api.md#django_components.Component.request).

```python
class MyComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            'user_id': self.request.GET['user_id'],
        }
```

## Context Processors

Components support Django's [context processors](https://docs.djangoproject.com/en/5.2/ref/templates/api/#using-requestcontext).

In regular Django templates, the context processors are applied only when the template is rendered with [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext).

In Components, the context processors are applied when the component has access to the `request` object.

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

You can also access the context processors data from within [`get_template_data()`](../../reference/api.md#django_components.Component.get_template_data) and other methods under [`Component.context_processors_data`](../../reference/api.md#django_components.Component.context_processors_data).

```python
class MyComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        csrf_token = self.context_processors_data['csrf_token']
        return {
            'csrf_token': csrf_token,
        }
```

This is a dictionary with the context processors data.

If the request object is not available, then [`self.context_processors_data`](../../reference/api.md#django_components.Component.context_processors_data) will be an empty dictionary.

!!! warning

    The [`self.context_processors_data`](../../reference/api.md#django_components.Component.context_processors_data) object is generated dynamically, so changes to it are not persisted.
