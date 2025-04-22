## Customizing component tags with TagFormatter

_New in version 0.89_

By default, components are rendered using the pair of `{% component %}` / `{% endcomponent %}` template tags:

```django
{% component "button" href="..." disabled %}
Click me!
{% endcomponent %}

{# or #}

{% component "button" href="..." disabled / %}
```

You can change this behaviour in the settings under the [`COMPONENTS.tag_formatter`](#tag-formatter-setting).

For example, if you set the tag formatter to

`django_components.component_shorthand_formatter`

then the components' names will be used as the template tags:

```django
{% button href="..." disabled %}
  Click me!
{% endbutton %}

{# or #}

{% button href="..." disabled / %}
```

## Available TagFormatters

django_components provides following predefined TagFormatters:

- **`ComponentFormatter` (`django_components.component_formatter`)**

  Default

  Uses the `component` and `endcomponent` tags, and the component name is gives as the first positional argument.

  Example as block:

  ```django
  {% component "button" href="..." %}
      {% fill "content" %}
          ...
      {% endfill %}
  {% endcomponent %}
  ```

  Example as inlined tag:

  ```django
  {% component "button" href="..." / %}
  ```

- **`ShorthandComponentFormatter` (`django_components.component_shorthand_formatter`)**

  Uses the component name as start tag, and `end<component_name>`
  as an end tag.

  Example as block:

  ```django
  {% button href="..." %}
      Click me!
  {% endbutton %}
  ```

  Example as inlined tag:

  ```django
  {% button href="..." / %}
  ```

## Writing your own TagFormatter

### Background

First, let's discuss how TagFormatters work, and how components are rendered in django_components.

When you render a component with `{% component %}` (or your own tag), the following happens:

1. `component` must be registered as a Django's template tag
2. Django triggers django_components's tag handler for tag `component`.
3. The tag handler passes the tag contents for pre-processing to `TagFormatter.parse()`.

   So if you render this:

   ```django
   {% component "button" href="..." disabled %}
   {% endcomponent %}
   ```

   Then `TagFormatter.parse()` will receive a following input:

   ```py
   ["component", '"button"', 'href="..."', 'disabled']
   ```

4. `TagFormatter` extracts the component name and the remaining input.

   So, given the above, `TagFormatter.parse()` returns the following:

   ```py
   TagResult(
       component_name="button",
       tokens=['href="..."', 'disabled']
   )
   ```

5. The tag handler resumes, using the tokens returned from `TagFormatter`.

   So, continuing the example, at this point the tag handler practically behaves as if you rendered:

   ```django
   {% component href="..." disabled %}
   ```

6. Tag handler looks up the component `button`, and passes the args, kwargs, and slots to it.

### TagFormatter

`TagFormatter` handles following parts of the process above:

- Generates start/end tags, given a component. This is what you then call from within your template as `{% component %}`.

- When you `{% component %}`, tag formatter pre-processes the tag contents, so it can link back the custom template tag to the right component.

To do so, subclass from `TagFormatterABC` and implement following method:

- `start_tag`
- `end_tag`
- `parse`

For example, this is the implementation of [`ShorthandComponentFormatter`](#available-tagformatters)

```py
class ShorthandComponentFormatter(TagFormatterABC):
    # Given a component name, generate the start template tag
    def start_tag(self, name: str) -> str:
        return name  # e.g. 'button'

    # Given a component name, generate the start template tag
    def end_tag(self, name: str) -> str:
        return f"end{name}"  # e.g. 'endbutton'

    # Given a tag, e.g.
    # `{% button href="..." disabled %}`
    #
    # The parser receives:
    # `['button', 'href="..."', 'disabled']`
    def parse(self, tokens: List[str]) -> TagResult:
        tokens = [*tokens]
        name = tokens.pop(0)
        return TagResult(
            name,  # e.g. 'button'
            tokens  # e.g. ['href="..."', 'disabled']
        )
```

That's it! And once your `TagFormatter` is ready, don't forget to update the settings!
