from typing import Any, Dict, NamedTuple, Optional

from django.template import Context, TemplateSyntaxError
from django.utils.safestring import SafeString

from django_components.context import _INJECT_CONTEXT_KEY_PREFIX
from django_components.node import BaseNode
from django_components.perfutil.provide import managed_provide_cache, provide_cache
from django_components.util.misc import gen_id


class ProvideNode(BaseNode):
    """
    The [`{% provide %}`](../template_tags#provide) tag is part of the "provider" part of
    the [provide / inject feature](../../concepts/advanced/provide_inject).

    Pass kwargs to this tag to define the provider's data.

    Any components defined within the `{% provide %}..{% endprovide %}` tags will be able to access this data
    with [`Component.inject()`](../api#django_components.Component.inject).

    This is similar to React's [`ContextProvider`](https://react.dev/learn/passing-data-deeply-with-context),
    or Vue's [`provide()`](https://vuejs.org/guide/components/provide-inject).

    **Args:**

    - `name` (str, required): Provider name. This is the name you will then use in
        [`Component.inject()`](../api#django_components.Component.inject).
    - `**kwargs`: Any extra kwargs will be passed as the provided data.

    **Example:**

    Provide the "user_data" in parent component:

    ```djc_py
    @register("parent")
    class Parent(Component):
        template = \"\"\"
          <div>
            {% provide "user_data" user=user %}
              {% component "child" / %}
            {% endprovide %}
          </div>
        \"\"\"

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "user": kwargs["user"],
            }
    ```

    Since the "child" component is used within the `{% provide %} / {% endprovide %}` tags,
    we can request the "user_data" using `Component.inject("user_data")`:

    ```djc_py
    @register("child")
    class Child(Component):
        template = \"\"\"
          <div>
            User is: {{ user }}
          </div>
        \"\"\"

        def get_template_data(self, args, kwargs, slots, context):
            user = self.inject("user_data").user
            return {
                "user": user,
            }
    ```

    Notice that the keys defined on the [`{% provide %}`](../template_tags#provide) tag are then accessed as attributes
    when accessing them with [`Component.inject()`](../api#django_components.Component.inject).

    ✅ Do this
    ```python
    user = self.inject("user_data").user
    ```

    ❌ Don't do this
    ```python
    user = self.inject("user_data")["user"]
    ```
    """

    tag = "provide"
    end_tag = "endprovide"
    allowed_flags = ()

    def render(self, context: Context, name: str, **kwargs: Any) -> SafeString:
        # NOTE: The "provided" kwargs are meant to be shared privately, meaning that components
        # have to explicitly opt in by using the `Component.inject()` method. That's why we don't
        # add the provided kwargs into the Context.
        with context.update({}):
            # "Provide" the data to child nodes
            provide_id = set_provided_context_var(context, name, kwargs)

            # `managed_provide_cache` will remove the cache entry at the end if no components reference it.
            with managed_provide_cache(provide_id):
                output = self.nodelist.render(context)

        return output


def get_injected_context_var(
    component_name: str,
    context: Context,
    key: str,
    default: Optional[Any] = None,
) -> Any:
    """
    Retrieve a 'provided' field. The field MUST have been previously 'provided'
    by the component's ancestors using the `{% provide %}` template tag.
    """
    # NOTE: For simplicity, we keep the provided values directly on the context.
    # This plays nicely with Django's Context, which behaves like a stack, so "newer"
    # values overshadow the "older" ones.
    internal_key = _INJECT_CONTEXT_KEY_PREFIX + key

    # Return provided value if found
    if internal_key in context:
        cache_key = context[internal_key]
        return provide_cache[cache_key]

    # If a default was given, return that
    if default is not None:
        return default

    # Otherwise raise error
    raise KeyError(
        f"Component '{component_name}' tried to inject a variable '{key}' before it was provided."
        f" To fix this, make sure that at least one ancestor of component '{component_name}' has"
        f" the variable '{key}' in their 'provide' attribute.",
    )


def set_provided_context_var(
    context: Context,
    key: str,
    provided_kwargs: Dict[str, Any],
) -> str:
    """
    'Provide' given data under given key. In other words, this data can be retrieved
    using `self.inject(key)` inside of `get_template_data()` method of components that
    are nested inside the `{% provide %}` tag.
    """
    # NOTE: We raise TemplateSyntaxError since this func should be called only from
    # within template.
    if not key:
        raise TemplateSyntaxError(
            "Provide tag received an empty string. Key must be non-empty and a valid identifier.",
        )
    if not key.isidentifier():
        raise TemplateSyntaxError(
            "Provide tag received a non-identifier string. Key must be non-empty and a valid identifier.",
        )

    # We turn the kwargs into a NamedTuple so that the object that's "provided"
    # is immutable. This ensures that the data returned from `inject` will always
    # have all the keys that were passed to the `provide` tag.
    tuple_cls = NamedTuple("DepInject", provided_kwargs.keys())  # type: ignore[misc]
    payload = tuple_cls(**provided_kwargs)

    # Instead of storing the provided data on the Context object, we store it
    # in a separate dictionary, and we set only the key to the data on the Context.
    context_key = _INJECT_CONTEXT_KEY_PREFIX + key
    provide_id = gen_id()
    context[context_key] = provide_id
    provide_cache[provide_id] = payload

    return provide_id
