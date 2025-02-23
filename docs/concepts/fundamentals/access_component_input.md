When you call `Component.render` or `Component.render_to_response`, the inputs to these methods can be accessed from within the instance under `self.input`.

This means that you can use `self.input` inside:

- `get_context_data`
- `get_template_name`
- `get_template`
- `on_render_before`
- `on_render_after`

`self.input` is only defined during the execution of `Component.render`, and raises a `RuntimeError` when called outside of this context.

`self.input` has the same fields as the input to `Component.render`:

```python
class TestComponent(Component):
    def get_context_data(self, var1, var2, variable, another, **attrs):
        assert self.input.args == (123, "str")
        assert self.input.kwargs == {"variable": "test", "another": 1}
        assert self.input.slots == {"my_slot": "MY_SLOT"}
        assert isinstance(self.input.context, Context)

        return {
            "variable": variable,
        }

rendered = TestComponent.render(
    kwargs={"variable": "test", "another": 1},
    args=(123, "str"),
    slots={"my_slot": "MY_SLOT"},
)
```

NOTE: The slots in `self.input.slots` are normalized to slot functions.
