# Python Expressions

Python expressions allow you to evaluate Python code directly in templates by wrapping the expression in parentheses. This provides a Vue/React-like experience for writing component templates.

## How it works

When you use parentheses `()` in a template tag attribute, the content inside is treated as a Python expression and evaluated in the template context.

```django
{% component "button" disabled=(not editable) %}
```

In the example above, `(not editable)` is evaluated as a Python expression, so if `editable` is `False`, then `disabled` will be `True`.

## Basic syntax

Python expressions are simply Python code wrapped in parentheses:

```django
{% component "button"
    disabled=(not editable)
    variant=(user.is_admin and 'danger' or 'primary')
    size=(name.upper() if name else 'medium')
/ %}
```

## Common use cases

### Negating booleans

```django
{% component "button" disabled=(not editable) / %}
```

### Conditional expressions

```django
{% component "button"
    variant=(user.is_admin and 'danger' or 'primary')
/ %}
```

### Method calls

```django
{% component "button" text=(name.upper()) / %}
```

### Complex expressions

```django
{% component "user_card"
    is_active=(user.status == 'active')
    score=(user.points + bonus_points)
/ %}
```

## Comparison with alternatives

### Without Python expressions

Without Python expressions, you would need to compute values in `get_template_data()`:

```py
@register("button")
class Button(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "disabled": not kwargs["editable"],
            "variant": "danger" if kwargs["user"].is_admin else "primary",
        }
```

### With Python expressions

With Python expressions, you can evaluate directly in the template:

```django
{% component "button"
    disabled=(not editable)
    variant=(user.is_admin and 'danger' or 'primary')
/ %}
```

This keeps the logic closer to where it's used and reduces boilerplate in `get_template_data()`.

## Best practices

1. **Use for simple transformations**: Python expressions are best for simple conditionals, negations, and basic operations.

2. **Keep complex logic in Python**: Complex business logic should still be in `get_template_data()` or views, not in templates.

3. **Context access**: Python expressions have access to the template context, so you can use any variables available in the context.

4. **Performance**: Expressions are cached for performance, so repeated evaluations of the same expression are fast.

5. **Readability**: Use Python expressions when they make the template more readable. If an expression becomes too complex, consider moving it to `get_template_data()`.

## Definition

```djc_py
--8<-- "docs/examples/python_expressions/component.py"
```

## Example

To see the component in action, you can set up a view and a URL pattern as shown below.

### `views.py`

```djc_py
--8<-- "docs/examples/python_expressions/page.py"
```

### `urls.py`

```python
from django.urls import path

from docs.examples.python_expressions.page import PythonExpressionsPage

urlpatterns = [
    path("examples/python_expressions", PythonExpressionsPage.as_view(), name="python_expressions"),
]
```