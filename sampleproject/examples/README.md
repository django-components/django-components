# Examples

This Django app dynamically discovers and registers example components from the documentation (`docs/examples/`).

## How it works

1. **Discovery**: At startup, the app scans `docs/examples/*/` directories for:

   - `component.py` - Component definitions with inline templates
   - `page.py` - Page views for live demos

2. **Registration**: Found modules are imported as:

   - `examples.dynamic.<example_name>.component`
   - `examples.dynamic.<example_name>.page`

3. **Components**: Are automatically registered with django-components registry via `@register()` decorators

4. **URLs**: Page views are automatically registered as URL patterns at `examples/<example_name>`

## Structure

Each example in `docs/examples/` follows this structure:

```
docs/examples/form/
├── README.md           # Documentation
├── component.py        # Component with inline templates
├── page.py            # Page view for live demo
├── test.py            # Tests
└── images/            # Screenshots/assets
```

## Live examples

All examples are available as live demos:

- **Index page**: [http://localhost:8000/examples/](http://localhost:8000/examples/) - Lists all available examples
- **Individual examples**: `http://localhost:8000/examples/<example_name>`
  - [http://localhost:8000/examples/form_grid](http://localhost:8000/examples/form_grid)
  - [http://localhost:8000/examples/tabs](http://localhost:8000/examples/tabs)

## Adding new examples

1. Create a new directory in `docs/examples/<example_name>/`
2. Add `component.py`, `page.py`, and other files as seen above.
3. Start the server and open `http://localhost:8000/examples/<example_name>` to see the example.
