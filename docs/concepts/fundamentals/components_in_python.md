_New in version 0.81_

Components can be rendered outside of Django templates, calling them as regular functions ("React-style").

The component class defines `render` and `render_to_response` class methods. These methods accept positional args, kwargs, and slots, offering the same flexibility as the `{% component %}` tag:

```djc_py
class SimpleComponent(Component):
    template = """
        {% load component_tags %}
        hello: {{ hello }}
        foo: {{ foo }}
        kwargs: {{ kwargs|safe }}
        slot_first: {% slot "first" required / %}
    """

    def get_context_data(self, arg1, arg2, **kwargs):
        return {
            "hello": arg1,
            "foo": arg2,
            "kwargs": kwargs,
        }

rendered = SimpleComponent.render(
    args=["world", "bar"],
    kwargs={"kw1": "test", "kw2": "ooo"},
    slots={"first": "FIRST_SLOT"},
    context={"from_context": 98},
)
```

Renders:

```
hello: world
foo: bar
kwargs: {'kw1': 'test', 'kw2': 'ooo'}
slot_first: FIRST_SLOT
```

## Inputs of `render` and `render_to_response`

Both `render` and `render_to_response` accept the same input:

```py
Component.render(
    context: Mapping | django.template.Context | None = None,
    args: List[Any] | None = None,
    kwargs: Dict[str, Any] | None = None,
    slots: Dict[str, str | SafeString | SlotFunc] | None = None,
    escape_slots_content: bool = True
) -> str:
```

- _`args`_ - Positional args for the component. This is the same as calling the component
  as `{% component "my_comp" arg1 arg2 ... %}`

- _`kwargs`_ - Keyword args for the component. This is the same as calling the component
  as `{% component "my_comp" key1=val1 key2=val2 ... %}`

- _`slots`_ - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
  Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
  or [`SlotFunc`](#slotfunc).

- _`escape_slots_content`_ - Whether the content from `slots` should be escaped. `True` by default to prevent XSS attacks. If you disable escaping, you should make sure that any content you pass to the slots is safe, especially if it comes from user input.

- _`context`_ - A context (dictionary or Django's Context) within which the component
  is rendered. The keys on the context can be accessed from within the template.
  - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
    component's args and kwargs.

- _`request`_ - A Django request object. This is used to enable Django template `context_processors` to run,  
  allowing for template tags like `{% csrf_token %}` and variables like `{{ debug }}`.  
  - Similar behavior can be achieved with [provide / inject](#how-to-use-provide--inject).
  - This is used internally to convert `context` to a RequestContext. It does nothing if `context` is already 
    a `Context` instance.

### `SlotFunc`

When rendering components with slots in `render` or `render_to_response`, you can pass either a string or a function.

The function has following signature:

```py
def render_func(
   context: Context,
   data: Dict[str, Any],
   slot_ref: SlotRef,
) -> str | SafeString:
    return nodelist.render(ctx)
```

- _`context`_ - Django's Context available to the Slot Node.
- _`data`_ - Data passed to the `{% slot %}` tag. See [Scoped Slots](#scoped-slots).
- _`slot_ref`_ - The default slot content. See [Accessing original content of slots](#accessing-original-content-of-slots).
  - NOTE: The slot is lazily evaluated. To render the slot, convert it to string with `str(slot_ref)`.

Example:

```py
def footer_slot(ctx, data, slot_ref):
   return f"""
      SLOT_DATA: {data['abc']}
      ORIGINAL: {slot_ref}
   """

MyComponent.render_to_response(
    slots={
        "footer": footer_slot,
   },
)
```

## Response class of `render_to_response`

While `render` method returns a plain string, `render_to_response` wraps the rendered content in a "Response" class. By default, this is `django.http.HttpResponse`.

If you want to use a different Response class in `render_to_response`, set the `Component.response_class` attribute:

```py
class MyResponse(HttpResponse):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Configure response
        self.headers = ...
        self.status = ...

class SimpleComponent(Component):
    response_class = MyResponse
    template: types.django_html = "HELLO"

response = SimpleComponent.render_to_response()
assert isinstance(response, MyResponse)
```
