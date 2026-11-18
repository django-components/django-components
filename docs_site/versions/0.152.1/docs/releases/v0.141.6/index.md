---
title: v0.141.6 (2025-09-29)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.141.6/
description: "- Fix error that occured when calling Component.inject() inside loops:"
---

# v0.141.6 (2025-09-29)

#### Fix

- Fix error that occured when calling `Component.inject()` inside loops:


   ```py
   class MyComponent(Component):
       def get_template_data(self, args, kwargs, slots, context):
           data = self.inject("my_provide")
           return {"data": data}
   ```



   ```django
   {% load component_tags %}
   {% provide "my_provide" key="hi" data=data %}
       {% for i in range(10) %}
           {% component "my_component" / %}
       {% endfor %}
   {% endprovide %}
   ```


- Allow to call `Component.inject()` outside of the rendering:


   ```py
   comp = None

   class MyComponent(Component):
       def get_template_data(self, args, kwargs, slots, context):
           nonlocal comp
           comp = self

   template_str = """
       {% load component_tags %}
       {% provide "my_provide" key="hi" data=data %}
           {% component "my_component" / %}
       {% endprovide %}
   """
   template = Template(template_str)
   rendered = template.render(Context({}))

   assert comp is not None

   injected = comp.inject("my_provide")
   assert injected.key == "hi"
   assert injected.data == "data"
   ```


#### Refactor

- Removed circular references to the Component instances. Component instances
  are now garbage collected unless you keep a reference to them.