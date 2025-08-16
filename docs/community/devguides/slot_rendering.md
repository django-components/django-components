This doc serves as a primer on how component slots and fills are resolved.

## Flow

1. Imagine you have a template. Some kind of text, maybe HTML:
   ```django
   | ------
   | ---------
   | ----
   | -------
   ```

2. The template may contain some vars, tags, etc
   ```django
   | -- {{ my_var }} --
   | ---------
   | ----
   | -------
   ```

3. The template also contains some slots, etc
   ```django
   | -- {{ my_var }} --
   | ---------
   | -- {% slot "myslot" %} ---
   | -- {% endslot %} ---
   | ----
   | -- {% slot "myslot2" %} ---
   | -- {% endslot %} ---
   | -------
   ```

4. Slots may be nested
   ```django
   | -- {{ my_var }} --
   | -- ABC
   | -- {% slot "myslot" %} ---
   | ----- DEF {{ my_var }}
   | ----- {% slot "myslot_inner" %}
   | -------- GHI {{ my_var }}
   | ----- {% endslot %}
   | -- {% endslot %} ---
   | ----
   | -- {% slot "myslot2" %} ---
   | ---- JKL {{ my_var }}
   | -- {% endslot %} ---
   | -------
   ```

5. Some slots may be inside fills for other components
   ```django
   | -- {{ my_var }} --
   | -- ABC
   | -- {% slot "myslot" %}---
   | ----- DEF {{ my_var }}
   | ----- {% slot "myslot_inner" %}
   | -------- GHI {{ my_var }}
   | ----- {% endslot %}
   | -- {% endslot %} ---
   | ------
   | -- {% component "mycomp" %} ---
   | ---- {% slot "myslot" %} ---
   | ------- JKL {{ my_var }}
   | ------- {% slot "myslot_inner" %}
   | ---------- MNO {{ my_var }}
   | ------- {% endslot %}
   | ---- {% endslot %} ---
   | -- {% endcomponent %} ---
   | ----
   | -- {% slot "myslot2" %} ---
   | ---- PQR {{ my_var }}
   | -- {% endslot %} ---
   | -------
   ```

6. The names of the slots and fills may be defined using variables
   ```django
   | -- {% slot slot_name %} ---
   | ---- STU {{ my_var }}
   | -- {% endslot %} ---
   | -------
   ```

7. The slot and fill names may be defined using for loops or other variables defined within the template (e.g. `{% with %}` tag or `{% ... as var %}` syntax)
   ```django
   | -- {% for slot_name in slots %} ---
   | ---- {% slot slot_name %} ---
   | ------ STU {{ slot_name }}
   | ---- {% endslot %} ---
   | -- {% endfor %} ---
   | -------
   ```

8. Variables for names and for loops allow us implement "passthrough slots" - that is, taking all slots that our component received, and passing them to a child component, dynamically.
   ```django
   | -- {% component "mycomp" %} ---
   | ---- {% for slot_name in slots %} ---
   | ------ {% fill slot_name %} ---
   | -------- {% slot slot_name %} ---
   | ---------- XYZ {{ slot_name }}
   | --------- {% endslot %}
   | ------- {% endfill %}
   | ---- {% endfor %} ---
   | -- {% endcomponent %} ---
   | ----
   ```

9. Putting that all together, a document may look like this:
   ```django
   | -- {{ my_var }} --
   | -- ABC
   | -- {% slot "myslot" %}---
   | ----- DEF {{ my_var }}
   | ----- {% slot "myslot_inner" %}
   | -------- GHI {{ my_var }}
   | ----- {% endslot %}
   | -- {% endslot %} ---
   | ------
   | -- {% component "mycomp" %} ---
   | ---- {% slot "myslot" %} ---
   | ------- JKL {{ my_var }}
   | ------- {% slot "myslot_inner" %}
   | ---------- MNO {{ my_var }}
   | ------- {% endslot %}
   | ---- {% endslot %} ---
   | -- {% endcomponent %} ---
   | ----
   | -- {% slot "myslot2" %} ---
   | ---- PQR {{ my_var }}
   | -- {% endslot %} ---
   | -------
   | -- {% for slot_name in slots %} ---
   | ---- {% component "mycomp" %} ---
   | ------- {% slot slot_name %}
   | ---------- STU {{ slot_name }}
   | ------- {% endslot %}
   | ---- {% endcomponent %} ---
   | -- {% endfor %} ---
   | ----
   | -- {% component "mycomp" %} ---
   | ---- {% for slot_name in slots %} ---
   | ------ {% fill slot_name %} ---
   | -------- {% slot slot_name %} ---
   | ---------- XYZ {{ slot_name }}
   | --------- {% endslot %}
   | ------- {% endfill %}
   | ---- {% endfor %} ---
   | -- {% endcomponent %} ---
   | -------
   ```

