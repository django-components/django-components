import re
from dataclasses import dataclass
from enum import Enum
from importlib import import_module
from os import PathLike
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from django.conf import settings

from django_components.util.misc import default

if TYPE_CHECKING:
    from django_components.extension import ComponentExtension
    from django_components.tag_formatter import TagFormatterABC


T = TypeVar("T")


ContextBehaviorType = Literal["django", "isolated"]


class ContextBehavior(str, Enum):
    """
    Configure how (and whether) the context is passed to the component fills
    and what variables are available inside the [`{% fill %}`](../template_tags#fill) tags.

    Also see [Component context and scope](../../concepts/fundamentals/component_context_scope#context-behavior).

    **Options:**

    - `django`: With this setting, component fills behave as usual Django tags.
    - `isolated`: This setting makes the component fills behave similar to Vue or React.
    """

    DJANGO = "django"
    """
    With this setting, component fills behave as usual Django tags.
    That is, they enrich the context, and pass it along.

    1. Component fills use the context of the component they are within.
    2. Variables from [`Component.get_template_data()`](../api#django_components.Component.get_template_data)
    are available to the component fill.

    **Example:**

    Given this template
    ```django
    {% with cheese="feta" %}
      {% component 'my_comp' %}
        {{ my_var }}  # my_var
        {{ cheese }}  # cheese
      {% endcomponent %}
    {% endwith %}
    ```

    and this context returned from the `Component.get_template_data()` method
    ```python
    { "my_var": 123 }
    ```

    Then if component "my_comp" defines context
    ```python
    { "my_var": 456 }
    ```

    Then this will render:
    ```django
    456   # my_var
    feta  # cheese
    ```

    Because "my_comp" overrides the variable "my_var",
    so `{{ my_var }}` equals `456`.

    And variable "cheese" will equal `feta`, because the fill CAN access
    the current context.
    """

    ISOLATED = "isolated"
    """
    This setting makes the component fills behave similar to Vue or React, where
    the fills use EXCLUSIVELY the context variables defined in
    [`Component.get_template_data()`](../api#django_components.Component.get_template_data).

    **Example:**

    Given this template
    ```django
    {% with cheese="feta" %}
      {% component 'my_comp' %}
        {{ my_var }}  # my_var
        {{ cheese }}  # cheese
      {% endcomponent %}
    {% endwith %}
    ```

    and this context returned from the `get_template_data()` method
    ```python
    { "my_var": 123 }
    ```

    Then if component "my_comp" defines context
    ```python
    { "my_var": 456 }
    ```

    Then this will render:
    ```django
    123   # my_var
          # cheese
    ```

    Because both variables "my_var" and "cheese" are taken from the root context.
    Since "cheese" is not defined in root context, it's empty.
    """


