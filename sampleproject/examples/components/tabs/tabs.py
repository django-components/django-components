"""
Alpine-based tab components: Tablist and Tab.

Based on https://github.com/django-components/django-components/discussions/540
"""

from typing import List, NamedTuple, Optional

from django.utils.safestring import mark_safe
from django.utils.text import slugify

from django_components import Component, register
from django_components import types as t


class TabDatum(NamedTuple):
    """Datum for an individual tab."""

    tab_id: str
    tabpanel_id: str
    header: str
    content: str
    disabled: bool = False


class TabContext(NamedTuple):
    id: str
    tab_data: List[TabDatum]
    enabled: bool


@register("_tabset")
class _TablistImpl(Component):
    """
    Delegated Tablist component.

    Refer to `Tablist` API below.
    """

    template_file = "tabs.html"
    css_file = "tabs.css"

    class Media:
        js = (
            # `mark_safe` is used so the script tag is usd as is, so we can add `defer` flag.
            # `defer` is used so that AlpineJS is actually loaded only after all plugins are registered
            mark_safe(
                '<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>'
            ),
        )

    class Kwargs(NamedTuple):
        tab_data: List[TabDatum]
        id: Optional[str] = None
        name: Optional[str] = None
        selected_tab: Optional[str] = None
        container_attrs: Optional[dict] = None
        tablist_attrs: Optional[dict] = None
        tab_attrs: Optional[dict] = None
        tabpanel_attrs: Optional[dict] = None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        selected_tab = (
            kwargs.selected_tab
            if kwargs.selected_tab is not None
            else kwargs.tab_data[0].tab_id
        )
        tab_data = [
            (tab, tab.tab_id != selected_tab)  # (tab, is_hidden)
            for tab in kwargs.tab_data
        ]

        return {
            "id": kwargs.id,
            "name": kwargs.name,
            "container_attrs": kwargs.container_attrs,
            "tablist_attrs": kwargs.tablist_attrs,
            "tab_attrs": kwargs.tab_attrs,
            "tabpanel_attrs": kwargs.tabpanel_attrs,
            "tab_data": tab_data,
            "selected_tab": selected_tab,
        }


@register("Tablist")
class Tablist(Component):
    """
    Tablist role component comprised of nested tab components.

    After the input is processed, this component delegates to an internal implementation
    component that renders the content.

    `name` identifies the tablist and is used as a WAI-ARIA label

    `id`, by default, is a sligified `name`, we could be used to preselect a tab based
    on query parameters (TODO)

    Example:
    ```
    {% component "Tablist" id="my-tablist" name="My Tabs" %}
        {% component Tab header="Tab 1" %}
            This is the content of Tab 1
        {% endcomponent %}
        {% component Tab header="Tab 2" disabled=True %}
            This is the content of Tab 2
        {% endcomponent %}
    {% endcomponent %}
    ```

    """

    template: t.django_html = """
        {% load component_tags %}
        {% provide "_tab" ...tab_context %}
            {% slot "content" default / %}
        {% endprovide %}
    """

    class Kwargs(NamedTuple):
        id: Optional[str] = None
        name: str = "Tabs"
        selected_tab: Optional[str] = None
        container_attrs: Optional[dict] = None
        tablist_attrs: Optional[dict] = None
        tab_attrs: Optional[dict] = None
        tabpanel_attrs: Optional[dict] = None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        self.tablist_id: str = kwargs.id or slugify(kwargs.name)
        self.tab_data: List[TabDatum] = []

        tab_context = TabContext(
            id=self.tablist_id,
            tab_data=self.tab_data,
            enabled=True,
        )

        return {
            "tab_context": tab_context._asdict(),
        }

    def on_render_after(self, context, template, result, error) -> Optional[str]:
        """
        Render the tab set.

        By the time we get here, all child Tab components should have been rendered,
        and they should've populated the tablist.
        """
        if error or result is None:
            return None

        kwargs: Tablist.Kwargs = self.kwargs

        # Render the TablistImpl component in place of Tablist.
        return _TablistImpl.render(
            kwargs=_TablistImpl.Kwargs(
                # Access variables we've defined in get_template_data
                id=self.tablist_id,
                tab_data=self.tab_data,
                name=kwargs.name,
                selected_tab=kwargs.selected_tab,
                container_attrs=kwargs.container_attrs,
                tablist_attrs=kwargs.tablist_attrs,
                tab_attrs=kwargs.tab_attrs,
                tabpanel_attrs=kwargs.tabpanel_attrs,
            ),
            deps_strategy="ignore",
        )


@register("Tab")
class Tab(Component):
    """
    Individual tab, inside the default slot of the `Tablist` component.

    Example:
    ```
    {% component "Tablist" id="my-tablist" name="My Tabs" %}
        {% component Tab header="Tab 1" %}
            This is the content of Tab 1
        {% endcomponent %}
        {% component Tab header="Tab 2" disabled=True %}
            This is the content of Tab 2
        {% endcomponent %}
    {% endcomponent %}
    ```

    """

    template: t.django_html = """
        {% load component_tags %}
        {% provide "_tab" ...overriding_tab_context %}
            {% slot "content" default / %}
        {% endprovide %}
    """

    class Kwargs(NamedTuple):
        header: str
        disabled: bool = False
        id: Optional[str] = None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        """
        Access the tab data registered for the parent Tablist component.

        This raises if we're not nested inside a Tablist component.
        """
        tab_ctx: TabContext = self.inject("_tab")

        # We accessed the _tab context, but we're inside ANOTHER Tab
        if not tab_ctx.enabled:
            raise RuntimeError(
                f"Component '{self.name}' was called with no parent Tablist component. "
                f"Either wrap '{self.name}' in Tablist component, or check if the "
                f"component is not a descendant of another instance of '{self.name}'"
            )

        if kwargs.id:
            slug = kwargs.id
        else:
            group_slug = slugify(tab_ctx.id)
            tab_slug = slugify(kwargs.header)
            slug = f"{group_slug}_{tab_slug}"

        self.tab_id = f"{slug}_tab"
        self.tabpanel_id = f"{slug}_content"
        self.parent_tabs: List[TabDatum] = tab_ctx.tab_data

        # Prevent Tab's children from accessing the parent Tablist context.
        # If we didn't do this, then you could place a Tab inside another Tab,
        # ```
        # {% component Tablist %}
        #     {% component Tab header="Tab 1" %}
        #         {% component Tab header="Tab 2" %}
        #             This is the content of Tab 2
        #         {% endcomponent %}
        #     {% endcomponent %}
        # {% endcomponent %}
        # ```
        overriding_tab_context = TabContext(
            id=self.tab_id,
            tab_data=[],
            enabled=False,
        )

        return {
            "overriding_tab_context": overriding_tab_context._asdict(),
        }

    # This runs when the Tab component is rendered and the content is returned.
    # We add the TabDatum to the parent Tablist component.
    def on_render_after(self, context, template, result, error) -> None:
        if error or result is None:
            return

        kwargs: Tab.Kwargs = self.kwargs

        self.parent_tabs.append(
            TabDatum(
                tab_id=self.tab_id,
                tabpanel_id=self.tabpanel_id,
                header=kwargs.header,
                disabled=kwargs.disabled,
                content=mark_safe(result.strip()),
            ),
        )
