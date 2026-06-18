"""
Per-page discovery generators.

Each module here exposes ``discover() -> ReferencePage`` for one page of the API
reference (``exceptions``, ``api``, ``commands``, ...). They find *what* to
document (the public symbols) using runtime introspection of
``django_components``; Layer 2 then uses griffe to get the structured *facts*
about each symbol. One module per reference page, matching the old
``gen_reference_*`` functions in ``the old mkdocs scripts/reference.py``.
"""
