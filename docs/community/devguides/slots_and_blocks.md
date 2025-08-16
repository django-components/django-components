1.  First let's clarify how `include` and `extends` tags work inside components.

    When component template includes `include` or `extends` tags, it's as if the "included"
    template was inlined. So if the "included" template contains `slot` tags, then the component
    uses those slots.

    If you have a template `abc.html`:
    ```django
    <div>
      hello
      {% slot "body" %}{% endslot %}
    </div>
    ```

    And components that make use of `abc.html` via `include` or `extends`:
    ```djc_py
    from django_components import Component, register

    @register("my_comp_extends")
    class MyCompWithExtends(Component):
        template = """{% extends "abc.html" %}"""

    @register("my_comp_include")
    class MyCompWithInclude(Component):
        template = """{% include "abc.html" %}"""
    ```

    Then you can set slot fill for the slot imported via `include/extends`:

    ```django
    {% component "my_comp_extends" %}
        {% fill "body" %}
            123
        {% endfill %}
    {% endcomponent %}
    ```

    And it will render:
    ```html
    <div>
      hello
      123
    </div>
    ```

2.  Slot and block

    If you have a template `abc.html` like so:

    ```django
    <div>
      hello
      {% block inner %}
        1
        {% slot "body" %}
          2
        {% endslot %}
      {% endblock %}
    </div>
    ```

    and component `my_comp`:

    ```py
    @register("my_comp")
    class MyComp(Component):
        template_file = "abc.html"
    ```

    Then:

    1.  Since the `block` wasn't overriden, you can use the `body` slot:

        ```django
        {% component "my_comp" %}
        	{% fill "body" %}
        		XYZ
        	{% endfill %}
        {% endcomponent %}
        ```

        And we get:

        ```html
        <div>hello 1 XYZ</div>
        ```

    2.  `blocks` CANNOT be overriden through the `component` tag, so something like this:

        ```django
        {% component "my_comp" %}
        	{% fill "body" %}
        		XYZ
        	{% endfill %}
        {% endcomponent %}
        {% block "inner" %}
        	456
        {% endblock %}
        ```

        Will still render the component content just the same:

        ```html
        <div>hello 1 XYZ</div>
        ```

    3.  You CAN override the `block` tags of `abc.html` if the component template
        uses `extends`. In that case, just as you would expect, the `block inner` inside
        `abc.html` will render `OVERRIDEN`:

        ```djc_py
        @register("my_comp")
        class MyComp(Component):
            template = """
                {% extends "abc.html" %}
                {% block inner %}
                  OVERRIDEN
                {% endblock %}
            """
        ```

    4.  This is where it gets interesting (but still intuitive). You can insert even
        new `slots` inside these "overriding" blocks:

        ```djc_py
        @register("my_comp")
        class MyComp(Component):
            template = """
              {% extends "abc.html" %}

              {% load component_tags %}
              {% block "inner" %}
                OVERRIDEN
                {% slot "new_slot" %}
                  hello
                {% endslot %}
              {% endblock %}
            """
        ```

        And you can then pass fill for this `new_slot` when rendering the component:

        ```django
        {% component "my_comp" %}
        	{% fill "new_slot" %}
        		XYZ
        	{% endfill %}
        {% endcomponent %}
        ```

        NOTE: Currently you can supply fills for both `new_slot` and `body` slots, and you will
        not get an error for an invalid/unknown slot name. But since `body` slot is not rendered,
        it just won't do anything. So this renders the same as above:

        ```django
        {% component "my_comp" %}
        	{% fill "new_slot" %}
        		XYZ
        	{% endfill %}
        	{% fill "body" %}
        		www
        	{% endfill %}
        {% endcomponent %}
        ```
