# Signals

Below are the signals that are sent by or during the use of django-components.

## template_rendered

Django's [`template_rendered`](https://docs.djangoproject.com/en/5.2/ref/signals/#template-rendered) signal.
This signal is sent when a template is rendered.

Django-components triggers this signal when a component is rendered. If there are nested components,
the signal is triggered for each component.

Import from django as `django.test.signals.template_rendered`.

```djc_py
from django.test.signals import template_rendered

# Setup a callback function
def my_callback(sender, **kwargs):
    ...

template_rendered.connect(my_callback)

class MyTable(Component):
    template = """
    <table>
        <tr>
            <th>Header</th>
        </tr>
        <tr>
            <td>Cell</td>
        </tr>
    """

# This will trigger the signal
MyTable().render()
```
