---
title: v0.110 🚨📢 (2024-11-25)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.110/
description: "⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See #791 and #789 and #818."
---

# v0.110 🚨📢 (2024-11-25)

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

### General

#### BREAKING CHANGES 🚨📢

- Installation changes:

    - If your components include JS or CSS, you now must use the middleware and add django-components' URLs to your `urlpatterns`
    (See "[Adding support for JS and CSS](https://github.com/django-components/django-components#adding-support-for-js-and-css)")

- Component typing signature changed from


    ```py
    Component[Args, Kwargs, Data, Slots]
    ```


    to


    ```py
    Component[Args, Kwargs, Slots, Data, JsData, CssData]
    ```


- If you rendered a component A with `Component.render()` and then inserted that into another component B, now you must pass `render_dependencies=False` to component A:


    ```py
    prerendered_a = CompA.render(
        args=[...],
        kwargs={...},
        render_dependencies=False,
    )

    html = CompB.render(
        kwargs={
            content=prerendered_a,
        },
    )
    ```


#### Feat

- Intellisense and mypy validation for settings:

  Instead of defining the `COMPONENTS` settings as a plain dict, you can use `ComponentsSettings`:


  ```py
  # settings.py
  from django_components import ComponentsSettings

  COMPONENTS = ComponentsSettings(
      autodiscover=True,
      ...
  )
  ```


- Use `get_component_dirs()` and `get_component_files()` to get the same list of dirs / files that would be imported by `autodiscover()`, but without actually
importing them.

#### Refactor

- For advanced use cases, use can omit the middleware and instead manage component JS and CSS dependencies yourself with `render_dependencies`

- The `ComponentRegistry` settings `RegistrySettings`
  were lowercased to align with the global settings:
  - `RegistrySettings.CONTEXT_BEHAVIOR` -> `RegistrySettings.context_behavior`
  - `RegistrySettings.TAG_FORMATTER` -> `RegistrySettings.tag_formatter`

  The old uppercase settings `CONTEXT_BEHAVIOR` and `TAG_FORMATTER` are deprecated and will be removed in v1.

- The setting `reload_on_template_change` was renamed to
  `reload_on_file_change`.
  And now it properly triggers server reload when any file in the component dirs change. The old name `reload_on_template_change`
  is deprecated and will be removed in v1.

- The setting `forbidden_static_files` was renamed to
  `static_files_forbidden`
  to align with `static_files_allowed`
  The old name `forbidden_static_files` is deprecated and will be removed in v1.

### Tags

#### BREAKING CHANGES 🚨📢

