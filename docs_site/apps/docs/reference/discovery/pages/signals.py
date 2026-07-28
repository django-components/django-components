"""
Discovery for the Signals reference page (features 4.17, 4.32, 4.56).

Port of ``gen_reference_signals``. Unlike the other pages, there is nothing to
introspect: the signals django-components participates in are Django's own, so
the page is a hand-authored markdown "island" with no per-symbol entries. It
flows through the same generator as every other reference page (one uniform
pipeline) - it just carries its whole body in ``preface_md``. The leading
``# Signals`` heading is dropped here because the page generator adds the title.
"""

from __future__ import annotations

from apps.docs.reference.discovery.kinds import ReferencePage

_BODY = """\
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
    template = \"\"\"
    <table>
        <tr>
            <th>Header</th>
        </tr>
        <tr>
            <td>Cell</td>
        </tr>
    \"\"\"

# This will trigger the signal
MyTable().render()
```
"""


def discover() -> ReferencePage:
    """Build the (hand-authored) Signals ``ReferencePage``."""
    return ReferencePage(
        slug="signals",
        title="Signals",
        preface_md=_BODY,
        entries=(),
        description="API reference - Signals.",
    )
