---
title: v0.140.0 🚨📢 (2025-06-05)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.140.0/
description: "⚠️ Major release ⚠️ - Please test thoroughly before / after upgrading."
---

# v0.140.0 🚨📢 (2025-06-05)

⚠️ Major release ⚠️ - Please test thoroughly before / after upgrading.

This is the biggest step towards v1. While this version introduces
many small API changes, we don't expect to make further changes to
the affected parts before v1.

For more details see [#433](https://github.com/django-components/django-components/issues/433).

Summary:

- Overhauled typing system
- Middleware removed, no longer needed
- `get_template_data()` is the new canonical way to define template data.
  `get_context_data()` is now deprecated but will remain until v2.
- Slots API polished and prepared for v1.
- Merged `Component.Url` with `Component.View`
- Added `Component.args`, `Component.kwargs`, `Component.slots`, `Component.context`
- Added `{{ component_vars.args }}`, `{{ component_vars.kwargs }}`, `{{ component_vars.slots }}`
- You should no longer instantiate `Component` instances. Instead, call `Component.render()` or `Component.render_to_response()` directly.
- Component caching can now consider slots (opt-in)
- And lot more...

#### BREAKING CHANGES 🚨📢

**Middleware**

- The middleware `ComponentDependencyMiddleware` was removed as it is no longer needed.

    The middleware served one purpose - to render the JS and CSS dependencies of components
    when you rendered templates with `Template.render()` or `django.shortcuts.render()` and those templates contained `{% component %}` tags.

    - NOTE: If you rendered HTML with `Component.render()` or `Component.render_to_response()`, the JS and CSS were already rendered.

    Now, the JS and CSS dependencies of components are automatically rendered,
    even when you render Templates with `Template.render()` or `django.shortcuts.render()`.

    To disable this behavior, set the `DJC_DEPS_STRATEGY` context key to `"ignore"`
    when rendering the template:


    ```py
    # With `Template.render()`:
    template = Template(template_str)
    rendered = template.render(Context({"DJC_DEPS_STRATEGY": "ignore"}))

    # Or with django.shortcuts.render():
    from django.shortcuts import render
    rendered = render(
        request,
        "my_template.html",
        context={"DJC_DEPS_STRATEGY": "ignore"},
    )
    ```


    In fact, you can set the `DJC_DEPS_STRATEGY` context key to any of the strategies:

    - `"document"`
    - `"fragment"`
    - `"simple"`
    - `"prepend"`
    - `"append"`
    - `"ignore"`

    See [Dependencies rendering](https://django-components.github.io/django-components/0.140.1/concepts/advanced/rendering_js_css/) for more info.

**Typing**

- Component typing no longer uses generics. Instead, the types are now defined as class attributes of the component class.

    Before:


    ```py
    Args = Tuple[float, str]

    class Button(Component[Args]):
        pass
    ```


    After:


    ```py
    class Button(Component):
        class Args(NamedTuple):
            size: float
            text: str
    ```



    See [Migrating from generics to class attributes](https://django-components.github.io/django-components/0.140.1/concepts/fundamentals/typing_and_validation/#migrating-from-generics-to-class-attributes) for more info.
- Removed `EmptyTuple` and `EmptyDict` types. Instead, there is now a single `Empty` type.


    ```py
    from django_components import Component, Empty

    class Button(Component):
        template = "Hello"

        Args = Empty
        Kwargs = Empty
    ```


**Component API**

- The interface of the not-yet-released `get_js_data()` and `get_css_data()` methods has changed to
  match `get_template_data()`.

    Before:


    ```py
    def get_js_data(self, *args, **kwargs):
    def get_css_data(self, *args, **kwargs):
    ```


    After:


    ```py
    def get_js_data(self, args, kwargs, slots, context):
    def get_css_data(self, args, kwargs, slots, context):
    ```


- Arguments in `Component.render_to_response()` have changed
  to match that of `Component.render()`.

    Please ensure that you pass the parameters as kwargs, not as positional arguments,
    to avoid breaking changes.

    The signature changed, moving the `args` and `kwargs` parameters to 2nd and 3rd position.

    Next, the `render_dependencies` parameter was added to match `Component.render()`.

    Lastly:

    - Previously, any extra ARGS and KWARGS were passed to the `response_class`.
    - Now, only extra KWARGS will be passed to the `response_class`.

    Before:


    ```py
      def render_to_response(
          cls,
          context: Optional[Union[Dict[str, Any], Context]] = None,
          slots: Optional[SlotsType] = None,
          escape_slots_content: bool = True,
          args: Optional[ArgsType] = None,
          kwargs: Optional[KwargsType] = None,
          deps_strategy: DependenciesStrategy = "document",
          request: Optional[HttpRequest] = None,
          *response_args: Any,
          **response_kwargs: Any,
      ) -> HttpResponse:
    ```


    After:


    ```py
    def render_to_response(
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        slots: Optional[Any] = None,
        deps_strategy: DependenciesStrategy = "document",
        type: Optional[DependenciesStrategy] = None,  # Deprecated, use `deps_strategy`
        render_dependencies: bool = True,  # Deprecated, use `deps_strategy="ignore"`
        outer_context: Optional[Context] = None,
        request: Optional[HttpRequest] = None,
        registry: Optional[ComponentRegistry] = None,
        registered_name: Optional[str] = None,
        node: Optional[ComponentNode] = None,
        **response_kwargs: Any,
    ) -> HttpResponse:
    ```


- `Component.render()` and `Component.render_to_response()` NO LONGER accept `escape_slots_content` kwarg.

    Instead, slots are now always escaped.

    To disable escaping, wrap the result of `slots` in
    [`mark_safe()`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.mark_safe).

    Before:


    ```py
    html = component.render(
        slots={"my_slot": "CONTENT"},
        escape_slots_content=False,
    )
    ```


    After:


    ```py
    html = component.render(
        slots={"my_slot": mark_safe("CONTENT")}
    )
    ```


- `Component.template` no longer accepts a Template instance, only plain string.

    Before:


    ```py
    class MyComponent(Component):
        template = Template("{{ my_var }}")
    ```


    Instead, either:

    1. Set `Component.template` to a plain string.


        ```py
        class MyComponent(Component):
            template = "{{ my_var }}"
        ```


    2. Move the template to it's own HTML file and set `Component.template_file`.


        ```py
        class MyComponent(Component):
            template_file = "my_template.html"
        ```


    3. Or, if you dynamically created the template, render the template inside `Component.on_render()`.


        ```py
        class MyComponent(Component):
            def on_render(self, context, template):
                dynamic_template = do_something_dynamic()
                return dynamic_template.render(context)
        ```


- Subclassing of components with `None` values has changed:

    Previously, when a child component's template / JS / CSS attributes were set to `None`, the child component still inherited the parent's template / JS / CSS.

    Now, the child component will not inherit the parent's template / JS / CSS if it sets the attribute to `None`.

    Before:


    ```py
    class Parent(Component):
        template = "parent.html"

    class Child(Parent):
        template = None

    # Child still inherited parent's template
    assert Child.template == Parent.template
    ```


    After:


    ```py
    class Parent(Component):
        template = "parent.html"

    class Child(Parent):
        template = None

    # Child does not inherit parent's template
    assert Child.template is None
    ```


- The `Component.Url` class was merged with `Component.View`.

    Instead of `Component.Url.public`, use `Component.View.public`.

    If you imported `ComponentUrl` from `django_components`, you need to update your import to `ComponentView`.

    Before:


    ```py
    class MyComponent(Component):
        class Url:
            public = True

        class View:
            def get(self, request):
                return self.render_to_response()
    ```


    After:


    ```py
    class MyComponent(Component):
        class View:
            public = True

            def get(self, request):
                return self.render_to_response()
    ```


- Caching - The function signatures of `Component.Cache.get_cache_key()` and `Component.Cache.hash()` have changed to enable passing slots.

    Args and kwargs are no longer spread, but passed as a list and a dict, respectively.

    Before:


    ```py
    def get_cache_key(self, *args: Any, **kwargs: Any) -> str:

    def hash(self, *args: Any, **kwargs: Any) -> str:
    ```


    After:


    ```py
    def get_cache_key(self, args: Any, kwargs: Any, slots: Any) -> str:

    def hash(self, args: Any, kwargs: Any) -> str:
    ```


**Template tags**

- Component name in the `{% component %}` tag can no longer be set as a kwarg.

    Instead, the component name MUST be the first POSITIONAL argument only.

    Before, it was possible to set the component name as a kwarg
    and put it anywhere in the `{% component %}` tag:


    ```django
    {% component rows=rows headers=headers name="my_table" ... / %}
    ```


    Now, the component name MUST be the first POSITIONAL argument:


    ```django
    {% component "my_table" rows=rows headers=headers ... / %}
    ```


    Thus, the `name` kwarg can now be used as a regular input.


    ```django
    {% component "profile" name="John" job="Developer" / %}
    ```


**Slots**

- If you instantiated `Slot` class with kwargs, you should now use `contents` instead of `content_func`.

    Before:


    ```py
    slot = Slot(content_func=lambda *a, **kw: "CONTENT")
    ```


    After:


    ```py
    slot = Slot(contents=lambda ctx: "CONTENT")
    ```


    Alternatively, pass the function / content as first positional argument:


    ```py
    slot = Slot(lambda ctx: "CONTENT")
    ```


- The undocumented `Slot.escaped` attribute was removed.

    Instead, slots are now always escaped.

    To disable escaping, wrap the result of `slots` in
    [`mark_safe()`](https://docs.djangoproject.com/en/5.2/ref/utils/#django.utils.safestring.mark_safe).

- Slot functions behavior has changed. See the new [Slots](https://django-components.github.io/django-components/docs/concepts/fundamentals/slots/) docs for more info.

    - Function signature:

        1. All parameters are now passed under a single `ctx` argument.

            You can still access all the same parameters via `ctx.context`, `ctx.data`, and `ctx.fallback`.

        2. `context` and `fallback` now may be `None` if the slot function was called outside of `{% slot %}` tag.

        Before:


        ```py
        def slot_fn(context: Context, data: Dict, slot_ref: SlotRef):
            isinstance(context, Context)
            isinstance(data, Dict)
            isinstance(slot_ref, SlotRef)

            return "CONTENT"
        ```


        After:


        ```py
        def slot_fn(ctx: SlotContext):
            assert isinstance(ctx.context, Context) # May be None
            assert isinstance(ctx.data, Dict)
            assert isinstance(ctx.fallback, SlotFallback) # May be None

            return "CONTENT"
        ```


    - Calling slot functions:

        1. Rather than calling the slot functions directly, you should now call the `Slot` instances.

        2. All parameters are now optional.

        3. The order of parameters has changed.

        Before:


        ```py
        def slot_fn(context: Context, data: Dict, slot_ref: SlotRef):
            return "CONTENT"

        html = slot_fn(context, data, slot_ref)
        ```


        After:


        ```py
        def slot_fn(ctx: SlotContext):
            return "CONTENT"

        slot = Slot(slot_fn)
        html = slot()
        html = slot({"data1": "abc", "data2": "hello"})
        html = slot({"data1": "abc", "data2": "hello"}, fallback="FALLBACK")
        ```


    - Usage in components:

        Before:


        ```python
        class MyComponent(Component):
            def get_context_data(self, *args, **kwargs):
                slots = self.input.slots
                slot_fn = slots["my_slot"]
                html = slot_fn(context, data, slot_ref)
                return {
                    "html": html,
                }
        ```


        After:


        ```python
        class MyComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                slot_fn = slots["my_slot"]
                html = slot_fn(data)
                return {
                    "html": html,
                }
        ```


**Miscellaneous**

- The second argument to `render_dependencies()` is now `strategy` instead of `type`.

    Before:


    ```py
    render_dependencies(content, type="document")
    ```


    After:


    ```py
    render_dependencies(content, strategy="document")
    ```


#### Deprecation 🚨📢

**Component API**

- `Component.get_context_data()` is now deprecated. Use `Component.get_template_data()` instead.

    `get_template_data()` behaves the same way, but has a different function signature
    to accept also slots and context.

    Since `get_context_data()` is widely used, it will remain available until v2.

- `Component.get_template_name()` and `Component.get_template()` are now deprecated. Use `Component.template`,
`Component.template_file` or `Component.on_render()` instead.

    `Component.get_template_name()` and `Component.get_template()` will be removed in v1.

    In v1, each Component will have at most one static template.
    This is needed to enable support for Markdown, Pug, or other pre-processing of templates by extensions.

    If you are using the deprecated methods to point to different templates, there's 2 ways to migrate:

    1. Split the single Component into multiple Components, each with its own template. Then switch between them in `Component.on_render()`:


        ```py
        class MyComponentA(Component):
            template_file = "a.html"

        class MyComponentB(Component):
            template_file = "b.html"

        class MyComponent(Component):
            def on_render(self, context, template):
                if context["a"]:
                    return MyComponentA.render(context)
                else:
                    return MyComponentB.render(context)
        ```


    2. Alternatively, use `Component.on_render()` with Django's `get_template()` to dynamically render different templates:


        ```py
        from django.template.loader import get_template

        class MyComponent(Component):
            def on_render(self, context, template):
                if context["a"]:
                    template_name = "a.html"
                else:
                    template_name = "b.html"

                actual_template = get_template(template_name)
                return actual_template.render(context)
        ```


    Read more in [django-components#1204](https://github.com/django-components/django-components/discussions/1204).

- The `type` kwarg in `Component.render()` and `Component.render_to_response()` is now deprecated. Use `deps_strategy` instead. The `type` kwarg will be removed in v1.

    Before:


    ```py
    Calendar.render_to_response(type="fragment")
    ```


    After:


    ```py
    Calendar.render_to_response(deps_strategy="fragment")
    ```


- The `render_dependencies` kwarg in `Component.render()` and `Component.render_to_response()` is now deprecated. Use `deps_strategy="ignore"` instead. The `render_dependencies` kwarg will be removed in v1.

    Before:


    ```py
    Calendar.render_to_response(render_dependencies=False)
    ```


    After:


    ```py
    Calendar.render_to_response(deps_strategy="ignore")
    ```


- Support for `Component` constructor kwargs `registered_name`, `outer_context`, and `registry` is deprecated, and will be removed in v1.

    Before, you could instantiate a standalone component,
    and then call `render()` on the instance:


    ```py
    comp = MyComponent(
        registered_name="my_component",
        outer_context=my_context,
        registry=my_registry,
    )
    comp.render(
        args=[1, 2, 3],
        kwargs={"a": 1, "b": 2},
        slots={"my_slot": "CONTENT"},
    )
    ```


    Now you should instead pass all that data to `Component.render()` / `Component.render_to_response()`:


    ```py
    MyComponent.render(
        args=[1, 2, 3],
        kwargs={"a": 1, "b": 2},
        slots={"my_slot": "CONTENT"},
        # NEW
        registered_name="my_component",
        outer_context=my_context,
        registry=my_registry,
    )
    ```


- `Component.input` (and its type `ComponentInput`) is now deprecated. The `input` property will be removed in v1.

    Instead, use attributes directly on the Component instance.

    Before:


    ```py
    class MyComponent(Component):
        def on_render(self, context, template):
            assert self.input.args == [1, 2, 3]
            assert self.input.kwargs == {"a": 1, "b": 2}
            assert self.input.slots == {"my_slot": "CONTENT"}
            assert self.input.context == {"my_slot": "CONTENT"}
            assert self.input.deps_strategy == "document"
            assert self.input.type == "document"
            assert self.input.render_dependencies == True
    ```


    After:


    ```py
    class MyComponent(Component):
        def on_render(self, context, template):
            assert self.args == [1, 2, 3]
            assert self.kwargs == {"a": 1, "b": 2}
            assert self.slots == {"my_slot": "CONTENT"}
            assert self.context == {"my_slot": "CONTENT"}
            assert self.deps_strategy == "document"
            assert (self.deps_strategy != "ignore") is True
    ```


- Component method `on_render_after` was updated to receive also `error` field.

    For backwards compatibility, the `error` field can be omitted until v1.

    Before:


    ```py
    def on_render_after(
        self,
        context: Context,
        template: Template,
        html: str,
    ) -> None:
        pass
    ```


    After:


    ```py
    def on_render_after(
        self,
        context: Context,
        template: Template,
        html: Optional[str],
        error: Optional[Exception],
    ) -> None:
        pass
    ```


- If you are using the Components as views, the way to access the component class is now different.

    Instead of `self.component`, use `self.component_cls`. `self.component` will be removed in v1.

    Before:


    ```py
    class MyView(View):
        def get(self, request):
            return self.component.render_to_response(request=request)
    ```


    After:


    ```py
    class MyView(View):
        def get(self, request):
            return self.component_cls.render_to_response(request=request)
    ```


**Extensions**

- In the `on_component_data()` extension hook, the `context_data` field of the context object was superseded by `template_data`.

    The `context_data` field will be removed in v1.0.

    Before:


    ```py
    class MyExtension(ComponentExtension):
        def on_component_data(self, ctx: OnComponentDataContext) -> None:
            ctx.context_data["my_template_var"] = "my_value"
    ```


    After:


    ```py
    class MyExtension(ComponentExtension):
        def on_component_data(self, ctx: OnComponentDataContext) -> None:
            ctx.template_data["my_template_var"] = "my_value"
    ```


- When creating extensions, the `ComponentExtension.ExtensionClass` attribute was renamed to `ComponentConfig`.

    The old name is deprecated and will be removed in v1.

    Before:


    ```py
    from django_components import ComponentExtension

    class MyExtension(ComponentExtension):
        class ExtensionClass(ComponentExtension.ExtensionClass):
            pass
    ```


    After:


    ```py
    from django_components import ComponentExtension, ExtensionComponentConfig

    class MyExtension(ComponentExtension):
        class ComponentConfig(ExtensionComponentConfig):
            pass
    ```


- When creating extensions, to access the Component class from within the methods of the extension nested classes,
  use `component_cls`.

    Previously this field was named `component_class`. The old name is deprecated and will be removed in v1.

   `ComponentExtension.ExtensionClass` attribute was renamed to `ComponentConfig`.

    The old name is deprecated and will be removed in v1.

    Before:


    ```py
    from django_components import ComponentExtension, ExtensionComponentConfig

    class LoggerExtension(ComponentExtension):
        name = "logger"

        class ComponentConfig(ExtensionComponentConfig):
            def log(self, msg: str) -> None:
                print(f"{self.component_class.__name__}: {msg}")
    ```


    After:


    ```py
    from django_components import ComponentExtension, ExtensionComponentConfig

    class LoggerExtension(ComponentExtension):
        name = "logger"

        class ComponentConfig(ExtensionComponentConfig):
            def log(self, msg: str) -> None:
                print(f"{self.component_cls.__name__}: {msg}")
    ```


**Slots**

- `SlotContent` was renamed to `SlotInput`. The old name is deprecated and will be removed in v1.

- `SlotRef` was renamed to `SlotFallback`. The old name is deprecated and will be removed in v1.

- The `default` kwarg in `{% fill %}` tag was renamed to `fallback`. The old name is deprecated and will be removed in v1.

    Before:


    ```django
    {% fill "footer" default="footer" %}
        {{ footer }}
    {% endfill %}
    ```


    After:


    ```django
    {% fill "footer" fallback="footer" %}
        {{ footer }}
    {% endfill %}
    ```


- The template variable `{{ component_vars.is_filled }}` is now deprecated. Will be removed in v1. Use `{{ component_vars.slots }}` instead.

    Before:


    ```django
    {% if component_vars.is_filled.footer %}
        <div>
            {% slot "footer" / %}
        </div>
    {% endif %}
    ```


    After:


    ```django
    {% if component_vars.slots.footer %}
        <div>
            {% slot "footer" / %}
        </div>
    {% endif %}
    ```


    NOTE: `component_vars.is_filled` automatically escaped slot names, so that even slot names that are
    not valid python identifiers could be set as slot names. `component_vars.slots` no longer does that.

- Component attribute `Component.is_filled` is now deprecated. Will be removed in v1. Use `Component.slots` instead.

    Before:


    ```py
    class MyComponent(Component):
        def get_template_data(self, args, kwargs, slots, context):
            if self.is_filled.footer:
                color = "red"
            else:
                color = "blue"

            return {
                "color": color,
            }
    ```


    After:


    ```py
    class MyComponent(Component):
        def get_template_data(self, args, kwargs, slots, context):
            if "footer" in slots:
                color = "red"
            else:
                color = "blue"

            return {
                "color": color,
            }
    ```


    NOTE: `Component.is_filled` automatically escaped slot names, so that even slot names that are
    not valid python identifiers could be set as slot names. `Component.slots` no longer does that.

**Miscellaneous**

- Template caching with `cached_template()` helper and `template_cache_size` setting is deprecated.
    These will be removed in v1.

    This feature made sense if you were dynamically generating templates for components using
    `Component.get_template_string()` and `Component.get_template()`.

    However, in v1, each Component will have at most one static template. This static template
    is cached internally per component class, and reused across renders.

    This makes the template caching feature obsolete.

    If you relied on `cached_template()`, you should either:

    1. Wrap the templates as Components.
    2. Manage the cache of Templates yourself.

- The `debug_highlight_components` and `debug_highlight_slots` settings are deprecated.
    These will be removed in v1.

    The debug highlighting feature was re-implemented as an extension.
    As such, the recommended way for enabling it has changed:

    Before:


    ```python
    COMPONENTS = ComponentsSettings(
        debug_highlight_components=True,
        debug_highlight_slots=True,
    )
    ```


    After:

    Set `extensions_defaults` in your `settings.py` file.


    ```python
    COMPONENTS = ComponentsSettings(
        extensions_defaults={
            "debug_highlight": {
                "highlight_components": True,
                "highlight_slots": True,
            },
        },
    )
    ```


    Alternatively, you can enable highlighting for specific components by setting `Component.DebugHighlight.highlight_components` to `True`:


    ```python
    class MyComponent(Component):
        class DebugHighlight:
            highlight_components = True
            highlight_slots = True
    ```


#### Feat

- New method to render template variables - `get_template_data()`

    `get_template_data()` behaves the same way as `get_context_data()`, but has
    a different function signature to accept also slots and context.


    ```py
    class Button(Component):
        def get_template_data(self, args, kwargs, slots, context):
            return {
                "val1": args[0],
                "val2": kwargs["field"],
            }
    ```


    If you define `Component.Args`, `Component.Kwargs`, `Component.Slots`, then
    the `args`, `kwargs`, `slots` arguments will be instances of these classes:


    ```py
    class Button(Component):
        class Args(NamedTuple):
            field1: str

        class Kwargs(NamedTuple):
            field2: int

        def get_template_data(self, args: Args, kwargs: Kwargs, slots, context):
            return {
                "val1": args.field1,
                "val2": kwargs.field2,
            }
    ```


- Input validation is now part of the render process.

    When you specify the input types (such as `Component.Args`, `Component.Kwargs`, etc),
    the actual inputs to data methods (`Component.get_template_data()`, etc) will be instances of the types you specified.

    This practically brings back input validation, because the instantiation of the types
    will raise an error if the inputs are not valid.

    Read more on [Typing and validation](https://django-components.github.io/django-components/docs/concepts/fundamentals/typing_and_validation/)

- Render emails or other non-browser HTML with new "dependencies strategies"

    When rendering a component with `Component.render()` or `Component.render_to_response()`,
    the `deps_strategy` kwarg (previously `type`) now accepts additional options:

    - `"simple"`
    - `"prepend"`
    - `"append"`
    - `"ignore"`


    ```py
    Calendar.render_to_response(
        request=request,
        kwargs={
            "date": request.GET.get("date", ""),
        },
        deps_strategy="append",
    )
    ```


    Comparison of dependencies render strategies:

    - `"document"`
        - Smartly inserts JS / CSS into placeholders or into `<head>` and `<body>` tags.
        - Inserts extra script to allow `fragment` strategy to work.
        - Assumes the HTML will be rendered in a JS-enabled browser.
    - `"fragment"`
        - A lightweight HTML fragment to be inserted into a document with AJAX.
        - Ignores placeholders and any `<head>` / `<body>` tags.
        - No JS / CSS included.
    - `"simple"`
        - Smartly insert JS / CSS into placeholders or into `<head>` and `<body>` tags.
        - No extra script loaded.
    - `"prepend"`
        - Insert JS / CSS before the rendered HTML.
        - Ignores placeholders and any `<head>` / `<body>` tags.
        - No extra script loaded.
    - `"append"`
        - Insert JS / CSS after the rendered HTML.
        - Ignores placeholders and any `<head>` / `<body>` tags.
        - No extra script loaded.
    - `"ignore"`
        - Rendered HTML is left as-is. You can still process it with a different strategy later with `render_dependencies()`.
        - Used for inserting rendered HTML into other components.

    See [Dependencies rendering](https://django-components.github.io/django-components/0.140.1/concepts/advanced/rendering_js_css/) for more info.

- New `Component.args`, `Component.kwargs`, `Component.slots` attributes available on the component class itself.

    These attributes are the same as the ones available in `Component.get_template_data()`.

    You can use these in other methods like `Component.on_render_before()` or `Component.on_render_after()`.


    ```py
    from django_components import Component, SlotInput

    class Table(Component):
        class Args(NamedTuple):
            page: int

        class Kwargs(NamedTuple):
            per_page: int

        class Slots(NamedTuple):
            content: SlotInput

        def on_render_before(self, context: Context, template: Optional[Template]) -> None:
            assert self.args.page == 123
            assert self.kwargs.per_page == 10
            content_html = self.slots.content()
    ```


    Same as with the parameters in `Component.get_template_data()`, they will be instances of the `Args`, `Kwargs`, `Slots` classes
    if defined, or plain lists / dictionaries otherwise.

- 4 attributes that were previously available only under the `Component.input` attribute
    are now available directly on the Component instance:

    - `Component.raw_args`
    - `Component.raw_kwargs`
    - `Component.raw_slots`
    - `Component.deps_strategy`

    The first 3 attributes are the same as the deprecated `Component.input.args`, `Component.input.kwargs`, `Component.input.slots` properties.

    Compared to the `Component.args` / `Component.kwargs` / `Component.slots` attributes,
    these "raw" attributes are not typed and will remain as plain lists / dictionaries
    even if you define the `Args`, `Kwargs`, `Slots` classes.

    The `Component.deps_strategy` attribute is the same as the deprecated `Component.input.deps_strategy` property.

- New template variables `{{ component_vars.args }}`, `{{ component_vars.kwargs }}`, `{{ component_vars.slots }}`

    These attributes are the same as the ones available in `Component.get_template_data()`.


    ```django
    {# Typed #}
    {% if component_vars.args.page == 123 %}
        <div>
            {% slot "content" / %}
        </div>
    {% endif %}

    {# Untyped #}
    {% if component_vars.args.0 == 123 %}
        <div>
            {% slot "content" / %}
        </div>
    {% endif %}
    ```


    Same as with the parameters in `Component.get_template_data()`, they will be instances of the `Args`, `Kwargs`, `Slots` classes
    if defined, or plain lists / dictionaries otherwise.

- New component lifecycle hook `Component.on_render()`.

    This hook is called when the component is being rendered.

    You can override this method to:

    - Change what template gets rendered
    - Modify the context
    - Modify the rendered output after it has been rendered
    - Handle errors

    See [on_render](https://django-components.github.io/django-components/0.140.1/concepts/advanced/hooks/#on_render) for more info.

- `get_component_url()` now optionally accepts `query` and `fragment` arguments.


    ```py
    from django_components import get_component_url

    url = get_component_url(
        MyComponent,
        query={"foo": "bar"},
        fragment="baz",
    )
    # /components/ext/view/components/c1ab2c3?foo=bar#baz
    ```


- The `BaseNode` class has a new `contents` attribute, which contains the raw contents (string) of the tag body.

    This is relevant when you define custom template tags with `@template_tag` decorator or `BaseNode` class.

    When you define a custom template tag like so:


    ```py
    from django_components import BaseNode, template_tag

    @template_tag(
        library,
        tag="mytag",
        end_tag="endmytag",
        allowed_flags=["required"]
    )
    def mytag(node: BaseNode, context: Context, name: str, **kwargs) -> str:
        print(node.contents)
        return f"Hello, {name}!"
    ```


    And render it like so:


    ```django
    {% mytag name="John" %}
        Hello, world!
    {% endmytag %}
    ```


    Then, the `contents` attribute of the `BaseNode` instance will contain the string `"Hello, world!"`.

- The `BaseNode` class also has two new metadata attributes:

    - `template_name` - the name of the template that rendered the node.
    - `template_component` - the component class that the template belongs to.

    This is useful for debugging purposes.

- `Slot` class now has 3 new metadata fields:

    1. `Slot.contents` attribute contains the original contents:

        - If `Slot` was created from `{% fill %}` tag, `Slot.contents` will contain the body of the `{% fill %}` tag.
        - If `Slot` was created from string via `Slot("...")`, `Slot.contents` will contain that string.
        - If `Slot` was created from a function, `Slot.contents` will contain that function.

    2. `Slot.extra` attribute where you can put arbitrary metadata about the slot.

    3. `Slot.fill_node` attribute tells where the slot comes from:

        - `FillNode` instance if the slot was created from `{% fill %}` tag.
        - `ComponentNode` instance if the slot was created as a default slot from a `{% component %}` tag.
        - `None` if the slot was created from a string, function, or `Slot` instance.

    See [Slot metadata](https://django-components.github.io/django-components/0.140.1/concepts/fundamentals/slots/#slot-metadata).

- `{% fill %}` tag now accepts `body` kwarg to pass a Slot instance to fill.

    First pass a `Slot` instance to the template
    with the `get_template_data()` method:


    ```python
    from django_components import component, Slot

    class Table(Component):
      def get_template_data(self, args, kwargs, slots, context):
        return {
            "my_slot": Slot(lambda ctx: "Hello, world!"),
        }
    ```


    Then pass the slot to the `{% fill %}` tag:


    ```django
    {% component "table" %}
      {% fill "pagination" body=my_slot / %}
    {% endcomponent %}
    ```


- You can now access the `{% component %}` tag (`ComponentNode` instance) from which a Component
    was created. Use `Component.node` to access it.

    This is mostly useful for extensions, which can use this to detect if the given Component
    comes from a `{% component %}` tag or from a different source (such as `Component.render()`).

    `Component.node` is `None` if the component is created by `Component.render()` (but you
    can pass in the `node` kwarg yourself).


    ```py
    class MyComponent(Component):
        def get_template_data(self, context, template):
            if self.node is not None:
                assert self.node.name == "my_component"
    ```


- Node classes `ComponentNode`, `FillNode`, `ProvideNode`, and `SlotNode` are part of the public API.

    These classes are what is instantiated when you use `{% component %}`, `{% fill %}`, `{% provide %}`, and `{% slot %}` tags.

    You can for example use these for type hints:


    ```py
    from django_components import Component, ComponentNode

    class MyTable(Component):
        def get_template_data(self, args, kwargs, slots, context):
            if kwargs.get("show_owner"):
                node: Optional[ComponentNode] = self.node
                owner: Optional[Component] = self.node.template_component
            else:
                node = None
                owner = None

            return {
                "owner": owner,
                "node": node,
            }
    ```


- Component caching can now take slots into account, by setting `Component.Cache.include_slots` to `True`.


    ```py
    class MyComponent(Component):
        class Cache:
            enabled = True
            include_slots = True
    ```


    In which case the following two calls will generate separate cache entries:


    ```django
    {% component "my_component" position="left" %}
        Hello, Alice
    {% endcomponent %}

    {% component "my_component" position="left" %}
        Hello, Bob
    {% endcomponent %}
    ```


    Same applies to `Component.render()` with string slots:


    ```py
    MyComponent.render(
        kwargs={"position": "left"},
        slots={"content": "Hello, Alice"}
    )
    MyComponent.render(
        kwargs={"position": "left"},
        slots={"content": "Hello, Bob"}
    )
    ```


    Read more on [Component caching](https://django-components.github.io/django-components/0.140.1/concepts/advanced/component_caching/).

- New extension hook `on_slot_rendered()`

    This hook is called when a slot is rendered, and allows you to access and/or modify the rendered result.

    This is used by the ["debug highlight" feature](https://django-components.github.io/django-components/0.140.1/guides/other/troubleshooting/#component-and-slot-highlighting).

    To modify the rendered result, return the new value:


    ```py
    class MyExtension(ComponentExtension):
        def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
            return ctx.result + "<!-- Hello, world! -->"
    ```


    If you don't want to modify the rendered result, return `None`.

    See all [Extension hooks](https://django-components.github.io/django-components/0.140.1/reference/extension_hooks/).

- When creating extensions, the previous syntax with `ComponentExtension.ExtensionClass` was causing
  Mypy errors, because Mypy doesn't allow using class attributes as bases:

    Before:


    ```py
    from django_components import ComponentExtension

    class MyExtension(ComponentExtension):
        class ExtensionClass(ComponentExtension.ExtensionClass):  # Error!
            pass
    ```


    Instead, you can import `ExtensionComponentConfig` directly:

    After:


    ```py
    from django_components import ComponentExtension, ExtensionComponentConfig

    class MyExtension(ComponentExtension):
        class ComponentConfig(ExtensionComponentConfig):
            pass
    ```


#### Refactor

- When a component is being rendered, a proper `Component` instance is now created.

    Previously, the `Component` state was managed as half-instance, half-stack.

- Component's "Render API" (args, kwargs, slots, context, inputs, request, context data, etc)
  can now be accessed also outside of the render call. So now its possible to take the component
  instance out of `get_template_data()` (although this is not recommended).

- Components can now be defined without a template.

    Previously, the following would raise an error:


    ```py
    class MyComponent(Component):
        pass
    ```


    "Template-less" components can be used together with `Component.on_render()` to dynamically
    pick what to render:


    ```py
    class TableNew(Component):
        template_file = "table_new.html"

    class TableOld(Component):
        template_file = "table_old.html"

    class Table(Component):
        def on_render(self, context, template):
            if self.kwargs.get("feat_table_new_ui"):
                return TableNew.render(args=self.args, kwargs=self.kwargs, slots=self.slots)
            else:
                return TableOld.render(args=self.args, kwargs=self.kwargs, slots=self.slots)
    ```


    "Template-less" components can be also used as a base class for other components, or as mixins.

- Passing `Slot` instance to `Slot` constructor raises an error.

- Extension hook `on_component_rendered` now receives `error` field.

    `on_component_rendered` now behaves similar to `Component.on_render_after`:

    - Raising error in this hook overrides what error will be returned from `Component.render()`.
    - Returning new string overrides what will be returned from `Component.render()`.

    Before:


    ```py
    class OnComponentRenderedContext(NamedTuple):
        component: "Component"
        component_cls: Type["Component"]
        component_id: str
        result: str
    ```


    After:


    ```py
    class OnComponentRenderedContext(NamedTuple):
        component: "Component"
        component_cls: Type["Component"]
        component_id: str
        result: Optional[str]
        error: Optional[Exception]
    ```


#### Fix

- Fix bug: Context processors data was being generated anew for each component. Now the data is correctly created once and reused across components with the same request ([#1165](https://github.com/django-components/django-components/issues/1165)).

- Fix KeyError on `component_context_cache` when slots are rendered outside of the component's render context. ([#1189](https://github.com/django-components/django-components/issues/1189))

- Component classes now have `do_not_call_in_templates=True` to prevent them from being called as functions in templates.