- `{% component_dependencies %}` tag was removed. Instead, use `{% component_js_dependencies %}` and `{% component_css_dependencies %}`

    - The combined tag was removed to encourage the best practice of putting JS scripts at the end of `<body>`, and CSS styles inside `<head>`.

        On the other hand, co-locating JS script and CSS styles can lead to
        a [flash of unstyled content](https://en.wikipedia.org/wiki/Flash_of_unstyled_content),
        as either JS scripts will block the rendering, or CSS will load too late.

- The undocumented keyword arg `preload` of `{% component_js_dependencies %}` and `{% component_css_dependencies %}` tags was removed.
  This will be replaced with HTML fragment support.

#### Fix

- Allow using forward slash (`/`) when defining custom TagFormatter,
  e.g. `{% MyComp %}..{% /MyComp %}`.

#### Refactor

- `{% component_dependencies %}` tags are now OPTIONAL - If your components use JS and CSS, but you don't use `{% component_dependencies %}` tags, the JS and CSS will now be, by default, inserted at the end of `<body>` and at the end of `<head>` respectively.

### Slots

#### Feat

- Fills can now be defined within loops (`{% for %}`) or other tags (like `{% with %}`),
  or even other templates using `{% include %}`.

  Following is now possible


  ```django
  {% component "table" %}
    {% for slot_name in slots %}
      {% fill name=slot_name %}
      {% endfill %}
    {% endfor %}
  {% endcomponent %}
  ```


- If you need to access the data or the default content of a default fill, you can
  set the `name` kwarg to `"default"`.

  Previously, a default fill would be defined simply by omitting the `{% fill %}` tags:


  ```django
  {% component "child" %}
    Hello world
  {% endcomponent %}
  ```


  But in that case you could not access the slot data or the default content, like it's possible
  for named fills:


  ```django
  {% component "child" %}
    {% fill name="header" data="data" %}
      Hello {{ data.user.name }}
    {% endfill %}
  {% endcomponent %}
  ```


  Now, you can specify default tag by using `name="default"`:


  ```django
  {% component "child" %}
    {% fill name="default" data="data" %}
      Hello {{ data.user.name }}
    {% endfill %}
  {% endcomponent %}
  ```


- When inside `get_context_data()` or other component methods, the default fill
  can now be accessed as `Component.input.slots["default"]`, e.g.:


  ```py
  class MyTable(Component):
      def get_context_data(self, *args, **kwargs):
          default_slot = self.input.slots["default"]
          ...
  ```


- You can now dynamically pass all slots to a child component. This is similar to
  [passing all slots in Vue](https://vue-land.github.io/faq/forwarding-slots#passing-all-slots):


  ```py
  class MyTable(Component):
      def get_context_data(self, *args, **kwargs):
          return {
              "slots": self.input.slots,
          }

      template: """
        <div>
          {% component "child" %}
            {% for slot_name in slots %}
              {% fill name=slot_name data="data" %}
                {% slot name=slot_name ...data / %}
              {% endfill %}
            {% endfor %}
          {% endcomponent %}
        </div>
      """
  ```


#### Fix

- Slots defined with `{% fill %}` tags are now properly accessible via `self.input.slots` in `get_context_data()`

- Do not raise error if multiple slots with same name are flagged as default

- Slots can now be defined within loops (`{% for %}`) or other tags (like `{% with %}`),
  or even other templates using `{% include %}`.

  Previously, following would cause the kwarg `name` to be an empty string:


  ```django
  {% for slot_name in slots %}
    {% slot name=slot_name %}
  {% endfor %}
  ```


#### Refactor

- When you define multiple slots with the same name inside a template,
  you now have to set the `default` and `required` flags individually.


  ```htmldjango
  <div class="calendar-component">
      <div class="header">
          {% slot "image" default required %}Image here{% endslot %}
      </div>
      <div class="body">
          {% slot "image" default required %}Image here{% endslot %}
      </div>
  </div>
  ```


  This means you can also have multiple slots with the same name but
  different conditions.

  E.g. in this example, we have a component that renders a user avatar
  - a small circular image with a profile picture of name initials.

  If the component is given `image_src` or `name_initials` variables,
  the `image` slot is optional. But if neither of those are provided,
  you MUST fill the `image` slot.


  ```htmldjango
  <div class="avatar">
      {% if image_src %}
          {% slot "image" default %}
              <img src="{{ image_src }}" />
          {% endslot %}
      {% elif name_initials %}
          {% slot "image" default required %}
              <div style="
                  border-radius: 25px;
                  width: 50px;
                  height: 50px;
                  background: blue;
              ">
                  {{ name_initials }}
              </div>
          {% endslot %}
      {% else %}
          {% slot "image" default required / %}
      {% endif %}
  </div>
  ```


- The slot fills that were passed to a component and which can be accessed as `Component.input.slots`
  can now be passed through the Django template, e.g. as inputs to other tags.

  Internally, django-components handles slot fills as functions.

  Previously, if you tried to pass a slot fill within a template, Django would try to call it as a function.

  Now, something like this is possible:


  ```py
  class MyTable(Component):
      def get_context_data(self, *args, **kwargs):
          return {
              "child_slot": self.input.slots["child_slot"],
          }

      template: """
        <div>
          {% component "child" content=child_slot / %}
        </div>
      """
  ```


  NOTE: Using `{% slot %}` and `{% fill %}` tags is still the preferred method, but the approach above
  may be necessary in some complex or edge cases.

- The `is_filled` variable (and the `{{ component_vars.is_filled }}` context variable) now returns
  `False` when you try to access a slot name which has not been defined:

  Before:


  ```django
  {{ component_vars.is_filled.header }} -> True
  {{ component_vars.is_filled.footer }} -> False
  {{ component_vars.is_filled.nonexist }} -> "" (empty string)
  ```


  After:

  ```django
  {{ component_vars.is_filled.header }} -> True
  {{ component_vars.is_filled.footer }} -> False
  {{ component_vars.is_filled.nonexist }} -> False
  ```


- Components no longer raise an error if there are extra slot fills

- Components will raise error when a slot is doubly-filled.

  E.g. if we have a component with a default slot:


  ```django
  {% slot name="content" default / %}
  ```


  Now there is two ways how we can target this slot: Either using `name="default"`
  or `name="content"`.

  In case you specify BOTH, the component will raise an error:


  ```django
  {% component "child" %}
    {% fill slot="default" %}
      Hello from default slot
    {% endfill %}
    {% fill slot="content" data="data" %}
      Hello from content slot
    {% endfill %}
  {% endcomponent %}
  ```
