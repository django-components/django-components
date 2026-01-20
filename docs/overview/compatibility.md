Django-components supports all supported combinations versions of [Django](https://docs.djangoproject.com/en/5.2/faq/install/#what-python-version-can-i-use-with-django) and [Python](https://devguide.python.org/versions/#versions).

| Python version | Django version |
| -------------- | -------------- |
| 3.8            | 4.2            |
| 3.9            | 4.2            |
| 3.10           | 4.2, 5.1, 5.2  |
| 3.11           | 4.2, 5.1, 5.2  |
| 3.12           | 4.2, 5.1, 5.2  |
| 3.13           | 5.1, 5.2       |
| 3.14           | 5.2            |

### Operating systems

django-components is tested against Ubuntu and Windows, and should work on any operating system that supports Python.

!!! note

    django-components uses Rust-based parsers for better performance.

    These sub-packages are built with [maturin](https://github.com/PyO3/maturin)
    which supports a wide range of operating systems, architectures, and Python versions ([see the full list](https://pypi.org/project/djc-core/#files)).
    
    This should cover most of the cases.

    However, if your environment is not supported, you will need to install Rust and Cargo to build the sub-packages from source.

### Other packages

Here we track which other packages from the Django ecosystem we try to be compatible with.

How to read this table - E.g. in case of `django-template-partials`, you should use at least version `0.142.3` of `django-components` and at least version `23.3` of django-template-partials.

| Package | django-components version | Package version |
| -------------- | -------------- | --- |
[`django-template-partials`](https://github.com/carltongibson/django-template-partials) | >=0.142.3            | >=23.3            |
