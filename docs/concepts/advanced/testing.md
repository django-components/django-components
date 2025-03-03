_New in version 0.131_

The [`@djc_test`](../../../reference/testing_api#djc_test) decorator is a powerful tool for testing components created with `django-components`. It ensures that each test is properly isolated, preventing components registered in one test from affecting others.

## Usage

The [`@djc_test`](../../../reference/testing_api#djc_test) decorator can be applied to functions, methods, or classes. When applied to a class, it recursively decorates all methods starting with `test_`, including those in nested classes. This allows for comprehensive testing of component behavior.

### Applying to a Function

To apply [`djc_test`](../../../reference/testing_api#djc_test) to a function,
simply decorate the function as shown below:

```python
import django
from django_components.testing import djc_test

django.setup()

@djc_test
def test_my_component():
    @register("my_component")
    class MyComponent(Component):
        template = "..."
    ...
```

### Applying to a Class

When applied to a class, `djc_test` decorates each `test_` method individually:

```python
import django
from django_components.testing import djc_test

django.setup()

@djc_test
class TestMyComponent:
    def test_something(self):
        ...

    class Nested:
        def test_something_else(self):
            ...
```

This is equivalent to applying the decorator to each method individually:

```python
import django
from django_components.testing import djc_test

django.setup()

class TestMyComponent:
    @djc_test
    def test_something(self):
        ...

    class Nested:
        @djc_test
        def test_something_else(self):
            ...
```

### Arguments

See the API reference for [`@djc_test`](../../../reference/testing_api#djc_test) for more details.

### Setting Up Django

Before using [`djc_test`](../../../reference/testing_api#djc_test), ensure Django is set up:

```python
import django
from django_components.testing import djc_test

django.setup()

@djc_test
def test_my_component():
    ...
```

## Example: Parametrizing Context Behavior

You can parametrize the [context behavior](../../../reference/settings#django_components.app_settings.ComponentsSettings.context_behavior) using [`djc_test`](../../../reference/testing_api#djc_test):

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
    rendered = MyComponent().render()
    ...
```
