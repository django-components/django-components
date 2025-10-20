from django_components.dependencies import cache_component_css, cache_component_js
from django_components.extension import (
    ComponentExtension,
    OnComponentClassCreatedContext,
)


class DependenciesExtension(ComponentExtension):
    """
    This extension adds a nested `Dependencies` class to each `Component`.

    This extension is automatically added to all components.
    """

    name = "dependencies"

    # Cache the component's JS and CSS scripts when the class is created, so that
    # components' JS/CSS files are accessible even before having to render the component first.
    #
    # This is important for the scenario when the web server may restart in a middle of user
    # session. In which case, if we did not cache the JS/CSS, then user may fail to retrieve
    # JS/CSS of some component.
    #
    # Component JS/CSS is then also cached after each time a component is rendered.
    # That way, if the component JS/CSS cache is smaller than the total number of
    # components/assets, we add back the most-recent entries.
    def on_component_class_created(self, ctx: OnComponentClassCreatedContext) -> None:
        cache_component_js(ctx.component_cls, force=True)
        cache_component_css(ctx.component_cls, force=True)
