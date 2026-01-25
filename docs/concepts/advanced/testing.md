_New in version 0.131_

The [`@djc_test`](../../reference/testing_api.md#django_components.testing.djc_test) decorator is a powerful tool for testing components created with `django-components`. It ensures that each test is properly isolated, preventing components registered in one test from affecting others.

## Usage

The [`@djc_test`](../../reference/testing_api.md#django_components.testing.djc_test) decorator can be applied to functions, methods, or classes.

When applied to a class, it decorates all methods starting with `test_`, and all nested classes starting with `Test`,
recursively.

### Applying to a Function

To apply [`@djc_test`](../../reference/testing_api.md#django_components.testing.djc_test) to a function,
simply decorate the function as shown below:

```python
import django
from django_components.testing import djc_test

@djc_test
def test_my_component():
    @register("my_component")
    class MyComponent(Component):
        template = "..."
    ...
```

### Applying to a Class

When applied to a class, `djc_test` decorates each `test_` method, as well as all nested classes starting with `Test`.

```python
import django
from django_components.testing import djc_test

@djc_test
class TestMyComponent:
    def test_something(self):
        ...

    class TestNested:
        def test_something_else(self):
            ...
```

This is equivalent to applying the decorator to both of the methods individually:

```python
import django
from django_components.testing import djc_test

class TestMyComponent:
    @djc_test
    def test_something(self):
        ...

    class TestNested:
        @djc_test
        def test_something_else(self):
            ...
```

### Arguments

See the API reference for [`@djc_test`](../../reference/testing_api.md#django_components.testing.djc_test) for more details.

### Setting Up Django

If you want to define a common Django settings that would be the baseline for all tests,
you can call [`django.setup()`](https://docs.djangoproject.com/en/5.2/ref/applications/#django.setup)
before the `@djc_test` decorator:

```python
import django
from django_components.testing import djc_test

django.setup(...)

@djc_test
def test_my_component():
    ...
```

!!! info

    If you omit [`django.setup()`](https://docs.djangoproject.com/en/5.2/ref/applications/#django.setup)
    in the example above, `@djc_test` will call it for you, so you don't need to do it manually.

## Example: Parametrizing Context Behavior

You can parametrize the [context behavior](../../reference/settings.md#django_components.app_settings.ComponentsSettings.context_behavior) using [`djc_test`](../../reference/testing_api.md#django_components.testing.djc_test):

```python
from django_components.testing import djc_test

@djc_test(
    # Settings applied to all cases
    components_settings={
        "app_dirs": ["custom_dir"],
    },
    # Parametrized settings
    parametrize=(
        ["components_settings"],
        [
            [{"context_behavior": "django"}],
            [{"context_behavior": "isolated"}],
        ],
        ["django", "isolated"],
    )
)
def test_context_behavior(components_settings):
    rendered = MyComponent.render()
    ...
```
