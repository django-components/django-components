from typing import NamedTuple, Optional, cast

from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError

from django_components import Component, OnRenderGenerator, SlotInput, types


class ErrorFallback(Component):
    """
    A component that catches errors and displays fallback content, similar to React's ErrorBoundary.

    See React's [`ErrorBoundary`](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
    component.

    **Parameters**:

    - **fallback** (str, optional): A string to display when an error occurs. Cannot be used together with the `fallback` slot.

    **Slots**:

    - **content** or **default**: The main content that might raise an error.
    - **fallback**: Custom fallback content to display when an error occurs. When using the `fallback` slot, you can access the `error` object through slot data (`{% fill "fallback" data="data" %}`). Cannot be used together with the `fallback` kwarg.

    **Example:**

    Given this template:

    ```django
    {% component "error_fallback" fallback="Oops, something went wrong" %}
        {% component "table" / %}
    {% endcomponent %}
    ```

    Then:

    - If the `table` component does NOT raise an error, then the table is rendered as normal.
    - If the `table` component DOES raise an error, then `error_fallback` renders `Oops, something went wrong`.

    To have more control over the fallback content, you can use the `fallback` slot
    instead of the `fallback` kwarg.

    ```django
    {% component "error_fallback" %}
        {% fill "content" %}
            {% component "table" / %}
        {% endfill %}
        {% fill "fallback" %}
            <p>Oops, something went wrong</p>
            {% button href="/report-error" %}
                Report error
            {% endbutton %}
        {% endfill %}
    {% endcomponent %}
    ```

    If you want to print the error, you can access the `error` variable
    as [slot data](../../concepts/fundamentals/slots/#slot-data).

    ```django
    {% component "error_fallback" %}
        {% fill "content" %}
            {% component "table" / %}
        {% endfill %}
        {% fill "fallback" data="data" %}
            Oops, something went wrong:
            <pre>{{ data.error }}</pre>
        {% endfill %}
    {% endcomponent %}
    ```

    **Python:**

    With fallback kwarg:

    ```py
    from django_components import ErrorFallback

    ErrorFallback.render(
        slots={
            # Main content
            "content": lambda ctx: TableComponent.render(
                deps_strategy="ignore",
            ),
        },
        kwargs={
            # Fallback content
            "fallback": "Oops, something went wrong",
        },
    )
    ```

    With fallback slot:

    ```py
    from django_components import ErrorFallback

    ErrorFallback.render(
        slots={
            # Main content
            "content": lambda ctx: TableComponent.render(
                deps_strategy="ignore",
            ),
            # Fallback content
            "fallback": lambda ctx: mark_safe("Oops, something went wrong: " + ctx.error),
        },
    )
    ```

    !!! info

        Remember to define the `content` slot as function, so it's evaluated from inside of `ErrorFallback`.
    """

    class Kwargs(NamedTuple):
        fallback: Optional[str] = None

    class Slots(NamedTuple):
        default: Optional[SlotInput] = None
        content: Optional[SlotInput] = None
        fallback: Optional[SlotInput] = None

    def on_render(
        self,
        context: Context,
        template: Optional[Template],
    ) -> OnRenderGenerator:
        if template is None:
            raise TemplateSyntaxError("The 'error_fallback' component must have a template.")

        fallback_kwarg = cast("ErrorFallback.Kwargs", self.kwargs).fallback
        fallback_slot = cast("ErrorFallback.Slots", self.slots).fallback

        if fallback_kwarg is not None and fallback_slot is not None:
            raise TemplateSyntaxError(
                "The 'fallback' argument and slot cannot both be provided. Please provide only one.",
            )

        result, error = yield lambda: template.render(context)

        # No error, return the result
        if error is None:
            return result

        # Error, return the fallback
        if fallback_kwarg is not None:
            return fallback_kwarg
        elif fallback_slot is not None:
            # Render the template second time, this time with the error
            # So that we render the fallback slot with proper access to the outer context and whatnot.
            with context.push({"error": error}):
                return template.render(context)
        else:
            return ""

    # TODO - Once we don't have to pass Context to the slot, we can remove the template
    #        and render the slots directly.
    template: types.django_html = """
        {% load component_tags %}
        {% if not error %}
            {% slot "content" default / %}
        {% else %}
            {% slot "fallback" error=error / %}
        {% endif %}
    """
