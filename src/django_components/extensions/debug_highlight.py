from typing import Any, Literal, NamedTuple, Optional, Type

from django_components.app_settings import app_settings
from django_components.extension import (
    ComponentExtension,
    ExtensionComponentConfig,
    OnComponentRenderedContext,
    OnSlotRenderedContext,
)
from django_components.util.misc import gen_id


class HighlightColor(NamedTuple):
    text_color: str
    border_color: str


COLORS = {
    "component": HighlightColor(text_color="#2f14bb", border_color="blue"),
    "slot": HighlightColor(text_color="#bb1414", border_color="#e40c0c"),
}


def apply_component_highlight(highlight_type: Literal["component", "slot"], output: str, name: str) -> str:
    """
    Wrap HTML (string) in a div with a border and a highlight color.

    This is part of the component / slot highlighting feature. User can toggle on
    to see the component / slot boundaries.
    """
    color = COLORS[highlight_type]

    # Because the component / slot name is set via styling as a `::before` pseudo-element,
    # we need to generate a unique ID for each component / slot to avoid conflicts.
    highlight_id = gen_id()

    output = f"""
        <style>
        .{type}-highlight-{highlight_id}::before {{
            content: "{name}: ";
            font-weight: bold;
            color: {color.text_color};
        }}
        </style>
        <div class="{type}-highlight-{highlight_id}" style="border: 1px solid {color.border_color}">
            {output}
        </div>
    """

    return output


class HighlightComponentsDescriptor:
    def __get__(self, obj: Optional[Any], objtype: Type) -> bool:
        return app_settings.DEBUG_HIGHLIGHT_COMPONENTS


class HighlightSlotsDescriptor:
    def __get__(self, obj: Optional[Any], objtype: Type) -> bool:
        return app_settings.DEBUG_HIGHLIGHT_SLOTS


class ComponentDebugHighlight(ExtensionComponentConfig):
    """
    The interface for `Component.DebugHighlight`.

    The fields of this class are used to configure the component debug highlighting for this component
    and its direct slots.

    Read more about [Component debug highlighting](../../guides/other/troubleshooting#component-and-slot-highlighting).

    **Example:**

    ```python
    from django_components import Component

    class MyComponent(Component):
        class DebugHighlight:
            highlight_components = True
            highlight_slots = True
    ```

    To highlight ALL components and slots, set
    [extension defaults](../../reference/settings/#django_components.app_settings.ComponentsSettings.extensions_defaults)
    in your settings:

    ```python
    from django_components import ComponentsSettings

    COMPONENTS = ComponentsSettings(
        extensions_defaults={
            "debug_highlight": {
                "highlight_components": True,
                "highlight_slots": True,
            },
        },
    )
    ```
    """  # noqa: E501

    # TODO_v1 - Remove `DEBUG_HIGHLIGHT_COMPONENTS` and `DEBUG_HIGHLIGHT_SLOTS`
    #           Instead set this as plain boolean fields.
    highlight_components = HighlightComponentsDescriptor()
    """Whether to highlight this component in the rendered output."""
    highlight_slots = HighlightSlotsDescriptor()
    """Whether to highlight slots of this component in the rendered output."""


# TODO_v1 - Move into standalone extension (own repo?) and ask people to manually add this extension in settings.
class DebugHighlightExtension(ComponentExtension):
    """
    This extension adds the ability to highlight components and slots in the rendered output.

    To highlight slots, set `ComponentsSettings.DEBUG_HIGHLIGHT_SLOTS` to `True` in your settings.

    To highlight components, set `ComponentsSettings.DEBUG_HIGHLIGHT_COMPONENTS` to `True`.

    Highlighting is done by wrapping the content in a `<div>` with a border and a highlight color.

    This extension is automatically added to all components.
    """

    name = "debug_highlight"
    ComponentConfig = ComponentDebugHighlight

    # Apply highlight to the slot's rendered output
    def on_slot_rendered(self, ctx: OnSlotRenderedContext) -> Optional[str]:
        debug_cls: Optional[ComponentDebugHighlight] = getattr(ctx.component_cls, "DebugHighlight", None)
        if not debug_cls or not debug_cls.highlight_slots:
            return None

        return apply_component_highlight("slot", ctx.result, f"{ctx.component_cls.__name__} - {ctx.slot_name}")

    # Apply highlight to the rendered component
    def on_component_rendered(self, ctx: OnComponentRenderedContext) -> Optional[str]:
        debug_cls: Optional[ComponentDebugHighlight] = getattr(ctx.component_cls, "DebugHighlight", None)
        if not debug_cls or not debug_cls.highlight_components or ctx.result is None:
            return None

        return apply_component_highlight("component", ctx.result, f"{ctx.component.name} ({ctx.component_id})")
