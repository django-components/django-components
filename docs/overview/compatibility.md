Django-components supports all supported combinations versions of [Django](https://docs.djangoproject.com/en/dev/faq/install/#what-python-version-can-i-use-with-django) and [Python](https://devguide.python.org/versions/#versions).

| Python version | Django version |
| -------------- | -------------- |
| 3.8            | 4.2            |
| 3.9            | 4.2            |
| 3.10           | 4.2, 5.0, 5.1  |
| 3.11           | 4.2, 5.0, 5.1  |
| 3.12           | 4.2, 5.0, 5.1  |
| 3.13           | 5.1            |

### Operating systems

django-components is tested against Ubuntu and Windows, and should work on any operating system that supports Python.

!!! note

    django-components uses Rust-based parsers for better performance.

    These sub-packages are built with [maturin](https://github.com/PyO3/maturin)
    which supports a wide range of operating systems, architectures, and Python versions ([see the full list](https://pypi.org/project/djc-core-html-parser/#files)).
    
    This should cover most of the cases.

    However, if your environment is not supported, you will need to install Rust and Cargo to build the sub-packages from source.
