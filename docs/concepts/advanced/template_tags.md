Template tags introduced by django-components, such as `{% component %}` and `{% slot %}`,
offer additional features over the default Django template tags:

<!-- # TODO - Update docs regarding literal lists and dictionaries
- Using literal lists and dictionaries
- Comments inside and tag with `{# ... #}`
-->
- [Self-closing tags `{% mytag / %}`](../../fundamentals/template_tag_syntax#self-closing-tags)
- [Allowing the use of `:`, `-` (and more) in keys](../../fundamentals/template_tag_syntax#special-characters)
- [Spread operator `...`](../../fundamentals/template_tag_syntax#spread-operator)
- [Using template tags as inputs to other template tags](../../fundamentals/template_tag_syntax#use-template-tags-inside-component-inputs)
- [Flat definition of dictionaries `attr:key=val`](../../fundamentals/template_tag_syntax#pass-dictonary-by-its-key-value-pairs)
- Function-like input validation

You too can easily create custom template tags that use the above features.

## Defining template tags with `@template_tag`

The simplest way to create a custom template tag is using
the [`template_tag`](../../../reference/api#django_components.template_tag) decorator.
This decorator allows you to define a template tag by just writing a function that returns the rendered content.

```python
from django.template import Context, Library
from django_components import BaseNode, template_tag

library = Library()

@template_tag(
    library,
    tag="mytag",
    end_tag="endmytag",
    allowed_flags=["required"]
)
def mytag(node: BaseNode, context: Context, name: str, **kwargs) -> str:
    return f"Hello, {name}!"
```

This will allow you to use the tag in your templates like this:

```django
{% mytag name="John" %}
{% endmytag %}

{# or with self-closing syntax #}
{% mytag name="John" / %}

{# or with flags #}
{% mytag name="John" required %}
{% endmytag %}
```

### Parameters

The [`@template_tag`](../../../reference/api#django_components.template_tag) decorator accepts the following parameters:

- `library`: The Django template library to register the tag with
- `tag`: The name of the template tag (e.g. `"mytag"` for `{% mytag %}`)
- `end_tag`: Optional. The name of the end tag (e.g. `"endmytag"` for `{% endmytag %}`)
- `allowed_flags`: Optional. List of flags that can be used with the tag (e.g. `["required"]` for `{% mytag required %}`)

### Function signature

The function decorated with [`@template_tag`](../../../reference/api#django_components.template_tag)
must accept at least two arguments:

1. `node`: The node instance (we'll explain this in detail in the next section)
2. `context`: The Django template context

Any additional parameters in your function's signature define what inputs your template tag accepts. For example:

```python
@template_tag(library, tag="greet")
def greet(
    node: BaseNode,
    context: Context,
    name: str,                    # required positional argument
    count: int = 1,              # optional positional argument
    *,                           # keyword-only arguments marker
    msg: str,                    # required keyword argument
    mode: str = "default",       # optional keyword argument
) -> str:
    return f"{msg}, {name}!" * count
```

This allows the tag to be used like:

```django
{# All parameters #}
{% greet "John" count=2 msg="Hello" mode="custom" %}

{# Only required parameters #}
{% greet "John" msg="Hello" %}

{# Missing required parameter - will raise error #}
{% greet "John" %}  {# Error: missing 'msg' #}
```

When you pass input to a template tag, it behaves the same way as if you passed the input to a function:

- If required parameters are missing, an error is raised
- If unexpected parameters are passed, an error is raised

To accept keys that are not valid Python identifiers (e.g. `data-id`), or would conflict with Python keywords (e.g. `is`), you can use the `**kwargs` syntax:

```python
@template_tag(library, tag="greet")
def greet(
    node: BaseNode,
    context: Context,
    **kwargs,
) -> str:
    attrs = kwargs.copy()
    is_var = attrs.pop("is", None)
    attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())

    return mark_safe(f"""
        <div {attrs_str}>
            Hello, {is_var}!
        </div>
    """)
```

This allows you to use the tag like this:

```django
{% greet is="John" data-id="123" %}
```

## Defining template tags with `BaseNode`

For more control over your template tag, you can subclass [`BaseNode`](../../../reference/api#django_components.BaseNode) directly instead of using the decorator. This gives you access to additional features like the node's internal state and parsing details.

```python
from django_components import BaseNode

class GreetNode(BaseNode):
    tag = "greet"
    end_tag = "endgreet"
    allowed_flags = ["required"]

    def render(self, context: Context, name: str, **kwargs) -> str:
        # Access node properties
        if self.flags["required"]:
            return f"Required greeting: Hello, {name}!"
        return f"Hello, {name}!"

# Register the node
GreetNode.register(library)
```

### Node properties

When using [`BaseNode`](../../../reference/api#django_components.BaseNode), you have access to several useful properties:

- [`node_id`](../../../reference/api#django_components.BaseNode.node_id): A unique identifier for this node instance
- [`flags`](../../../reference/api#django_components.BaseNode.flags): Dictionary of flag values (e.g. `{"required": True}`)
- [`params`](../../../reference/api#django_components.BaseNode.params): List of raw parameters passed to the tag
- [`nodelist`](../../../reference/api#django_components.BaseNode.nodelist): The template nodes between the start and end tags
- [`contents`](../../../reference/api#django_components.BaseNode.contents): The raw contents between the start and end tags
- [`active_flags`](../../../reference/api#django_components.BaseNode.active_flags): List of flags that are currently set to True
- [`template_name`](../../../reference/api#django_components.BaseNode.template_name): The name of the `Template` instance inside which the node was defined
- [`template_component`](../../../reference/api#django_components.BaseNode.template_component): The component class that the `Template` belongs to

This is what the `node` parameter in the [`@template_tag`](../../../reference/api#django_components.template_tag) decorator gives you access to - it's the instance of the node class that was automatically created for your template tag.

### Rendering content between tags

When your tag has an end tag, you can access and render the content between the tags using `nodelist`:

```python
class WrapNode(BaseNode):
    tag = "wrap"
    end_tag = "endwrap"

    def render(self, context: Context, tag: str = "div", **attrs) -> str:
        # Render the content between tags
        inner = self.nodelist.render(context)
        attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f"<{tag} {attrs_str}>{inner}</{tag}>"

# Usage:
{% wrap tag="section" class="content" %}
    Hello, world!
{% endwrap %}
```

### Unregistering nodes

You can unregister a node from a library using the `unregister` method:

```python
GreetNode.unregister(library)
```

This is particularly useful in testing when you want to clean up after registering temporary tags.
