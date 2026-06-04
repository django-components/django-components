---
title: Form handling
---

# Form handling

Components can handle form submissions via `Component.View`:

```python
from django_components import Component, register

@register("contact_form")
class ContactForm(Component):
    template = """
        <form method="post" action="{{ form_url }}">
            {% csrf_token %}
            <input name="email" placeholder="Email">
            <button type="submit">Submit</button>
        </form>
    """

    class View:
        public = True

        def post(self, request):
            email = request.POST.get("email", "")
            return HttpResponse(f"Thanks, {email}!")
```

!!! warning
    Set `public = True` on the View class to expose the endpoint. Without it,
    the form submission URL won't be registered.
