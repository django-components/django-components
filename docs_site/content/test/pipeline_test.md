# Pipeline Test Page

This page exercises every feature of the docs build pipeline. It exists so
pipeline changes can be validated without depending on real docs content that
may move or be renamed.

## Code fences with syntax highlighting

Python:

```python
from django_components import Component

class MyComponent(Component):
    template = "<div>{{ message }}</div>"
```

Django template (with template tags inside the fence that must NOT be executed):

```django
{% load component_tags %}
{% component "my_component" message="hello" %}
{% endcomponent %}
```

`djc_py` (our custom Pygments lexer):

```djc_py
class Calendar(Component):
    template: types.django_html = """
        <div class="calendar">
            {% slot "header" %}Default header{% endslot %}
        </div>
    """
```

## Fenced code with title

```python title="components/calendar.py"
class Calendar(Component):
    pass
```

## Inline code with template syntax

Use `{% component "name" %}` to render a component inline. The context
variable `{{ request.user }}` is also available.

## Admonitions

!!! note
    This is a note admonition. It should render with a blue left border.

!!! warning "Watch out"
    This is a warning with a custom title.

!!! info
    Admonitions can contain `inline code` and **bold text**.

## Tabbed content

=== "uv"

    LOL

    ```bash
    uv pip install django-components
    ```

    KEK

=== "pip"

    ```bash
    pip install django-components
    ```

=== "third"

    LOL

    ```bash
    uv pip install django-components
    ```

## Collapsible details

??? note "Click to expand"
    This content is hidden by default.

???+ info "Open by default"
    This content is visible by default.

## Task list

- [x] Fence protection pre-pass
- [x] Django template rendering (Pass 1)
- [x] python-markdown conversion (Pass 2)
- [ ] DocPage layout wrap (Pass 3)
- [ ] Full build command

## Tables

| Feature | Status | Phase |
|---|---|---|
| Fence scanner | Done | 1 |
| Django pass | Done | 1 |
| Markdown pass | Done | 1 |
| DocPage layout | Stub | 1 |

## Django template tag (Pass 1 expansion)

Current version: {% version %}

## Cross-page link styles

Same-page anchor: [see tables above](#tables)

Markdown link (gets rewritten to a clean URL): [another page](./other.md)

Clean-URL link (left as-is): [another page](../other/)

## Heading hierarchy for TOC testing

### Sub-section A

Content under A.

### Sub-section B

Content under B.

#### Nested under B

Deeply nested content.

## Edge cases

Empty code fence:

```
```

Fence with no language:

```
plain text content
```

Backtick-heavy inline: use `` `backticks` `` inside prose.