# This is the source of truth for the settings that are available. If the documentation
# or the defaults do NOT match this, they should be updated.
class ComponentsSettings(NamedTuple):
    """
    Settings available for django_components.

    **Example:**

    ```python
    COMPONENTS = ComponentsSettings(
        autodiscover=False,
        dirs = [BASE_DIR / "components"],
    )
    ```
    """

    extensions: Optional[Sequence[Union[Type["ComponentExtension"], str]]] = None
    """
    List of [extensions](../../concepts/advanced/extensions) to be loaded.

    The extensions can be specified as:

    - Python import path, e.g. `"path.to.my_extension.MyExtension"`.
    - Extension class, e.g. `my_extension.MyExtension`.

    Read more about [extensions](../../concepts/advanced/extensions).

    **Example:**

    ```python
    COMPONENTS = ComponentsSettings(
        extensions=[
            "path.to.my_extension.MyExtension",
            StorybookExtension,
        ],
    )
    ```
    """

    extensions_defaults: Optional[Dict[str, Any]] = None
    """
    Global defaults for the extension classes.

    Read more about [Extension defaults](../../concepts/advanced/extensions#extension-defaults).

    **Example:**

    ```python
    COMPONENTS = ComponentsSettings(
        extensions_defaults={
            "my_extension": {
                "my_setting": "my_value",
            },
            "cache": {
                "enabled": True,
                "ttl": 60,
            },
        },
    )
    ```
    """

    autodiscover: Optional[bool] = None
    """
    Toggle whether to run [autodiscovery](../../concepts/fundamentals/autodiscovery) at the Django server startup.

    Defaults to `True`

    ```python
    COMPONENTS = ComponentsSettings(
        autodiscover=False,
    )
    ```
    """

    dirs: Optional[Sequence[Union[str, PathLike, Tuple[str, str], Tuple[str, PathLike]]]] = None
    """
    Specify the directories that contain your components.

    Defaults to `[Path(settings.BASE_DIR) / "components"]`. That is, the root `components/` app.

    Directories must be full paths, same as with
    [STATICFILES_DIRS](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STATICFILES_DIRS).

    These locations are searched during [autodiscovery](../../concepts/fundamentals/autodiscovery),
    or when you [define HTML, JS, or CSS as separate files](../../concepts/fundamentals/defining_js_css_html_files).

    ```python
    COMPONENTS = ComponentsSettings(
        dirs=[BASE_DIR / "components"],
    )
    ```

    Set to empty list to disable global components directories:

    ```python
    COMPONENTS = ComponentsSettings(
        dirs=[],
    )
    ```
    """

    app_dirs: Optional[Sequence[str]] = None
    """
    Specify the app-level directories that contain your components.

    Defaults to `["components"]`. That is, for each Django app, we search `<app>/components/` for components.

    The paths must be relative to app, e.g.:

    ```python
    COMPONENTS = ComponentsSettings(
        app_dirs=["my_comps"],
    )
    ```

    To search for `<app>/my_comps/`.

    These locations are searched during [autodiscovery](../../concepts/fundamentals/autodiscovery),
    or when you [define HTML, JS, or CSS as separate files](../../concepts/fundamentals/defining_js_css_html_files).

    Set to empty list to disable app-level components:

    ```python
    COMPONENTS = ComponentsSettings(
        app_dirs=[],
    )
    ```
    """

    cache: Optional[str] = None
    """
    Name of the [Django cache](https://docs.djangoproject.com/en/5.2/topics/cache/)
    to be used for storing component's JS and CSS files.

    If `None`, a [`LocMemCache`](https://docs.djangoproject.com/en/5.2/topics/cache/#local-memory-caching)
    is used with default settings.

    Defaults to `None`.

    Read more about [caching](../../guides/setup/caching).

    ```python
    COMPONENTS = ComponentsSettings(
        cache="my_cache",
    )
    ```
    """

    context_behavior: Optional[ContextBehaviorType] = None
    """
    Configure whether, inside a component template, you can use variables from the outside
    ([`"django"`](../api#django_components.ContextBehavior.DJANGO))
    or not ([`"isolated"`](../api#django_components.ContextBehavior.ISOLATED)).
    This also affects what variables are available inside the [`{% fill %}`](../template_tags#fill)
    tags.

    Also see [Component context and scope](../../concepts/fundamentals/component_context_scope#context-behavior).

    Defaults to `"django"`.

    ```python
    COMPONENTS = ComponentsSettings(
        context_behavior="isolated",
    )
    ```

    > NOTE: `context_behavior` and `slot_context_behavior` options were merged in v0.70.
    >
    > If you are migrating from BEFORE v0.67, set `context_behavior` to `"django"`.
    > From v0.67 to v0.78 (incl) the default value was `"isolated"`.
    >
    > For v0.79 and later, the default is again `"django"`. See the rationale for change
    > [here](https://github.com/django-components/django-components/issues/498).
    """

    # TODO_v1 - remove. Users should use extension defaults instead.
    debug_highlight_components: Optional[bool] = None
    """
    DEPRECATED. Use
    [`extensions_defaults`](../settings/#django_components.app_settings.ComponentsSettings.extensions_defaults)
    instead. Will be removed in v1.

    Enable / disable component highlighting.
    See [Troubleshooting](../../guides/other/troubleshooting#component-highlighting) for more details.

    Defaults to `False`.

    ```python
    COMPONENTS = ComponentsSettings(
        debug_highlight_components=True,
    )
    ```
    """

    # TODO_v1 - remove. Users should use extension defaults instead.
    debug_highlight_slots: Optional[bool] = None
    """
    DEPRECATED. Use
    [`extensions_defaults`](../settings/#django_components.app_settings.ComponentsSettings.extensions_defaults)
    instead. Will be removed in v1.

    Enable / disable slot highlighting.
    See [Troubleshooting](../../guides/other/troubleshooting#slot-highlighting) for more details.

    Defaults to `False`.

    ```python
    COMPONENTS = ComponentsSettings(
        debug_highlight_slots=True,
    )
    ```
    """

    dynamic_component_name: Optional[str] = None
    """
    By default, the [dynamic component](../components#django_components.components.dynamic.DynamicComponent)
    is registered under the name `"dynamic"`.

    In case of a conflict, you can use this setting to change the component name used for
    the dynamic components.

    ```python
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

    libraries: Optional[List[str]] = None
    """
    Configure extra python modules that should be loaded.

    This may be useful if you are not using the [autodiscovery feature](../../concepts/fundamentals/autodiscovery),
    or you need to load components from non-standard locations. Thus you can have
    a structure of components that is independent from your apps.

    Expects a list of python module paths. Defaults to empty list.

    **Example:**

    ```python
    COMPONENTS = ComponentsSettings(
        libraries=[
            "mysite.components.forms",
            "mysite.components.buttons",
            "mysite.components.cards",
        ],
    )
    ```

    This would be the equivalent of importing these modules from within Django's
    [`AppConfig.ready()`](https://docs.djangoproject.com/en/5.2/ref/applications/#django.apps.AppConfig.ready):

    ```python
    class MyAppConfig(AppConfig):
        def ready(self):
            import "mysite.components.forms"
            import "mysite.components.buttons"
            import "mysite.components.cards"
    ```

    # Manually loading libraries

    In the rare case that you need to manually trigger the import of libraries, you can use
    the [`import_libraries()`](../api/#django_components.import_libraries) function:

    ```python
    from django_components import import_libraries

    import_libraries()
    ```
    """

    multiline_tags: Optional[bool] = None
    """
    Enable / disable
    [multiline support for template tags](../../concepts/fundamentals/template_tag_syntax#multiline-tags).
    If `True`, template tags like `{% component %}` or `{{ my_var }}` can span multiple lines.

    Defaults to `True`.

    Disable this setting if you are making custom modifications to Django's
    regular expression for parsing templates at `django.template.base.tag_re`.

    ```python
    COMPONENTS = ComponentsSettings(
        multiline_tags=False,
    )
    ```
    """

    # TODO_REMOVE_IN_V1
    reload_on_template_change: Optional[bool] = None
    """Deprecated. Use
    [`COMPONENTS.reload_on_file_change`](../settings/#django_components.app_settings.ComponentsSettings.reload_on_file_change)
    instead."""  # noqa: E501

    reload_on_file_change: Optional[bool] = None
    """
    This is relevant if you are using the project structure where
    HTML, JS, CSS and Python are in separate files and nested in a directory.

    In this case you may notice that when you are running a development server,
    the server sometimes does not reload when you change component files.

    Django's native [live reload](https://stackoverflow.com/a/66023029/9788634) logic
    handles only Python files and HTML template files. It does NOT reload when other
    file types change or when template files are nested more than one level deep.

    The setting `reload_on_file_change` fixes this, reloading the dev server even when your component's
    HTML, JS, or CSS changes.

    If `True`, django_components configures Django to reload when files inside
    [`COMPONENTS.dirs`](../settings/#django_components.app_settings.ComponentsSettings.dirs)
    or
    [`COMPONENTS.app_dirs`](../settings/#django_components.app_settings.ComponentsSettings.app_dirs)
    change.

    See [Reload dev server on component file changes](../../guides/setup/development_server/#reload-dev-server-on-component-file-changes).

    Defaults to `False`.

    !!! warning

        This setting should be enabled only for the dev environment!
    """  # noqa: E501

    static_files_allowed: Optional[List[Union[str, re.Pattern]]] = None
    """
    A list of file extensions (including the leading dot) that define which files within
    [`COMPONENTS.dirs`](../settings/#django_components.app_settings.ComponentsSettings.dirs)
    or
    [`COMPONENTS.app_dirs`](../settings/#django_components.app_settings.ComponentsSettings.app_dirs)
    are treated as [static files](https://docs.djangoproject.com/en/5.2/howto/static-files/).

    If a file is matched against any of the patterns, it's considered a static file. Such files are collected
    when running [`collectstatic`](https://docs.djangoproject.com/en/5.2/ref/contrib/staticfiles/#collectstatic),
    and can be accessed under the
    [static file endpoint](https://docs.djangoproject.com/en/5.2/ref/settings/#static-url).

    You can also pass in compiled regexes ([`re.Pattern`](https://docs.python.org/3/library/re.html#re.Pattern))
    for more advanced patterns.

    By default, JS, CSS, and common image and font file formats are considered static files:

    ```python
    COMPONENTS = ComponentsSettings(
        static_files_allowed=[
            ".css",
            ".js", ".jsx", ".ts", ".tsx",
            # Images
            ".apng", ".png", ".avif", ".gif", ".jpg",
            ".jpeg",  ".jfif", ".pjpeg", ".pjp", ".svg",
            ".webp", ".bmp", ".ico", ".cur", ".tif", ".tiff",
            # Fonts
            ".eot", ".ttf", ".woff", ".otf", ".svg",
        ],
    )
    ```

    !!! warning

        Exposing your Python files can be a security vulnerability.
        See [Security notes](../../overview/security_notes).
    """

    # TODO_REMOVE_IN_V1
    forbidden_static_files: Optional[List[Union[str, re.Pattern]]] = None
    """Deprecated. Use
    [`COMPONENTS.static_files_forbidden`](../settings/#django_components.app_settings.ComponentsSettings.static_files_forbidden)
    instead."""  # noqa: E501

    static_files_forbidden: Optional[List[Union[str, re.Pattern]]] = None
    """
    A list of file extensions (including the leading dot) that define which files within
    [`COMPONENTS.dirs`](../settings/#django_components.app_settings.ComponentsSettings.dirs)
    or
    [`COMPONENTS.app_dirs`](../settings/#django_components.app_settings.ComponentsSettings.app_dirs)
    will NEVER be treated as [static files](https://docs.djangoproject.com/en/5.2/howto/static-files/).

    If a file is matched against any of the patterns, it will never be considered a static file,
    even if the file matches a pattern in
    [`static_files_allowed`](../settings/#django_components.app_settings.ComponentsSettings.static_files_allowed).

    Use this setting together with
    [`static_files_allowed`](../settings/#django_components.app_settings.ComponentsSettings.static_files_allowed)
    for a fine control over what file types will be exposed.

    You can also pass in compiled regexes ([`re.Pattern`](https://docs.python.org/3/library/re.html#re.Pattern))
    for more advanced patterns.

    By default, any HTML and Python are considered NOT static files:

    ```python
    COMPONENTS = ComponentsSettings(
        static_files_forbidden=[
            ".html", ".django", ".dj", ".tpl",
            # Python files
            ".py", ".pyc",
        ],
    )
    ```

    !!! warning

        Exposing your Python files can be a security vulnerability.
        See [Security notes](../../overview/security_notes).
    """

    tag_formatter: Optional[Union["TagFormatterABC", str]] = None
    """
    Configure what syntax is used inside Django templates to render components.
    See the [available tag formatters](../tag_formatters).

    Defaults to `"django_components.component_formatter"`.

    Learn more about [Customizing component tags with TagFormatter](../../concepts/advanced/tag_formatter).

    Can be set either as direct reference:

    ```python
    from django_components import component_formatter

    COMPONENTS = ComponentsSettings(
        "tag_formatter": component_formatter
    )
    ```

    Or as an import string;

    ```python
    COMPONENTS = ComponentsSettings(
        "tag_formatter": "django_components.component_formatter"
    )
    ```

    **Examples:**

    - `"django_components.component_formatter"`

        Set

        ```python
        COMPONENTS = ComponentsSettings(
            "tag_formatter": "django_components.component_formatter"
        )
        ```

        To write components like this:

        ```django
        {% component "button" href="..." %}
            Click me!
        {% endcomponent %}
        ```

    - `django_components.component_shorthand_formatter`

        Set

        ```python
        COMPONENTS = ComponentsSettings(
            "tag_formatter": "django_components.component_shorthand_formatter"
        )
        ```

        To write components like this:

        ```django
        {% button href="..." %}
            Click me!
        {% endbutton %}
        ```
    """

    template_cache_size: Optional[int] = None
    """
    Configure the maximum amount of Django templates to be cached.

    Defaults to `128`.

    Each time a [Django template](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template)
    is rendered, it is cached to a global in-memory cache (using Python's
    [`lru_cache`](https://docs.python.org/3/library/functools.html#functools.lru_cache)
    decorator). This speeds up the next render of the component.
    As the same component is often used many times on the same page, these savings add up.

    By default the cache holds 128 component templates in memory, which should be enough for most sites.
    But if you have a lot of components, or if you are overriding
    [`Component.get_template()`](../api#django_components.Component.get_template)
    to render many dynamic templates, you can increase this number.

    ```python
    COMPONENTS = ComponentsSettings(
        template_cache_size=256,
    )
    ```

    To remove the cache limit altogether and cache everything, set `template_cache_size` to `None`.

    ```python
    COMPONENTS = ComponentsSettings(
        template_cache_size=None,
    )
    ```

    If you want to add templates to the cache yourself, you can use
    [`cached_template()`](../api/#django_components.cached_template):

    ```python
    from django_components import cached_template

    cached_template("Variable: {{ variable }}")

    # You can optionally specify Template class, and other Template inputs:
    class MyTemplate(Template):
        pass

    cached_template(
        "Variable: {{ variable }}",
        template_cls=MyTemplate,
        name=...
        origin=...
        engine=...
    )
    ```
    """


# NOTE: Some defaults depend on the Django settings, which may not yet be
# initialized at the time that these settings are generated. For such cases
# we define the defaults as a factory function, and use the `Dynamic` class to
# mark such fields.
@dataclass(frozen=True)
class Dynamic(Generic[T]):
    getter: Callable[[], T]


# This is the source of truth for the settings defaults. If the documentation
# does NOT match it, the documentation should be updated.
#
# NOTE: Because we need to access Django settings to generate default dirs
#       for `COMPONENTS.dirs`, we do it lazily.
# NOTE 2: We show the defaults in the documentation, together with the comments
#        (except for the `Dynamic` instances and comments like `type: ignore`).
#        So `fmt: off` turns off Black formatting and `snippet:defaults` allows
#        us to extract the snippet from the file.
#
# fmt: off
# --snippet:defaults--
defaults = ComponentsSettings(
    autodiscover=True,
    cache=None,
    context_behavior=ContextBehavior.DJANGO.value,  # "django" | "isolated"
    # Root-level "components" dirs, e.g. `/path/to/proj/components/`
    dirs=Dynamic(lambda: [Path(settings.BASE_DIR) / "components"]),  # type: ignore[arg-type]
    # App-level "components" dirs, e.g. `[app]/components/`
    app_dirs=["components"],
    debug_highlight_components=False,
    debug_highlight_slots=False,
    dynamic_component_name="dynamic",
    extensions=[],
    extensions_defaults={},
    libraries=[],  # E.g. ["mysite.components.forms", ...]
    multiline_tags=True,
    reload_on_file_change=False,
    static_files_allowed=[
        ".css",
        ".js", ".jsx", ".ts", ".tsx",
        # Images
        ".apng", ".png", ".avif", ".gif", ".jpg",
        ".jpeg", ".jfif", ".pjpeg", ".pjp", ".svg",
        ".webp", ".bmp", ".ico", ".cur", ".tif", ".tiff",
        # Fonts
        ".eot", ".ttf", ".woff", ".otf", ".svg",
    ],
    static_files_forbidden=[
        # See https://marketplace.visualstudio.com/items?itemName=junstyle.vscode-django-support
        ".html", ".django", ".dj", ".tpl",
        # Python files
        ".py", ".pyc",
    ],
    tag_formatter="django_components.component_formatter",
    template_cache_size=128,
)
# --endsnippet:defaults--
# fmt: on


# Interface through which we access the settings.
#
# This is the only place where we actually access the settings.
# The settings are merged with defaults, and then validated.
#
# The settings are then available through the `app_settings` object.
#
# Settings are loaded from Django settings only once, at `apps.py` in `ready()`.
class InternalSettings:
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        self._settings = ComponentsSettings(**settings) if settings else defaults

    def _load_settings(self) -> None:
        data = getattr(settings, "COMPONENTS", {})
        components_settings = ComponentsSettings(**data) if not isinstance(data, ComponentsSettings) else data

        # Merge we defaults and otherwise initialize if necessary

        # For DIRS setting, we use a getter for the default value, because the default value
        # uses Django settings, which may not yet be initialized at the time these settings are generated.
        dirs_default_fn = cast(Dynamic[Sequence[Union[str, Tuple[str, str]]]], defaults.dirs)
        dirs_default = dirs_default_fn.getter()

        self._settings = ComponentsSettings(
            autodiscover=default(components_settings.autodiscover, defaults.autodiscover),
            cache=default(components_settings.cache, defaults.cache),
            dirs=default(components_settings.dirs, dirs_default),
            app_dirs=default(components_settings.app_dirs, defaults.app_dirs),
            debug_highlight_components=default(
                components_settings.debug_highlight_components, defaults.debug_highlight_components
            ),
            debug_highlight_slots=default(components_settings.debug_highlight_slots, defaults.debug_highlight_slots),
            dynamic_component_name=default(
                components_settings.dynamic_component_name, defaults.dynamic_component_name
            ),
            libraries=default(components_settings.libraries, defaults.libraries),
            # NOTE: Internally we store the extensions as a list of instances, but the user
            #       can pass in either a list of classes or a list of import strings.
            extensions=self._prepare_extensions(components_settings),  # type: ignore[arg-type]
            extensions_defaults=default(components_settings.extensions_defaults, defaults.extensions_defaults),
            multiline_tags=default(components_settings.multiline_tags, defaults.multiline_tags),
            reload_on_file_change=self._prepare_reload_on_file_change(components_settings),
            template_cache_size=default(components_settings.template_cache_size, defaults.template_cache_size),
            static_files_allowed=default(components_settings.static_files_allowed, defaults.static_files_allowed),
            static_files_forbidden=self._prepare_static_files_forbidden(components_settings),
            context_behavior=self._prepare_context_behavior(components_settings),
            tag_formatter=default(components_settings.tag_formatter, defaults.tag_formatter),  # type: ignore[arg-type]
        )

    def _prepare_extensions(self, new_settings: ComponentsSettings) -> List["ComponentExtension"]:
        extensions: Sequence[Union[Type["ComponentExtension"], str]] = default(
            new_settings.extensions, cast(List[str], defaults.extensions)
        )

        # Prepend built-in extensions
        from django_components.extensions.cache import CacheExtension
        from django_components.extensions.debug_highlight import DebugHighlightExtension
        from django_components.extensions.defaults import DefaultsExtension
        from django_components.extensions.view import ViewExtension

        extensions = cast(
            List[Type["ComponentExtension"]],
            [
                CacheExtension,
                DefaultsExtension,
                ViewExtension,
                DebugHighlightExtension,
            ],
        ) + list(extensions)

        # Extensions may be passed in either as classes or import strings.
        extension_instances: List["ComponentExtension"] = []
        for extension in extensions:
            if isinstance(extension, str):
                import_path, class_name = extension.rsplit(".", 1)
                extension_module = import_module(import_path)
                extension = cast(Type["ComponentExtension"], getattr(extension_module, class_name))

            if isinstance(extension, type):
                extension_instance = extension()
            else:
                extension_instances.append(extension)

            extension_instances.append(extension_instance)

        return extension_instances

    def _prepare_reload_on_file_change(self, new_settings: ComponentsSettings) -> bool:
        val = new_settings.reload_on_file_change
        # TODO_REMOVE_IN_V1
        if val is None:
            val = new_settings.reload_on_template_change

        return default(val, cast(bool, defaults.reload_on_file_change))

    def _prepare_static_files_forbidden(self, new_settings: ComponentsSettings) -> List[Union[str, re.Pattern]]:
        val = new_settings.static_files_forbidden
        # TODO_REMOVE_IN_V1
        if val is None:
            val = new_settings.forbidden_static_files

        return default(val, cast(List[Union[str, re.Pattern]], defaults.static_files_forbidden))

    def _prepare_context_behavior(self, new_settings: ComponentsSettings) -> Literal["django", "isolated"]:
        raw_value = cast(
            Literal["django", "isolated"],
            default(new_settings.context_behavior, defaults.context_behavior),
        )
        try:
            ContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in ContextBehavior]
            raise ValueError(f"Invalid context behavior: {raw_value}. Valid options are {valid_values}")

        return raw_value

    # TODO REMOVE THE PROPERTIES BELOW? THEY NO LONGER SERVE ANY PURPOSE
    @property
    def AUTODISCOVER(self) -> bool:
        return self._settings.autodiscover  # type: ignore[return-value]

    @property
    def CACHE(self) -> Optional[str]:
        return self._settings.cache

    @property
    def DIRS(self) -> Sequence[Union[str, PathLike, Tuple[str, str], Tuple[str, PathLike]]]:
        return self._settings.dirs  # type: ignore[return-value]

    @property
    def APP_DIRS(self) -> Sequence[str]:
        return self._settings.app_dirs  # type: ignore[return-value]

    @property
    def DEBUG_HIGHLIGHT_COMPONENTS(self) -> bool:
        return self._settings.debug_highlight_components  # type: ignore[return-value]

    @property
    def DEBUG_HIGHLIGHT_SLOTS(self) -> bool:
        return self._settings.debug_highlight_slots  # type: ignore[return-value]

    @property
    def DYNAMIC_COMPONENT_NAME(self) -> str:
        return self._settings.dynamic_component_name  # type: ignore[return-value]

    @property
    def LIBRARIES(self) -> List[str]:
        return self._settings.libraries  # type: ignore[return-value]

    @property
    def EXTENSIONS(self) -> List["ComponentExtension"]:
        return self._settings.extensions  # type: ignore[return-value]

    @property
    def MULTILINE_TAGS(self) -> bool:
        return self._settings.multiline_tags  # type: ignore[return-value]

    @property
    def RELOAD_ON_FILE_CHANGE(self) -> bool:
        return self._settings.reload_on_file_change  # type: ignore[return-value]

    @property
    def TEMPLATE_CACHE_SIZE(self) -> int:
        return self._settings.template_cache_size  # type: ignore[return-value]

    @property
    def STATIC_FILES_ALLOWED(self) -> Sequence[Union[str, re.Pattern]]:
        return self._settings.static_files_allowed  # type: ignore[return-value]

    @property
    def STATIC_FILES_FORBIDDEN(self) -> Sequence[Union[str, re.Pattern]]:
        return self._settings.static_files_forbidden  # type: ignore[return-value]

    @property
    def CONTEXT_BEHAVIOR(self) -> ContextBehavior:
        return ContextBehavior(self._settings.context_behavior)

    @property
    def TAG_FORMATTER(self) -> Union["TagFormatterABC", str]:
        return self._settings.tag_formatter  # type: ignore[return-value]


app_settings = InternalSettings()
