---
title: HTML Fragments
---

# HTML Fragments

Load partial HTML into a page without a full reload using HTMX, Alpine.js,
or vanilla JavaScript.

## The pattern

1. Define a component that renders a fragment of HTML
2. Expose it via `Component.View` with `public = True`
3. Use `get_component_url()` to get the endpoint URL
4. Fetch the fragment client-side and swap it into the DOM

```python title="components/counter.py"
@register("counter")
class Counter(Component):
    template = "<span>Count: {{ count }}</span>"

    class View:
        public = True

        def get(self, request):
            count = int(request.GET.get("n", 0)) + 1
            return Counter.render_to_response(kwargs={"count": count})
```

## With HTMX

```html
<div hx-get="{{ get_component_url('counter') }}" hx-trigger="click">
    Click to increment
</div>
```
