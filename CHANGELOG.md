# Release notes

## 🚨📢 v0.140.0

⚠️ Major release ⚠️ - Please test thoroughly before / after upgrading.

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

#### 🚨📢 BREAKING CHANGES

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

    See [Dependencies rendering](https://django-components.github.io/django-components/0.140/concepts/advanced/rendering_js_css/) for more info.

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

    See [Migrating from generics to class attributes](https://django-components.github.io/django-components/0.140/concepts/fundamentals/typing_and_validation/#migrating-from-generics-to-class-attributes) for more info.

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
        args: Optional[Tuple[Any, ...]] = None,
        kwargs: Optional[Mapping] = None,
        slots: Optional[Mapping] = None,
        deps_strategy: DependenciesStrategy = "document",
        render_dependencies: bool = True,
        request: Optional[HttpRequest] = None,
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

- Slot functions behavior has changed. See the new [Slots](https://django-components.github.io/django-components/latest/concepts/fundamentals/slots/) docs for more info.

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

#### 🚨📢 Deprecation

**Component API**

- `Component.get_context_data()` is now deprecated. Use `Component.get_template_data()` instead.

    `get_template_data()` behaves the same way, but has a different function signature
    to accept also slots and context.

    Since `get_context_data()` is widely used, it will remain available until v2.

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
        class ExtensionClass(ComponentExtension.ComponentConfig):
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

    Read more on [Typing and validation](https://django-components.github.io/django-components/latest/concepts/fundamentals/typing_and_validation/)

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

    See [Dependencies rendering](https://django-components.github.io/django-components/0.140/concepts/advanced/rendering_js_css/) for more info.

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

        def on_render_before(self, context: Context, template: Template) -> None:
            assert self.args.page == 123
            assert self.kwargs.per_page == 10
            content_html = self.slots.content()
    ```

    Same as with the parameters in `Component.get_template_data()`, they will be instances of the `Args`, `Kwargs`, `Slots` classes
    if defined, or plain lists / dictionaries otherwise.

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

- `Slot` class now has a `Slot.contents` attribute, which contains the original contents:

    - If `Slot` was created from `{% fill %}` tag, `Slot.contents` will contain the body of the `{% fill %}` tag.
    - If `Slot` was created from string via `Slot("...")`, `Slot.contents` will contain that string.
    - If `Slot` was created from a function, `Slot.contents` will contain that function.

- `{% fill %}` tag now accepts `body` kwarg to pass a Slot instance to fill.

    First pass a [`Slot`](../api#django_components.Slot) instance to the template
    with the [`get_template_data()`](../api#django_components.Component.get_template_data)
    method:

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

    Read more on [Component caching](https://django-components.github.io/django-components/0.140/concepts/advanced/component_caching/).

- New extension hook `on_slot_rendered()`

    This hook is called when a slot is rendered, and allows you to access and/or modify the rendered result.

    This is used by the ["debug highlight" feature](https://django-components.github.io/django-components/0.140/guides/other/troubleshooting/#component-and-slot-highlighting).

    To modify the rendered result, return the new value:

    ```py
    class MyExtension(ComponentExtension):
        def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
            return ctx.result + "<!-- Hello, world! -->"
    ```

    If you don't want to modify the rendered result, return `None`.

    See all [Extension hooks](https://django-components.github.io/django-components/0.140/reference/extension_hooks/).

- When creating extensions, the previous syntax with `ComponentExtension.ExtensionClass` was causing
  Mypy errors, because Mypy doesn't allow using class attributes as bases:

    Before:

    ```py
    from django_components import ComponentExtension

    class MyExtension(ComponentExtension):
        class ExtensionClass(ComponentExtension.ComponentConfig):  # Error!
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

- Passing `Slot` instance to `Slot` constructor raises an error.

#### Fix

- Fix bug: Context processors data was being generated anew for each component. Now the data is correctly created once and reused across components with the same request ([#1165](https://github.com/django-components/django-components/issues/1165)).

- Fix KeyError on `component_context_cache` when slots are rendered outside of the component's render context. ([#1189](https://github.com/django-components/django-components/issues/1189))

- Component classes now have `do_not_call_in_templates=True` to prevent them from being called as functions in templates.

## v0.139.1

#### Fix

- Fix compatibility of component caching with `{% extend %}` block ([#1135](https://github.com/django-components/django-components/issues/1135))

#### Refactor

- Component ID is now prefixed with `c`, e.g. `c123456`.

- When typing a Component, you can now specify as few or as many parameters as you want.

    ```py
    Component[Args]
    Component[Args, Kwargs]
    Component[Args, Kwargs, Slots]
    Component[Args, Kwargs, Slots, Data]
    Component[Args, Kwargs, Slots, Data, JsData]
    Component[Args, Kwargs, Slots, Data, JsData, CssData]
    ```

    All omitted parameters will default to `Any`.

- Added `typing_extensions` to the project as a dependency

- Multiple extensions with the same name (case-insensitive) now raise an error

- Extension names (case-insensitive) also MUST NOT conflict with existing Component class API.
  
    So if you name an extension `render`, it will conflict with the `render()` method of the `Component` class,
    and thus raise an error.

## v0.139.0

#### Fix

- Fix bug: Fix compatibility with `Finder.find()` in Django 5.2 ([#1119](https://github.com/django-components/django-components/issues/1119))

## v0.138

#### Fix

- Fix bug: Allow components with `Url.public = True` to be defined before `django.setup()`

## v0.137

#### Feat

- Each Component class now has a `class_id` attribute, which is unique to the component subclass.

    NOTE: This is different from `Component.id`, which is unique to each rendered instance.

    To look up a component class by its `class_id`, use `get_component_by_class_id()`.

- It's now easier to create URLs for component views.

    Before, you had to call `Component.as_view()` and pass that to `urlpatterns`.
    
    Now this can be done for you if you set `Component.Url.public` to `True`:

    ```py
    class MyComponent(Component):
        class Url:
            public = True
        ...
    ```

    Then, to get the URL for the component, use `get_component_url()`:

    ```py
    from django_components import get_component_url

    url = get_component_url(MyComponent)
    ```

    This way you don't have to mix your app URLs with component URLs.

    Read more on [Component views and URLs](https://django-components.github.io/django-components/0.137/concepts/fundamentals/component_views_urls/).

- Per-component caching - Set `Component.Cache.enabled` to `True` to enable caching for a component.

    Component caching allows you to store the rendered output of a component. Next time the component is rendered
    with the same input, the cached output is returned instead of re-rendering the component.

    ```py
    class TestComponent(Component):
        template = "Hello"

        class Cache:
            enabled = True
            ttl = 0.1  # .1 seconds TTL
            cache_name = "custom_cache"

            # Custom hash method for args and kwargs
            # NOTE: The default implementation simply serializes the input into a string.
            #       As such, it might not be suitable for complex objects like Models.
            def hash(self, *args, **kwargs):
                return f"{json.dumps(args)}:{json.dumps(kwargs)}"

    ```

    Read more on [Component caching](https://django-components.github.io/django-components/0.137/concepts/advanced/component_caching/).

- `@djc_test` can now be called without first calling `django.setup()`, in which case it does it for you.

- Expose `ComponentInput` class, which is a typing for `Component.input`.

#### Deprecation

- Currently, view request handlers such as `get()` and `post()` methods can be defined
  directly on the `Component` class:

    ```py
    class MyComponent(Component):
        def get(self, request):
            return self.render_to_response()
    ```

    Or, nested within the `Component.View` class:

    ```py
    class MyComponent(Component):
        class View:
            def get(self, request):
                return self.render_to_response()
    ```

    In v1, these methods should be defined only on the `Component.View` class instead.

#### Refactor

- `Component.get_context_data()` can now omit a return statement or return `None`.

## 🚨📢 v0.136

#### 🚨📢 BREAKING CHANGES

- Component input validation was moved to a separate extension [`djc-ext-pydantic`](https://github.com/django-components/djc-ext-pydantic).

    If you relied on components raising errors when inputs were invalid, you need to install `djc-ext-pydantic` and add it to extensions:

    ```python
    # settings.py
    COMPONENTS = {
        "extensions": [
            "djc_pydantic.PydanticExtension",
        ],
    }
    ```

#### Fix

- Make it possible to resolve URLs added by extensions by their names

## v0.135

#### Feat

- Add defaults for the component inputs with the `Component.Defaults` nested class. Defaults
  are applied if the argument is not given, or if it set to `None`.
  
  For lists, dictionaries, or other objects, wrap the value in `Default()` class to mark it as a factory
  function:

    ```python
    from django_components import Default

    class Table(Component):
        class Defaults:
            position = "left"
            width = "200px"
            options = Default(lambda: ["left", "right", "center"])

        def get_context_data(self, position, width, options):
            return {
                "position": position,
                "width": width,
                "options": options,
            }

    # `position` is used as given, `"right"`
    # `width` uses default because it's `None`
    # `options` uses default because it's missing
    Table.render(
        kwargs={
            "position": "right",
            "width": None,
        }
    )
    ```

- `{% html_attrs %}` now offers a Vue-like granular control over `class` and `style` HTML attributes,
where each class name or style property can be managed separately.

    ```django
    {% html_attrs
        class="foo bar"
        class={"baz": True, "foo": False}
        class="extra"
    %}
    ```

    ```django
    {% html_attrs
        style="text-align: center; background-color: blue;"
        style={"background-color": "green", "color": None, "width": False}
        style="position: absolute; height: 12px;"
    %}
    ```

    Read more on [HTML attributes](https://django-components.github.io/django-components/0.135/concepts/fundamentals/html_attributes/).

#### Fix

- Fix compat with Windows when reading component files ([#1074](https://github.com/django-components/django-components/issues/1074))
- Fix resolution of component media files edge case ([#1073](https://github.com/django-components/django-components/issues/1073))

## v0.134

#### Fix

- HOTFIX: Fix the use of URLs in `Component.Media.js` and `Component.Media.css`

## v0.133

⚠️ Attention ⚠️ - Please update to v0.134 to fix bugs introduced in v0.132.

#### Fix

- HOTFIX: Fix the use of URLs in `Component.Media.js` and `Component.Media.css`

## v0.132

⚠️ Attention ⚠️ - Please update to v0.134 to fix bugs introduced in v0.132.

#### Feat

- Allow to use glob patterns as paths for additional JS / CSS in
  `Component.Media.js` and `Component.Media.css`

    ```py
    class MyComponent(Component):
        class Media:
            js = ["*.js"]
            css = ["*.css"]
    ```

#### Fix

- Fix installation for Python 3.13 on Windows.

## v0.131

#### Feat

- Support for extensions (plugins) for django-components!

    - Hook into lifecycle events of django-components
    - Pre-/post-process component inputs, outputs, and templates
    - Add extra methods or attributes to Components
    - Add custom extension-specific CLI commands
    - Add custom extension-specific URL routes

    Read more on [Extensions](https://django-components.github.io/django-components/0.131/concepts/advanced/extensions/).

- New CLI commands:
    - `components list` - List all components
    - `components create <name>` - Create a new component (supersedes `startcomponent`)
    - `components upgrade` - Upgrade a component (supersedes `upgradecomponent`)
    - `components ext list` - List all extensions
    - `components ext run <extension> <command>` - Run a command added by an extension

- `@djc_test` decorator for writing tests that involve Components.

    - The decorator manages global state, ensuring that tests don't leak.
    - If using `pytest`, the decorator allows you to parametrize Django or Components settings.
    - The decorator also serves as a stand-in for Django's `@override_settings`.

    See the API reference for [`@djc_test`](https://django-components.github.io/django-components/0.131/reference/testing_api/#django_components.testing.djc_test) for more details.

- `ComponentRegistry` now has a `has()` method to check if a component is registered
   without raising an error.

- Get all created `Component` classes with `all_components()`.

- Get all created `ComponentRegistry` instances with `all_registries()`.

#### Refactor

- The `startcomponent` and `upgradecomponent` commands are deprecated, and will be removed in v1.

    Instead, use `components create <name>` and `components upgrade`.

#### Internal

- Settings are now loaded only once, and thus are considered immutable once loaded. Previously,
  django-components would load settings from `settings.COMPONENTS` on each access. The new behavior
  aligns with Django's settings.

## v0.130

#### Feat

- Access the HttpRequest object under `Component.request`.

    To pass the request object to a component, either:
    - Render a template or component with `RequestContext`,
    - Or set the `request` kwarg to `Component.render()` or `Component.render_to_response()`.

    Read more on [HttpRequest](https://django-components.github.io/django-components/0.130/concepts/fundamentals/http_request/).

- Access the context processors data under `Component.context_processors_data`.

    Context processors data is available only when the component has access to the `request` object,
    either by:
    - Passing the request to `Component.render()` or `Component.render_to_response()`,
    - Or by rendering a template or component with `RequestContext`,
    - Or being nested in another component that has access to the request object.

    The data from context processors is automatically available within the component's template.

    Read more on [HttpRequest](https://django-components.github.io/django-components/0.130/concepts/fundamentals/http_request/).

## v0.129

#### Fix

- Fix thread unsafe media resolve validation by moving it to ComponentMedia `__post_init` ([#977](https://github.com/django-components/django-components/pull/977)
- Fix bug: Relative path in extends and include does not work when using template_file ([#976](https://github.com/django-components/django-components/pull/976)
- Fix error when template cache setting (`template_cache_size`) is set to 0 ([#974](https://github.com/django-components/django-components/pull/974)

## v0.128

#### Feat

- Configurable cache - Set [`COMPONENTS.cache`](https://django-components.github.io/django-components/0.128/reference/settings/#django_components.app_settings.ComponentsSettings.cache) to change where and how django-components caches JS and CSS files. ([#946](https://github.com/django-components/django-components/pull/946))

    Read more on [Caching](https://django-components.github.io/django-components/0.128/guides/setup/caching).

- Highlight coponents and slots in the UI - We've added two boolean settings [`COMPONENTS.debug_highlight_components`](https://django-components.github.io/django-components/0.128/reference/settings/#django_components.app_settings.ComponentsSettings.debug_highlight_components) and [`COMPONENTS.debug_highlight_slots`](https://django-components.github.io/django-components/0.128/reference/settings/#django_components.app_settings.ComponentsSettings.debug_highlight_slots), which can be independently set to `True`. First will wrap components in a blue border, the second will wrap slots in a red border. ([#942](https://github.com/django-components/django-components/pull/942))

    Read more on [Troubleshooting](https://django-components.github.io/django-components/0.128/guides/other/troubleshooting/#component-and-slot-highlighting).

#### Refactor

- Removed use of eval for node validation ([#944](https://github.com/django-components/django-components/pull/944))

#### Perf

- Components can now be infinitely nested. ([#936](https://github.com/django-components/django-components/pull/936))

- Component input validation is now 6-7x faster on CPython and PyPy. This previously made up 10-30% of the total render time. ([#945](https://github.com/django-components/django-components/pull/945))

## v0.127

#### Fix

- Fix component rendering when using `{% cache %}` with remote cache and multiple web servers ([#930](https://github.com/django-components/django-components/issues/930))

## v0.126

#### Refactor

- Replaced [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) with a custom HTML parser.
- The heuristic for inserting JS and CSS dependenies into the default place has changed.
    - JS is still inserted at the end of the `<body>`, and CSS at the end of `<head>`.
    - However, we find end of `<body>` by searching for **last** occurrence of `</body>`
    - And for the end of `<head>` we search for the **first** occurrence of `</head>`

## v0.125

⚠️ Attention ⚠️ - We migrated from `EmilStenstrom/django-components` to `django-components/django-components`.

**Repo name and documentation URL changed. Package name remains the same.**

If you see any broken links or other issues, please report them in [#922](https://github.com/django-components/django-components/issues/922).

#### Feat

- `@template_tag` and `BaseNode` - A decorator and a class that allow you to define
  custom template tags that will behave similarly to django-components' own template tags.

  Read more on [Template tags](https://django-components.github.io/django-components/0.125/concepts/advanced/template_tags/).

  Template tags defined with `@template_tag` and `BaseNode` will have the following features:

  - Accepting args, kwargs, and flags.

  - Allowing literal lists and dicts as inputs as:
  
     `key=[1, 2, 3]` or `key={"a": 1, "b": 2}`
  - Using template tags tag inputs as:
  
    `{% my_tag key="{% lorem 3 w %}" / %}`
  - Supporting the flat dictionary definition:
  
     `attr:key=value`
  - Spreading args and kwargs with `...`:
  
     `{% my_tag ...args ...kwargs / %}`
  - Being able to call the template tag as:
  
     `{% my_tag %} ... {% endmy_tag %}` or `{% my_tag / %}`


#### Refactor

- Refactored template tag input validation. When you now call template tags like
  `{% slot %}`, `{% fill %}`, `{% html_attrs %}`, and others, their inputs are now
  validated the same way as Python function inputs are.

    So, for example

    ```django
    {% slot "my_slot" name="content" / %}
    ```

    will raise an error, because the positional argument `name` is given twice.

    NOTE: Special kwargs whose keys are not valid Python variable names are not affected by this change.
    So when you define:

    ```django
    {% component data-id=123 / %}
    ```

    The `data-id` will still be accepted as a valid kwarg, assuming that your `get_context_data()`
    accepts `**kwargs`:

    ```py
    def get_context_data(self, **kwargs):
        return {
            "data_id": kwargs["data-id"],
        }
    ```

## v0.124

#### Feat

- Instead of inlining the JS and CSS under `Component.js` and `Component.css`, you can move
    them to their own files, and link the JS/CSS files with `Component.js_file`  and `Component.css_file`.

    Even when you specify the JS/CSS with `Component.js_file` or `Component.css_file`, then you can still
    access the content under `Component.js` or `Component.css` - behind the scenes, the content of the JS/CSS files
    will be set to `Component.js` / `Component.css` upon first access.

    The same applies to `Component.template_file`, which will populate `Component.template` upon first access.

    With this change, the role of `Component.js/css` and the JS/CSS in `Component.Media` has changed:

    - The JS/CSS defined in `Component.js/css` or `Component.js/css_file` is the "main" JS/CSS
    - The JS/CSS defined in `Component.Media.js/css` are secondary or additional

    See the updated ["Getting Started" tutorial](https://django-components.github.io/django-components/0.124/getting_started/adding_js_and_css/)

#### Refactor

- The canonical way to define a template file was changed from `template_name` to `template_file`, to align with the rest of the API.
  
    `template_name` remains for backwards compatibility. When you get / set `template_name`,
    internally this is proxied to `template_file`.

- The undocumented `Component.component_id` was removed. Instead, use `Component.id`. Changes:

    - While `component_id` was unique every time you instantiated `Component`, the new `id` is unique
    every time you render the component (e.g. with `Component.render()`)
    - The new `id` is available only during render, so e.g. from within `get_context_data()`

- Component's HTML / CSS / JS are now resolved and loaded lazily. That is, if you specify `template_name`/`template_file`,
  `js_file`, `css_file`, or `Media.js/css`, the file paths will be resolved only once you:
  
    1. Try to access component's HTML / CSS / JS, or
    2. Render the component.

    Read more on [Accessing component's HTML / JS / CSS](https://django-components.github.io/django-components/0.124/concepts/fundamentals/defining_js_css_html_files/#customize-how-paths-are-rendered-into-html-tags).

- Component inheritance:

    - When you subclass a component, the JS and CSS defined on parent's `Media` class is now inherited by the child component.
    - You can disable or customize Media inheritance by setting `extend` attribute on the `Component.Media` nested class. This work similarly to Django's [`Media.extend`](https://docs.djangoproject.com/en/5.2/topics/forms/media/#extend).
    - When child component defines either `template` or `template_file`, both of parent's `template` and `template_file` are ignored. The same applies to `js_file` and `css_file`.

- Autodiscovery now ignores files and directories that start with an underscore (`_`), except `__init__.py`

- The [Signals](https://docs.djangoproject.com/en/5.2/topics/signals/) emitted by or during the use of django-components are now documented, together the `template_rendered` signal.

## v0.123

#### Fix

- Fix edge cases around rendering components whose templates used the `{% extends %}` template tag ([#859](https://github.com/django-components/django-components/pull/859))

## v0.122

#### Feat

- Add support for HTML fragments. HTML fragments can be rendered by passing `type="fragment"` to `Component.render()` or `Component.render_to_response()`. Read more on how to [use HTML fragments with HTMX, AlpineJS, or vanillaJS](https://django-components.github.io/django-components/latest/concepts/advanced/html_fragments).

## v0.121

#### Fix

- Fix the use of Django template filters (`|lower:"etc"`) with component inputs [#855](https://github.com/django-components/django-components/pull/855).

## v0.120

⚠️ Attention ⚠️ - Please update to v0.121 to fix bugs introduced in v0.119.

#### Fix

- Fix the use of translation strings `_("bla")` as inputs to components [#849](https://github.com/django-components/django-components/pull/849).

## v0.119

⚠️ Attention ⚠️ - This release introduced bugs [#849](https://github.com/django-components/django-components/pull/849), [#855](https://github.com/django-components/django-components/pull/855). Please update to v0.121.

#### Fix

- Fix compatibility with custom subclasses of Django's `Template` that need to access
  `origin` or other initialization arguments. (https://github.com/django-components/django-components/pull/828)

#### Refactor

- Compatibility with `django-debug-toolbar-template-profiler`:
  - Monkeypatching of Django's `Template` now happens at `AppConfig.ready()` (https://github.com/django-components/django-components/pull/825)

- Internal parsing of template tags tag was updated. No API change. (https://github.com/django-components/django-components/pull/827)

## v0.118

#### Feat

- Add support for `context_processors` and `RenderContext` inside component templates

   `Component.render()` and `Component.render_to_response()` now accept an extra kwarg `request`.

    ```py
    def my_view(request)
        return MyTable.render_to_response(
            request=request
        )
    ```

   - When you pass in `request`, the component will use `RenderContext` instead of `Context`.
    Thus the context processors will be applied to the context.

   - NOTE: When you pass in both `request` and `context` to `Component.render()`, and `context` is already an instance of `Context`, the `request` kwarg will be ignored.

## v0.117

#### Fix

- The HTML parser no longer erronously inserts `<html><head><body>` on some occasions, and
  no longer tries to close unclosed HTML tags.

#### Refactor

- Replaced [Selectolax](https://github.com/rushter/selectolax) with [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) as project dependencies.

## v0.116

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Fix the order of execution of JS scripts:
  - Scripts in `Component.Media.js` are executed in the order they are defined
  - Scripts in `Component.js` are executed AFTER `Media.js` scripts

- Fix compatibility with AlpineJS
  - Scripts in `Component.Media.js` are now again inserted as `<script>` tags
  - By default, `Component.Media.js` are inserted as synchronous `<script>` tags,
    so the AlpineJS components registered in the `Media.js` scripts will now again
    run BEFORE the core AlpineJS script.

  AlpineJS can be configured like so:

  Option 1 - AlpineJS loaded in `<head>` with `defer` attribute:
  ```html
  <html>
    <head>
      {% component_css_dependencies %}
      <script defer src="https://unpkg.com/alpinejs"></script>
    </head>
    <body>
      {% component 'my_alpine_component' / %}
      {% component_js_dependencies %}
    </body>
  </html>
  ```

  Option 2 - AlpineJS loaded in `<body>` AFTER `{% component_js_depenencies %}`:
  ```html
  <html>
      <head>
          {% component_css_dependencies %}
      </head>
      <body>
          {% component 'my_alpine_component' / %}
          {% component_js_dependencies %}

          <script src="https://unpkg.com/alpinejs"></script>
      </body>
  </html>
  ```

## v0.115

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Fix integration with ManifestStaticFilesStorage on Windows by resolving component filepaths 
 (like `Component.template_name`) to POSIX paths.

## v0.114

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Prevent rendering Slot tags during fill discovery stage to fix a case when a component inside a slot
  fill tried to access provided data too early.

## v0.113

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Ensure consistent order of scripts in `Component.Media.js`

## v0.112

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Allow components to accept default fill even if no default slot was encountered during rendering

## v0.111

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

#### Fix

- Prevent rendering Component tags during fill discovery stage to fix a case when a component inside the default slot
  tried to access provided data too early.

## 🚨📢 v0.110

⚠️ Attention ⚠️ - Please update to v0.117 to fix known bugs. See [#791](https://github.com/django-components/django-components/issues/791) and [#789](https://github.com/django-components/django-components/issues/789) and [#818](https://github.com/django-components/django-components/issues/818).

### General

#### 🚨📢 BREAKING CHANGES

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

- For advanced use cases, use can omit the middleware and instead manage component JS and CSS dependencies yourself with [`render_dependencies`](https://github.com/django-components/django-components#render_dependencies-and-deep-dive-into-rendering-js--css-without-the-middleware)

- The [`ComponentRegistry`](../api#django_components.ComponentRegistry) settings [`RegistrySettings`](../api#django_components.RegistrySettings)
  were lowercased to align with the global settings:
  - `RegistrySettings.CONTEXT_BEHAVIOR` -> `RegistrySettings.context_behavior`
  - `RegistrySettings.TAG_FORMATTER` -> `RegistrySettings.tag_formatter`

  The old uppercase settings `CONTEXT_BEHAVIOR` and `TAG_FORMATTER` are deprecated and will be removed in v1.

- The setting `reload_on_template_change` was renamed to
  [`reload_on_file_change`](../settings#django_components.app_settings.ComponentsSettings#reload_on_file_change).
  And now it properly triggers server reload when any file in the component dirs change. The old name `reload_on_template_change`
  is deprecated and will be removed in v1.

- The setting `forbidden_static_files` was renamed to
  [`static_files_forbidden`](../settings#django_components.app_settings.ComponentsSettings#static_files_forbidden)
  to align with [`static_files_allowed`](../settings#django_components.app_settings.ComponentsSettings#static_files_allowed)
  The old name `forbidden_static_files` is deprecated and will be removed in v1.

### Tags

#### 🚨📢 BREAKING CHANGES

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

## 🚨📢 v0.100

#### BREAKING CHANGES

- `django_components.safer_staticfiles` app was removed. It is no longer needed.

- Installation changes:

    - Instead of defining component directories in `STATICFILES_DIRS`, set them to [`COMPONENTS.dirs`](https://github.com/django-components/django-components#dirs).
    - You now must define `STATICFILES_FINDERS`

    - [See here how to migrate your settings.py](https://github.com/django-components/django-components/blob/master/docs/migrating_from_safer_staticfiles.md)

#### Feat

- Beside the top-level `/components` directory, you can now define also app-level components dirs, e.g. `[app]/components`
  (See [`COMPONENTS.app_dirs`](https://github.com/django-components/django-components#app_dirs)).

#### Refactor

- When you call `as_view()` on a component instance, that instance will be passed to `View.as_view()`

## v0.97

#### Fix

- Fixed template caching. You can now also manually create cached templates with [`cached_template()`](https://github.com/django-components/django-components#template_cache_size---tune-the-template-cache)

#### Refactor

- The previously undocumented `get_template` was made private.

- In it's place, there's a new `get_template`, which supersedes `get_template_string` (will be removed in v1). The new `get_template` is the same as `get_template_string`, except
  it allows to return either a string or a Template instance.

- You now must use only one of `template`, `get_template`, `template_name`, or `get_template_name`.

## v0.96

#### Feat

- Run-time type validation for Python 3.11+ - If the `Component` class is typed, e.g. `Component[Args, Kwargs, ...]`, the args, kwargs, slots, and data are validated against the given types. (See [Runtime input validation with types](https://github.com/django-components/django-components#runtime-input-validation-with-types))

- Render hooks - Set `on_render_before` and `on_render_after` methods on `Component` to intercept or modify the template or context before rendering, or the rendered result afterwards. (See [Component hooks](https://github.com/django-components/django-components#component-hooks))

- `component_vars.is_filled` context variable can be accessed from within `on_render_before` and `on_render_after` hooks as `self.is_filled.my_slot`

## 0.95

#### Feat

- Added support for dynamic components, where the component name is passed as a variable. (See [Dynamic components](https://github.com/django-components/django-components#dynamic-components))

#### Refactor

- Changed `Component.input` to raise `RuntimeError` if accessed outside of render context. Previously it returned `None` if unset.

## v0.94

#### Feat

- django_components now automatically configures Django to support multi-line tags. (See [Multi-line tags](https://github.com/django-components/django-components#multi-line-tags))

- New setting `reload_on_template_change`. Set this to `True` to reload the dev server on changes to component template files. (See [Reload dev server on component file changes](https://github.com/django-components/django-components#reload-dev-server-on-component-file-changes))

## v0.93

#### Feat

- Spread operator `...dict` inside template tags. (See [Spread operator](https://github.com/django-components/django-components#spread-operator))

- Use template tags inside string literals in component inputs. (See [Use template tags inside component inputs](https://github.com/django-components/django-components#use-template-tags-inside-component-inputs))

- Dynamic slots, fills and provides - The `name` argument for these can now be a variable, a template expression, or via spread operator

- Component library authors can now configure `CONTEXT_BEHAVIOR` and `TAG_FORMATTER` settings independently from user settings.

## 🚨📢 v0.92

#### BREAKING CHANGES

- `Component` class is no longer a subclass of `View`. To configure the `View` class, set the `Component.View` nested class. HTTP methods like `get` or `post` can still be defined directly on `Component` class, and `Component.as_view()` internally calls `Component.View.as_view()`. (See [Modifying the View class](https://github.com/django-components/django-components#modifying-the-view-class))

#### Feat

- The inputs (args, kwargs, slots, context, ...) that you pass to `Component.render()` can be accessed from within `get_context_data`, `get_template` and `get_template_name` via `self.input`. (See [Accessing data passed to the component](https://github.com/django-components/django-components#accessing-data-passed-to-the-component))

- Typing: `Component` class supports generics that specify types for `Component.render` (See [Adding type hints with Generics](https://github.com/django-components/django-components#adding-type-hints-with-generics))

## v0.90

#### Feat

- All tags (`component`, `slot`, `fill`, ...) now support "self-closing" or "inline" form, where you can omit the closing tag:

    ```django
    {# Before #}
    {% component "button" %}{% endcomponent %}
    {# After #}
    {% component "button" / %}
    ```

- All tags now support the "dictionary key" or "aggregate" syntax (`kwarg:key=val`):

    ```django
    {% component "button" attrs:class="hidden" %}
    ```

- You can change how the components are written in the template with [TagFormatter](https://github.com/django-components/django-components#customizing-component-tags-with-tagformatter).

    The default is `django_components.component_formatter`:

    ```django
    {% component "button" href="..." disabled %}
        Click me!
    {% endcomponent %}
    ```

    While `django_components.shorthand_component_formatter` allows you to write components like so:

    ```django
    {% button href="..." disabled %}
        Click me!
    {% endbutton %}
    ```

## 🚨📢 v0.85

#### BREAKING CHANGES

- Autodiscovery module resolution changed. Following undocumented behavior was removed:

    - Previously, autodiscovery also imported any `[app]/components.py` files, and used `SETTINGS_MODULE` to search for component dirs.

        To migrate from:

        - `[app]/components.py` - Define each module in `COMPONENTS.libraries` setting,
            or import each module inside the `AppConfig.ready()` hook in respective `apps.py` files.

        - `SETTINGS_MODULE` - Define component dirs using `STATICFILES_DIRS`

    - Previously, autodiscovery handled relative files in `STATICFILES_DIRS`. To align with Django, `STATICFILES_DIRS` now must be full paths ([Django docs](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STATICFILES_DIRS)).

## 🚨📢 v0.81

#### BREAKING CHANGES

- The order of arguments to `render_to_response` has changed, to align with the (now public) `render` method of `Component` class.

#### Feat

- `Component.render()` is public and documented

- Slots passed `render_to_response` and `render` can now be rendered also as functions.

## v0.80

#### Feat

- Vue-like provide/inject with the `{% provide %}` tag and `inject()` method.

## 🚨📢 v0.79

#### BREAKING CHANGES

- Default value for the `COMPONENTS.context_behavior` setting was changes from `"isolated"` to `"django"`. If you did not set this value explicitly before, this may be a breaking change. See the rationale for change [here](https://github.com/django-components/django-components/issues/498).

## 🚨📢 v0.77

#### BREAKING

- The syntax for accessing default slot content has changed from

    ```django
    {% fill "my_slot" as "alias" %}
        {{ alias.default }}
    {% endfill %}

    ```

    to

    ```django
    {% fill "my_slot" default="alias" %}
        {{ alias }}
    {% endfill %}
    ```

## v0.74

#### Feat

- `{% html_attrs %}` tag for formatting data as HTML attributes

- `prefix:key=val` construct for passing dicts to components

## 🚨📢 v0.70

#### BREAKING CHANGES

- `{% if_filled "my_slot" %}` tags were replaced with `{{ component_vars.is_filled.my_slot }}` variables.

- Simplified settings - `slot_context_behavior` and `context_behavior` were merged. See the [documentation](https://github.com/django-components/django-components#context-behavior) for more details.

## v0.67

#### Refactor

- Changed the default way how context variables are resolved in slots. See the [documentation](https://github.com/django-components/django-components/tree/0.67#isolate-components-slots) for more details.

## 🚨📢 v0.50

#### BREAKING CHANGES

- `{% component_block %}` is now `{% component %}`, and `{% component %}` blocks need an ending `{% endcomponent %}` tag.

    The new `python manage.py upgradecomponent` command can be used to upgrade a directory (use `--path` argument to point to each dir) of templates that use components to the new syntax automatically.

    This change is done to simplify the API in anticipation of a 1.0 release of django_components. After 1.0 we intend to be stricter with big changes like this in point releases.

## v0.34

#### Feat

- Components as views, which allows you to handle requests and render responses from within a component. See the [documentation](https://github.com/django-components/django-components#use-components-as-views) for more details.

## v0.28

#### Feat

- 'implicit' slot filling and the `default` option for `slot` tags.

## v0.27

#### Feat

- A second installable app `django_components.safer_staticfiles`. It provides the same behavior as `django.contrib.staticfiles` but with extra security guarantees (more info below in [Security Notes](https://github.com/django-components/django-components#security-notes)).

## 🚨📢 v0.26

#### BREAKING CHANGES

- Changed the syntax for `{% slot %}` tags. From now on, we separate defining a slot (`{% slot %}`) from filling a slot with content (`{% fill %}`). This means you will likely need to change a lot of slot tags to fill.

    We understand this is annoying, but it's the only way we can get support for nested slots that fill in other slots, which is a very nice feature to have access to. Hoping that this will feel worth it!

## v0.22

#### Feat

- All files inside components subdirectores are autoimported to simplify setup.

    An existing project might start to get `AlreadyRegistered` errors because of this. To solve this, either remove your custom loading of components, or set `"autodiscover": False` in `settings.COMPONENTS`.

## v0.17

#### BREAKING CHANGES

- Renamed `Component.context` and `Component.template` to `get_context_data` and `get_template_name`. The old methods still work, but emit a deprecation warning.

    This change was done to sync naming with Django's class based views, and make using django-components more familiar to Django users. `Component.context` and `Component.template` will be removed when version 1.0 is released.
