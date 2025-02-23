import re
from dataclasses import dataclass
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from django.conf import settings

from django_components.util.misc import default

if TYPE_CHECKING:
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
    2. Variables from [`Component.get_context_data()`](../api#django_components.Component.get_context_data)
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

    and this context returned from the `Component.get_context_data()` method
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
    [`Component.get_context_data()`](../api#django_components.Component.get_context_data).

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

    and this context returned from the `get_context_data()` method
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
    [STATICFILES_DIRS](https://docs.djangoproject.com/en/5.1/ref/settings/#std-setting-STATICFILES_DIRS).

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
    Name of the [Django cache](https://docs.djangoproject.com/en/5.1/topics/cache/)
    to be used for storing component's JS and CSS files.

    If `None`, a [`LocMemCache`](https://docs.djangoproject.com/en/5.1/topics/cache/#local-memory-caching)
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

    debug_highlight_components: Optional[bool] = None
    """
    Enable / disable component highlighting.
    See [Troubleshooting](../../guides/other/troubleshooting#component-highlighting) for more details.

    Defaults to `False`.

    ```python
    COMPONENTS = ComponentsSettings(
        debug_highlight_components=True,
    )
    ```
    """

    debug_highlight_slots: Optional[bool] = None
    """
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
    [`AppConfig.ready()`](https://docs.djangoproject.com/en/5.1/ref/applications/#django.apps.AppConfig.ready):

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
    are treated as [static files](https://docs.djangoproject.com/en/5.1/howto/static-files/).

    If a file is matched against any of the patterns, it's considered a static file. Such files are collected
    when running [`collectstatic`](https://docs.djangoproject.com/en/5.1/ref/contrib/staticfiles/#collectstatic),
    and can be accessed under the
    [static file endpoint](https://docs.djangoproject.com/en/5.1/ref/settings/#static-url).

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
    will NEVER be treated as [static files](https://docs.djangoproject.com/en/5.1/howto/static-files/).

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

    render_type_provider: Optional[str] = None

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

    Each time a [Django template](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Template)
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
    render_type_provider="django_components.static_document_render_type",
    tag_formatter="django_components.component_formatter",
    template_cache_size=128,
)
# --endsnippet:defaults--
# fmt: on


class InternalSettings:
    @property
    def _settings(self) -> ComponentsSettings:
        data = getattr(settings, "COMPONENTS", {})
        return ComponentsSettings(**data) if not isinstance(data, ComponentsSettings) else data

    @property
    def AUTODISCOVER(self) -> bool:
        return default(self._settings.autodiscover, cast(bool, defaults.autodiscover))

    @property
    def CACHE(self) -> Optional[str]:
        return default(self._settings.cache, defaults.cache)

    @property
    def DIRS(self) -> Sequence[Union[str, PathLike, Tuple[str, str], Tuple[str, PathLike]]]:
        # For DIRS we use a getter, because default values uses Django settings,
        # which may not yet be initialized at the time these settings are generated.
        default_fn = cast(Dynamic[Sequence[Union[str, Tuple[str, str]]]], defaults.dirs)
        default_dirs = default_fn.getter()
        return default(self._settings.dirs, default_dirs)

    @property
    def APP_DIRS(self) -> Sequence[str]:
        return default(self._settings.app_dirs, cast(List[str], defaults.app_dirs))

    @property
    def DEBUG_HIGHLIGHT_COMPONENTS(self) -> bool:
        return default(self._settings.debug_highlight_components, cast(bool, defaults.debug_highlight_components))

    @property
    def DEBUG_HIGHLIGHT_SLOTS(self) -> bool:
        return default(self._settings.debug_highlight_slots, cast(bool, defaults.debug_highlight_slots))

    @property
    def DYNAMIC_COMPONENT_NAME(self) -> str:
        return default(self._settings.dynamic_component_name, cast(str, defaults.dynamic_component_name))

    @property
    def LIBRARIES(self) -> List[str]:
        return default(self._settings.libraries, cast(List[str], defaults.libraries))

    @property
    def MULTILINE_TAGS(self) -> bool:
        return default(self._settings.multiline_tags, cast(bool, defaults.multiline_tags))

    @property
    def RELOAD_ON_FILE_CHANGE(self) -> bool:
        val = self._settings.reload_on_file_change
        # TODO_REMOVE_IN_V1
        if val is None:
            val = self._settings.reload_on_template_change

        return default(val, cast(bool, defaults.reload_on_file_change))

    @property
    def TEMPLATE_CACHE_SIZE(self) -> int:
        return default(self._settings.template_cache_size, cast(int, defaults.template_cache_size))

    @property
    def STATIC_FILES_ALLOWED(self) -> Sequence[Union[str, re.Pattern]]:
        return default(self._settings.static_files_allowed, cast(List[str], defaults.static_files_allowed))

    @property
    def STATIC_FILES_FORBIDDEN(self) -> Sequence[Union[str, re.Pattern]]:
        val = self._settings.static_files_forbidden
        # TODO_REMOVE_IN_V1
        if val is None:
            val = self._settings.forbidden_static_files

        return default(val, cast(List[str], defaults.static_files_forbidden))

    @property
    def CONTEXT_BEHAVIOR(self) -> ContextBehavior:
        raw_value = cast(str, default(self._settings.context_behavior, defaults.context_behavior))
        return self._validate_context_behavior(raw_value)

    def _validate_context_behavior(self, raw_value: Union[ContextBehavior, str]) -> ContextBehavior:
        try:
            return ContextBehavior(raw_value)
        except ValueError:
            valid_values = [behavior.value for behavior in ContextBehavior]
            raise ValueError(f"Invalid context behavior: {raw_value}. Valid options are {valid_values}")

    @property
    def RENDER_TYPE_PROVIDER(self) -> str:
        return default(self._settings.render_type_provider, cast(str, defaults.render_type_provider))

    @property
    def TAG_FORMATTER(self) -> Union["TagFormatterABC", str]:
        tag_formatter = default(self._settings.tag_formatter, cast(str, defaults.tag_formatter))
        return cast(Union["TagFormatterABC", str], tag_formatter)


app_settings = InternalSettings()
