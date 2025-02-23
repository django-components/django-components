_New in version 0.96_

Component hooks are functions that allow you to intercept the rendering process at specific positions.

## Available hooks

- `on_render_before`

  ```py
  def on_render_before(
      self: Component,
      context: Context,
      template: Template
  ) -> None:
  ```

  Hook that runs just before the component's template is rendered.

  You can use this hook to access or modify the context or the template:

  ```py
  def on_render_before(self, context, template) -> None:
      # Insert value into the Context
      context["from_on_before"] = ":)"

      # Append text into the Template
      template.nodelist.append(TextNode("FROM_ON_BEFORE"))
  ```

- `on_render_after`

  ```py
  def on_render_after(
      self: Component,
      context: Context,
      template: Template,
      content: str
  ) -> None | str | SafeString:
  ```

  Hook that runs just after the component's template was rendered.
  It receives the rendered output as the last argument.

  You can use this hook to access the context or the template, but modifying
  them won't have any effect.

  To override the content that gets rendered, you can return a string or SafeString from this hook:

  ```py
  def on_render_after(self, context, template, content):
      # Prepend text to the rendered content
      return "Chocolate cookie recipe: " + content
  ```

## Component hooks example

You can use hooks together with [provide / inject](#how-to-use-provide--inject) to create components
that accept a list of items via a slot.

In the example below, each `tab_item` component will be rendered on a separate tab page, but they are all defined in the default slot of the `tabs` component.

[See here for how it was done](https://github.com/django-components/django-components/discussions/540)

```django
{% component "tabs" %}
  {% component "tab_item" header="Tab 1" %}
    <p>
      hello from tab 1
    </p>
    {% component "button" %}
      Click me!
    {% endcomponent %}
  {% endcomponent %}

  {% component "tab_item" header="Tab 2" %}
    Hello this is tab 2
  {% endcomponent %}
{% endcomponent %}
```
