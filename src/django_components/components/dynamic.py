import inspect
from typing import Any, Optional, Type, Union, cast

from django.template import Context, Template

from django_components import Component, ComponentRegistry, NotRegistered
from django_components.component_registry import ALL_REGISTRIES


class DynamicComponent(Component):
    """
    This component is given a registered name or a reference to another component,
    and behaves as if the other component was in its place.

    The args, kwargs, and slot fills are all passed down to the underlying component.

    Args:
        is (str | Type[Component]): Component that should be rendered. Either a registered name of a component,
            or a [Component](./api.md#django_components.Component) class directly. Required.
        registry (ComponentRegistry, optional): Specify the [registry](./api.md#django_components.ComponentRegistry)\
            to search for the registered name. If omitted, all registries are searched until the first match.
        *args: Additional data passed to the component.
        **kwargs: Additional data passed to the component.

    **Slots:**

    * Any slots, depending on the actual component.

    **Examples:**

    Django
    ```django
    {% component "dynamic" is=table_comp data=table_data headers=table_headers %}
        {% fill "pagination" %}
            {% component "pagination" / %}
        {% endfill %}
    {% endcomponent %}
    ```

    Or in case you use the `django_components.component_shorthand_formatter` tag formatter:

    ```django
    {% dynamic is=table_comp data=table_data headers=table_headers %}
        {% fill "pagination" %}
            {% component "pagination" / %}
        {% endfill %}
    {% enddynamic %}
    ```

    Python
    ```py
    from django_components import DynamicComponent

    DynamicComponent.render(
        kwargs={
            "is": table_comp,
            "data": table_data,
            "headers": table_headers,
        },
        slots={
            "pagination": PaginationComponent.render(
                deps_strategy="ignore",
            ),
        },
    )
    ```

    ## Use cases

    Dynamic components are suitable if you are writing something like a form component. You may design
    it such that users give you a list of input types, and you render components depending on the input types.

    While you could handle this with a series of if / else statements, that's not an extensible approach.
    Instead, you can use the dynamic component in place of normal components.

    ## Component name

    By default, the dynamic component is registered under the name `"dynamic"`. In case of a conflict,
    you can set the
    [`COMPONENTS.dynamic_component_name`](./settings.md#django_components.app_settings.ComponentsSettings.dynamic_component_name)
    setting to change the name used for the dynamic components.

    ```py
    # settings.py
    COMPONENTS = ComponentsSettings(
        dynamic_component_name="my_dynamic",
    )
    ```

    After which you will be able to use the dynamic component with the new name:
    ```django
    {% component "my_dynamic" is=table_comp data=table_data headers=table_headers %}
        {% fill "pagination" %}
            {% component "pagination" / %}
        {% endfill %}
    {% endcomponent %}
    ```
    """

    _is_dynamic_component = True

    # NOTE: The inner component is rendered in `on_render`, so that the `Context` object
    # is already configured as if the inner component was rendered inside the template.
    # E.g. the `_COMPONENT_CONTEXT_KEY` is set, which means that the child component
    # will know that it's a child of this component.
    def on_render(
        self,
        context: Context,
        template: Optional[Template],
    ) -> str:
        # Make a copy of kwargs so we pass to the child only the kwargs that are
        # actually used by the child component.
        cleared_kwargs = self.raw_kwargs.copy()

        registry: Optional[ComponentRegistry] = cleared_kwargs.pop("registry", None)
        comp_name_or_class: Union[str, Type[Component]] = cleared_kwargs.pop("is", None)
        if not comp_name_or_class:
            raise TypeError(f"Component '{self.name}' is missing a required argument 'is'")

        # Resolve the component class
        comp_class = self._resolve_component(comp_name_or_class, registry)

        output = comp_class.render(
            context=self.context,
            args=self.raw_args,
            kwargs=cleared_kwargs,
            slots=self.raw_slots,
            deps_strategy=self.deps_strategy,
            registered_name=self.registered_name,
            outer_context=self.outer_context,
            registry=self.registry,
        )
        return output

    def _resolve_component(
        self,
        comp_name_or_class: Union[str, Type[Component], Any],
        registry: Optional[ComponentRegistry] = None,
    ) -> Type[Component]:
        component_cls: Optional[Type[Component]] = None

        if not isinstance(comp_name_or_class, str):
            # NOTE: When Django template is resolving the variable that refers to the
            # component class, it may see that it's callable and evaluate it. Hence, we need
            # get check if we've got class or instance.
            if inspect.isclass(comp_name_or_class):
                component_cls = comp_name_or_class
            else:
                component_cls = cast(Type[Component], comp_name_or_class.__class__)

        else:
            if registry:
                component_cls = registry.get(comp_name_or_class)
            else:
                # Search all registries for the first match
                for reg_ref in ALL_REGISTRIES:
                    reg = reg_ref()
                    if not reg:
                        continue

                    try:
                        component_cls = reg.get(comp_name_or_class)
                        break
                    except NotRegistered:
                        continue

        # Raise if none found
        if not component_cls:
            raise NotRegistered(f"The component '{comp_name_or_class}' was not found")

        return component_cls
