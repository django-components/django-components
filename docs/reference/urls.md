<!-- Autogenerated by reference.py -->

# URLs

Below are all the URL patterns that will be added by adding `django_components.urls`.

See [Installation](../overview/installation.md#adding-support-for-js-and-css)
on how to add these URLs to your Django project.

Django components already prefixes all URLs with `components/`. So when you are
adding the URLs to `urlpatterns`, you can use an empty string as the first argument:

```python
from django.urls import include, path

urlpatterns = [
    ...
    path("", include("django_components.urls")),
]
```

## List of URLs


- `components/cache/<str:comp_cls_id>.<str:input_hash>.<str:script_type>`

- `components/cache/<str:comp_cls_id>.<str:script_type>`