10. Given the above, we want to render the slots with `{% fill %}` tag that were defined OUTSIDE of this template. How do I do that?

    > _NOTE: Before v0.110, slots were resolved statically, by walking down the Django Template and Nodes. However, this did not allow for using for loops or other variables defined in the template._

    Currently, this consists of 2 steps:

    1. If a component is rendered within a template using `{% component %}` tag, determine the given `{% fill %}` tags in the component's body (the content in between `{% component %}` and `{% endcomponent %}`).
    
        After this step, we know about all the fills that were passed to the component.

    2. Then we simply render the template as usual. And then we reach the `{% slot %}` tag, we search the context for the available fills.
    
        - If there IS a fill with the same name as the slot, we render the fill.
        - If the slot is marked `default`, and there is a fill named `default`, then we render that.
        - Otherwise, we render the slot's default content.

11. Obtaining the fills from `{% fill %}`.

    When a component is rendered with `{% component %}` tag, and it has some content in between `{% component %}` and `{% endcomponent %}`, we want to figure out if that content is a default slot (no `{% fill %}` used), or if there is a collection of named `{% fill %}` tags:

    Default slot:

    ```django
    | -- {% component "mycomp" %} ---
    | ---- STU {{ slot_name }}
    | -- {% endcomponent %} ---
    ```

    Named slots:

    ```django
    | -- {% component "mycomp" %} ---
    | ---- {% fill "slot_a" %}
    | ------ STU
    | ---- {% endslot %}
    | ---- {% fill "slot_b" %}
    | ------ XYZ
    | ---- {% endslot %}
    | -- {% endcomponent %} ---
    ```

    To respect any forloops or other variables defined within the template to which the fills may have access,
    we:

    1. Render the content between `{% component %}` and `{% endcomponent %}` using the context
       outside of the component.
    2. When we reach a `{% fill %}` tag, we capture any variables that were created between
       the `{% component %}` and `{% fill %}` tags.
    3. When we reach `{% fill %}` tag, we do not continue rendering deeper. Instead we
       make a record that we found the fill tag with given name, kwargs, etc.
    4. After the rendering is done, we check if we've encountered any fills.
       If yes, we expect only named fills. If no, we assume that the the component's body
       is a default slot.
    5. Lastly we process the found fills, and make them available to the context, so any
       slots inside the component may access these fills.

12. Rendering slots

    Slot rendering works similarly to collecting fills, in a sense that we do not search
    for the slots ahead of the time, but instead let Django handle the rendering of the template,
    and we step in only when Django come across as `{% slot %}` tag.

    When we reach a slot tag, we search the context for the available fills.
  
      - If there IS a fill with the same name as the slot, we render the fill.
      - If the slot is marked `default`, and there is a fill named `default`, then we render that.
      - Otherwise, we render the slot's default content.

## Using the correct context in {% slot/fill %} tags

In previous section, we said that the `{% fill %}` tags should be already rendered by the time they are inserted into the `{% slot %}` tags.

This is not quite true. To help you understand, consider this complex case:

```django
| -- {% for var in [1, 2, 3] %} ---
| ---- {% component "mycomp2" %} ---
| ------ {% fill "first" %}
| ------- STU {{ my_var }}
| -------     {{ var }}
| ------ {% endfill %}
| ------ {% fill "second" %}
| -------- {% component var=var my_var=my_var %}
| ---------- VWX {{ my_var }}
| -------- {% endcomponent %}
| ------ {% endfill %}
| ---- {% endcomponent %} ---
| -- {% endfor %} ---
| -------
```

We want the forloop variables to be available inside the `{% fill %}` tags. Because of that, however, we CANNOT render the fills/slots in advance.

Instead, our solution is closer to [how Vue handles slots](https://vuejs.org/guide/components/slots.html#scoped-slots). In Vue, slots are effectively functions that accept a context variables and render some content.

While we do not wrap the logic in a function, we do PREPARE IN ADVANCE:
1. The content that should be rendered for each slot
2. The context variables from `get_template_data()`

Thus, once we reach the `{% slot %}` node, in it's `render()` method, we access the data above, and, depending on the `context_behavior` setting, include the current context or not. For more info, see `SlotNode.render()`.
