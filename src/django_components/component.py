import sys
import types
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Deque,
    Dict,
    Generator,
    Generic,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from weakref import ReferenceType, finalize

from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media as MediaCls
from django.http import HttpRequest, HttpResponse
from django.template.base import NodeList, Origin, Parser, Template, TextNode, Token
from django.template.context import Context, RequestContext
from django.template.loader import get_template
from django.template.loader_tags import BLOCK_CONTEXT_KEY, BlockContext
from django.test.signals import template_rendered
from django.utils.html import conditional_escape
from django.views import View

from django_components.app_settings import ContextBehavior, app_settings
from django_components.component_media import ComponentMediaInput, ComponentMediaMeta
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as registry_
from django_components.context import _COMPONENT_CONTEXT_KEY, make_isolated_context_copy
from django_components.dependencies import (
    RenderType,
    cache_component_css,
    cache_component_css_vars,
    cache_component_js,
    cache_component_js_vars,
    comp_hash_mapping,
    insert_component_dependencies_comment,
)
from django_components.dependencies import render_dependencies as _render_dependencies
from django_components.dependencies import (
    set_component_attrs_for_js_and_css,
)
from django_components.extension import (
    OnComponentClassCreatedContext,
    OnComponentClassDeletedContext,
    OnComponentDataContext,
    OnComponentInputContext,
    extensions,
)
from django_components.extensions.view import ViewFn
from django_components.node import BaseNode
from django_components.perfutil.component import ComponentRenderer, component_context_cache, component_post_render
from django_components.perfutil.provide import register_provide_reference, unregister_provide_reference
from django_components.provide import get_injected_context_var
from django_components.slots import (
    Slot,
    SlotContent,
    SlotFunc,
    SlotIsFilled,
    SlotName,
    SlotRef,
    SlotResult,
    _is_extracting_fill,
    _nodelist_to_slot_render_func,
    resolve_fills,
)
from django_components.template import cached_template
from django_components.util.component_highlight import apply_component_highlight
from django_components.util.context import gen_context_processors_data, snapshot_context
from django_components.util.django_monkeypatch import is_template_cls_patched
from django_components.util.exception import component_error_message
from django_components.util.logger import trace_component_msg
from django_components.util.misc import gen_id, get_import_path, hash_comp_cls
from django_components.util.template_tag import TagAttr
from django_components.util.validation import validate_typed_dict, validate_typed_tuple
from django_components.util.weakref import cached_ref

# TODO_REMOVE_IN_V1 - Users should use top-level import instead
# isort: off
from django_components.component_registry import AlreadyRegistered as AlreadyRegistered  # NOQA
from django_components.component_registry import ComponentRegistry as ComponentRegistry  # NOQA
from django_components.component_registry import NotRegistered as NotRegistered  # NOQA
from django_components.component_registry import register as register  # NOQA
from django_components.component_registry import registry as registry  # NOQA

# isort: on

COMP_ONLY_FLAG = "only"

# Define TypeVars for args and kwargs
ArgsType = TypeVar("ArgsType", bound=tuple, contravariant=True)
KwargsType = TypeVar("KwargsType", bound=Mapping[str, Any], contravariant=True)
SlotsType = TypeVar("SlotsType", bound=Mapping[SlotName, SlotContent])
DataType = TypeVar("DataType", bound=Mapping[str, Any], covariant=True)
JsDataType = TypeVar("JsDataType", bound=Mapping[str, Any])
CssDataType = TypeVar("CssDataType", bound=Mapping[str, Any])


# NOTE: `ReferenceType` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    AllComponents = List[ReferenceType[Type["Component"]]]
else:
    AllComponents = List[ReferenceType]


# Keep track of all the Component classes created, so we can clean up after tests
ALL_COMPONENTS: AllComponents = []


def all_components() -> List[Type["Component"]]:
    """Get a list of all created [`Component`](../api#django_components.Component) classes."""
    components: List[Type["Component"]] = []
    for comp_ref in ALL_COMPONENTS:
        comp = comp_ref()
        if comp is not None:
            components.append(comp)
    return components


@dataclass(frozen=True)
class RenderInput(Generic[ArgsType, KwargsType, SlotsType]):
    context: Context
    args: ArgsType
    kwargs: KwargsType
    slots: SlotsType
    type: RenderType
    render_dependencies: bool


@dataclass()
class MetadataItem(Generic[ArgsType, KwargsType, SlotsType]):
    render_id: str
    input: RenderInput[ArgsType, KwargsType, SlotsType]
    is_filled: Optional[SlotIsFilled]
    request: Optional[HttpRequest]


class ComponentVars(NamedTuple):
    """
    Type for the variables available inside the component templates.

    All variables here are scoped under `component_vars.`, so e.g. attribute
    `is_filled` on this class is accessible inside the template as:

    ```django
    {{ component_vars.is_filled }}
    ```
    """

    is_filled: Dict[str, bool]
    """
    Dictonary describing which component slots are filled (`True`) or are not (`False`).

    <i>New in version 0.70</i>

    Use as `{{ component_vars.is_filled }}`

    Example:

    ```django
    {# Render wrapping HTML only if the slot is defined #}
    {% if component_vars.is_filled.my_slot %}
        <div class="slot-wrapper">
            {% slot "my_slot" / %}
        </div>
    {% endif %}
    ```

    This is equivalent to checking if a given key is among the slot fills:

    ```py
    class MyTable(Component):
        def get_context_data(self, *args, **kwargs):
            return {
                "my_slot_filled": "my_slot" in self.input.slots
            }
    ```
    """


# Descriptor to pass getting/setting of `template_name` onto `template_file`
class ComponentTemplateNameDescriptor:
    def __get__(self, instance: Optional["Component"], cls: Type["Component"]) -> Any:
        obj = instance if instance is not None else cls
        return obj.template_file  # type: ignore[attr-defined]

    def __set__(self, instance_or_cls: Union["Component", Type["Component"]], value: Any) -> None:
        cls = instance_or_cls if isinstance(instance_or_cls, type) else instance_or_cls.__class__
        cls.template_file = value


class ComponentMeta(ComponentMediaMeta):
    def __new__(mcs, name: Any, bases: Tuple, attrs: Dict) -> Any:
        # If user set `template_name` on the class, we instead set it to `template_file`,
        # because we want `template_name` to be the descriptor that proxies to `template_file`.
        if "template_name" in attrs:
            attrs["template_file"] = attrs.pop("template_name")
        attrs["template_name"] = ComponentTemplateNameDescriptor()

        return super().__new__(mcs, name, bases, attrs)

    # This runs when a Component class is being deleted
    def __del__(cls) -> None:
        comp_cls = cast(Type["Component"], cls)
        extensions.on_component_class_deleted(OnComponentClassDeletedContext(comp_cls))


# Internal data that are made available within the component's template
@dataclass
class ComponentContext:
    component_name: str
    component_id: str
    component_class: Type["Component"]
    component_path: List[str]
    template_name: Optional[str]
    is_dynamic_component: bool
    default_slot: Optional[str]
    fills: Dict[SlotName, Slot]
    outer_context: Optional[Context]
    registry: ComponentRegistry
    request: Optional[HttpRequest]
    # When we render a component, the root component, together with all the nested Components,
    # shares this dictionary for storing callbacks that are called from within `component_post_render`.
    # This is so that we can pass them all in when the root component is passed to `component_post_render`.
    post_render_callbacks: Dict[str, Callable[[str], str]]


class Component(
    Generic[ArgsType, KwargsType, SlotsType, DataType, JsDataType, CssDataType],
    metaclass=ComponentMeta,
):
    # #####################################
    # PUBLIC API (Configurable by users)
    # #####################################

    template_file: Optional[str] = None
    """
    Filepath to the Django template associated with this component.

    The filepath must be either:

    - Relative to the directory where the Component's Python file is defined.
    - Relative to one of the component directories, as set by
      [`COMPONENTS.dirs`](../settings.md#django_components.app_settings.ComponentsSettings.dirs)
      or
      [`COMPONENTS.app_dirs`](../settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
      (e.g. `<root>/components/`).
    - Relative to the template directories, as set by Django's `TEMPLATES` setting (e.g. `<root>/templates/`).

    Only one of [`template_file`](../api#django_components.Component.template_file),
    [`get_template_name`](../api#django_components.Component.get_template_name),
    [`template`](../api#django_components.Component.template)
    or [`get_template`](../api#django_components.Component.get_template) must be defined.

    **Example:**

    ```py
    class MyComponent(Component):
        template_file = "path/to/template.html"

        def get_context_data(self):
            return {"name": "World"}
    ```
    """

    # NOTE: This attribute is managed by `ComponentTemplateNameDescriptor` that's set in the metaclass.
    #       But we still define it here for documenting and type hinting.
    template_name: Optional[str]
    """
    Alias for [`template_file`](../api#django_components.Component.template_file).

    For historical reasons, django-components used `template_name` to align with Django's
    [TemplateView](https://docs.djangoproject.com/en/5.1/ref/class-based-views/base/#django.views.generic.base.TemplateView).

    `template_file` was introduced to align with `js/js_file` and `css/css_file`.

    Setting and accessing this attribute is proxied to `template_file`.
    """

    def get_template_name(self, context: Context) -> Optional[str]:
        """
        Filepath to the Django template associated with this component.

        The filepath must be relative to either the file where the component class was defined,
        or one of the roots of `STATIFILES_DIRS`.

        Only one of [`template_file`](../api#django_components.Component.template_file),
        [`get_template_name`](../api#django_components.Component.get_template_name),
        [`template`](../api#django_components.Component.template)
        or [`get_template`](../api#django_components.Component.get_template) must be defined.
        """
        return None

    template: Optional[Union[str, Template]] = None
    """
    Inlined Django template associated with this component. Can be a plain string or a Template instance.

    Only one of [`template_file`](../api#django_components.Component.template_file),
    [`get_template_name`](../api#django_components.Component.get_template_name),
    [`template`](../api#django_components.Component.template)
    or [`get_template`](../api#django_components.Component.get_template) must be defined.

    **Example:**

    ```py
    class MyComponent(Component):
        template = "Hello, {{ name }}!"

        def get_context_data(self):
            return {"name": "World"}
    ```
    """

    def get_template(self, context: Context) -> Optional[Union[str, Template]]:
        """
        Inlined Django template associated with this component. Can be a plain string or a Template instance.

        Only one of [`template_file`](../api#django_components.Component.template_file),
        [`get_template_name`](../api#django_components.Component.get_template_name),
        [`template`](../api#django_components.Component.template)
        or [`get_template`](../api#django_components.Component.get_template) must be defined.
        """
        return None

    def get_context_data(self, *args: Any, **kwargs: Any) -> DataType:
        return cast(DataType, {})

    js: Optional[str] = None
    """
    Main JS associated with this component inlined as string.

    Only one of [`js`](../api#django_components.Component.js) or
    [`js_file`](../api#django_components.Component.js_file) must be defined.

    **Example:**

    ```py
    class MyComponent(Component):
        js = "console.log('Hello, World!');"
    ```
    """

    js_file: Optional[str] = None
    """
    Main JS associated with this component as file path.

    The filepath must be either:

    - Relative to the directory where the Component's Python file is defined.
    - Relative to one of the component directories, as set by
      [`COMPONENTS.dirs`](../settings.md#django_components.app_settings.ComponentsSettings.dirs)
      or
      [`COMPONENTS.app_dirs`](../settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
      (e.g. `<root>/components/`).
    - Relative to the staticfiles directories, as set by Django's `STATICFILES_DIRS` setting (e.g. `<root>/static/`).

    When you create a Component class with `js_file`, these will happen:

    1. If the file path is relative to the directory where the component's Python file is,
       the path is resolved.
    2. The file is read and its contents is set to [`Component.js`](../api#django_components.Component.js).

    Only one of [`js`](../api#django_components.Component.js) or
    [`js_file`](../api#django_components.Component.js_file) must be defined.

    **Example:**

    ```js title="path/to/script.js"
    console.log('Hello, World!');
    ```

    ```py title="path/to/component.py"
    class MyComponent(Component):
        js_file = "path/to/script.js"

    print(MyComponent.js)
    # Output: console.log('Hello, World!');
    ```
    """

    css: Optional[str] = None
    """
    Main CSS associated with this component inlined as string.

    Only one of [`css`](../api#django_components.Component.css) or
    [`css_file`](../api#django_components.Component.css_file) must be defined.

    **Example:**

    ```py
    class MyComponent(Component):
        css = \"\"\"
        .my-class {
            color: red;
        }
        \"\"\"
    ```
    """

    css_file: Optional[str] = None
    """
    Main CSS associated with this component as file path.

    The filepath must be either:

    - Relative to the directory where the Component's Python file is defined.
    - Relative to one of the component directories, as set by
      [`COMPONENTS.dirs`](../settings.md#django_components.app_settings.ComponentsSettings.dirs)
      or
      [`COMPONENTS.app_dirs`](../settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
      (e.g. `<root>/components/`).
    - Relative to the staticfiles directories, as set by Django's `STATICFILES_DIRS` setting (e.g. `<root>/static/`).

    When you create a Component class with `css_file`, these will happen:

    1. If the file path is relative to the directory where the component's Python file is,
       the path is resolved.
    2. The file is read and its contents is set to [`Component.css`](../api#django_components.Component.css).

    Only one of [`css`](../api#django_components.Component.css) or
    [`css_file`](../api#django_components.Component.css_file) must be defined.

    **Example:**

    ```css title="path/to/style.css"
    .my-class {
        color: red;
    }
    ```

    ```py title="path/to/component.py"
    class MyComponent(Component):
        css_file = "path/to/style.css"

    print(MyComponent.css)
    # Output:
    # .my-class {
    #     color: red;
    # };
    ```
    """

    media: Optional[MediaCls] = None
    """
    Normalized definition of JS and CSS media files associated with this component.
    `None` if [`Component.Media`](../api#django_components.Component.Media) is not defined.

    This field is generated from [`Component.media_class`](../api#django_components.Component.media_class).

    Read more on [Accessing component's HTML / JS / CSS](../../concepts/fundamentals/defining_js_css_html_files/#accessing-components-media-files).

    **Example:**

    ```py
    class MyComponent(Component):
        class Media:
            js = "path/to/script.js"
            css = "path/to/style.css"

    print(MyComponent.media)
    # Output:
    # <script src="/static/path/to/script.js"></script>
    # <link href="/static/path/to/style.css" media="all" rel="stylesheet">
    ```
    """  # noqa: E501

    media_class: Type[MediaCls] = MediaCls
    """
    Set the [Media class](https://docs.djangoproject.com/en/5.1/topics/forms/media/#assets-as-a-static-definition)
    that will be instantiated with the JS and CSS media files from
    [`Component.Media`](../api#django_components.Component.Media).

    This is useful when you want to customize the behavior of the media files, like
    customizing how the JS or CSS files are rendered into `<script>` or `<link>` HTML tags.
    Read more in [Defining HTML / JS / CSS files](../../concepts/fundamentals/defining_js_css_html_files/#customize-how-paths-are-rendered-into-html-tags-with-media_class).

    **Example:**

    ```py
    class MyTable(Component):
        class Media:
            js = "path/to/script.js"
            css = "path/to/style.css"

        media_class = MyMediaClass
    ```
    """  # noqa: E501

    Media: Optional[Type[ComponentMediaInput]] = None
    """
    Defines JS and CSS media files associated with this component.

    This `Media` class behaves similarly to
    [Django's Media class](https://docs.djangoproject.com/en/5.1/topics/forms/media/#assets-as-a-static-definition):

    - Paths are generally handled as static file paths, and resolved URLs are rendered to HTML with
      `media_class.render_js()` or `media_class.render_css()`.
    - A path that starts with `http`, `https`, or `/` is considered a URL, skipping the static file resolution.
      This path is still rendered to HTML with `media_class.render_js()` or `media_class.render_css()`.
    - A `SafeString` (with `__html__` method) is considered an already-formatted HTML tag, skipping both static file
        resolution and rendering with `media_class.render_js()` or `media_class.render_css()`.
    - You can set [`extend`](../api#django_components.ComponentMediaInput.extend) to configure
      whether to inherit JS / CSS from parent components. See
      [Controlling Media Inheritance](../../concepts/fundamentals/defining_js_css_html_files/#controlling-media-inheritance).

    However, there's a few differences from Django's Media class:

    1. Our Media class accepts various formats for the JS and CSS files: either a single file, a list,
       or (CSS-only) a dictionary (See [`ComponentMediaInput`](../api#django_components.ComponentMediaInput)).
    2. Individual JS / CSS files can be any of `str`, `bytes`, `Path`,
       [`SafeString`](https://dev.to/doridoro/django-safestring-afj), or a function
       (See [`ComponentMediaInputPath`](../api#django_components.ComponentMediaInputPath)).

    **Example:**

    ```py
    class MyTable(Component):
        class Media:
            js = [
                "path/to/script.js",
                "https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js",  # AlpineJS
            ]
            css = {
                "all": [
                    "path/to/style.css",
                    "https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css",  # TailwindCSS
                ],
                "print": ["path/to/style2.css"],
            }
    ```
    """  # noqa: E501

    response_class = HttpResponse
    """This allows to configure what class is used to generate response from `render_to_response`"""

    # #####################################
    # PUBLIC API - HOOKS
    # #####################################

    def on_render_before(self, context: Context, template: Template) -> None:
        """
        Hook that runs just before the component's template is rendered.

        You can use this hook to access or modify the context or the template.
        """
        pass

    def on_render_after(self, context: Context, template: Template, content: str) -> Optional[SlotResult]:
        """
        Hook that runs just after the component's template was rendered.
        It receives the rendered output as the last argument.

        You can use this hook to access the context or the template, but modifying
        them won't have any effect.

        To override the content that gets rendered, you can return a string or SafeString
        from this hook.
        """
        pass

    # #####################################
    # MISC
    # #####################################

    _class_hash: ClassVar[str]

    def __init__(
        self,
        registered_name: Optional[str] = None,
        outer_context: Optional[Context] = None,
        registry: Optional[ComponentRegistry] = None,  # noqa F811
    ):
        # When user first instantiates the component class before calling
        # `render` or `render_to_response`, then we want to allow the render
        # function to make use of the instantiated object.
        #
        # So while `MyComp.render()` creates a new instance of MyComp internally,
        # if we do `MyComp(registered_name="abc").render()`, then we use the
        # already-instantiated object.
        #
        # To achieve that, we want to re-assign the class methods as instance methods.
        # For that we have to "unwrap" the class methods via __func__.
        # See https://stackoverflow.com/a/76706399/9788634
        self.render_to_response = types.MethodType(self.__class__.render_to_response.__func__, self)  # type: ignore
        self.render = types.MethodType(self.__class__.render.__func__, self)  # type: ignore
        self.as_view = types.MethodType(self.__class__.as_view.__func__, self)  # type: ignore

        self.registered_name: Optional[str] = registered_name
        self.outer_context: Optional[Context] = outer_context
        self.registry = registry or registry_
        self._metadata_stack: Deque[MetadataItem[ArgsType, KwargsType, SlotsType]] = deque()
        # None == uninitialized, False == No types, Tuple == types
        self._types: Optional[Union[Tuple[Any, Any, Any, Any, Any, Any], Literal[False]]] = None

        extensions._init_component_instance(self)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls._class_hash = hash_comp_cls(cls)
        comp_hash_mapping[cls._class_hash] = cls

        ALL_COMPONENTS.append(cached_ref(cls))  # type: ignore[arg-type]
        extensions._init_component_class(cls)
        extensions.on_component_class_created(OnComponentClassCreatedContext(cls))

    @contextmanager
    def _with_metadata(self, item: MetadataItem) -> Generator[None, None, None]:
        self._metadata_stack.append(item)
        yield
        self._metadata_stack.pop()

    @property
    def name(self) -> str:
        return self.registered_name or self.__class__.__name__

    @property
    def id(self) -> str:
        """
        This ID is unique for every time a [`Component.render()`](../api#django_components.Component.render)
        (or equivalent) is called (AKA "render ID").

        This is useful for logging or debugging.

        Raises `RuntimeError` if accessed outside of rendering execution.

        A single render ID has a chance of collision 1 in 3.3M. However, due to birthday paradox, the chance of
        collision increases when approaching ~1,000 render IDs.

        **Thus, there is a soft-cap of 1,000 components rendered on a single page.**

        If you need to more than that, please open an issue on GitHub.

        **Example:**

        ```py
        class MyComponent(Component):
            def get_context_data(self):
                print(f"Rendering '{self.id}'")
                return {}

        MyComponent.render()
        # Rendering 'ab3c4d'
        ```
        """
        if not len(self._metadata_stack):
            raise RuntimeError(
                f"{self.name}: Tried to access Component's `id` attribute " "while outside of rendering execution"
            )

        ctx = self._metadata_stack[-1]
        return ctx.render_id

    @property
    def input(self) -> RenderInput[ArgsType, KwargsType, SlotsType]:
        """
        Input holds the data (like arg, kwargs, slots) that were passed to
        the current execution of the `render` method.

        Raises `RuntimeError` if accessed outside of rendering execution.
        """
        if not len(self._metadata_stack):
            raise RuntimeError(f"{self.name}: Tried to access Component input while outside of rendering execution")

        # NOTE: Input is managed as a stack, so if `render` is called within another `render`,
        # the propertes below will return only the inner-most state.
        return self._metadata_stack[-1].input

    @property
    def is_filled(self) -> SlotIsFilled:
        """
        Dictionary describing which slots have or have not been filled.

        This attribute is available for use only within the template as `{{ component_vars.is_filled.slot_name }}`,
        and within `on_render_before` and `on_render_after` hooks.

        Raises `RuntimeError` if accessed outside of rendering execution.
        """
        if not len(self._metadata_stack):
            raise RuntimeError(
                f"{self.name}: Tried to access Component's `is_filled` attribute "
                "while outside of rendering execution"
            )

        ctx = self._metadata_stack[-1]
        if ctx.is_filled is None:
            raise RuntimeError(
                f"{self.name}: Tried to access Component's `is_filled` attribute " "before slots were resolved"
            )

        return ctx.is_filled

    @property
    def request(self) -> Optional[HttpRequest]:
        """
        [HTTPRequest](https://docs.djangoproject.com/en/5.1/ref/request-response/#django.http.HttpRequest)
        object passed to this component.

        In regular Django templates, you have to use
        [`RequestContext`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.RequestContext)
        to pass the `HttpRequest` object to the template.

        But in Components, you can either use `RequestContext`, or pass the `request` object
        explicitly via [`Component.render()`](../api#django_components.Component.render) and
        [`Component.render_to_response()`](../api#django_components.Component.render_to_response).

        When a component is nested in another, the child component uses parent's `request` object.

        Raises `RuntimeError` if accessed outside of rendering execution.

        **Example:**

        ```py
        class MyComponent(Component):
            def get_context_data(self):
                user_id = self.request.GET['user_id']
                return {
                    'user_id': user_id,
                }
        ```
        """
        if not len(self._metadata_stack):
            raise RuntimeError(
                f"{self.name}: Tried to access Component's `request` attribute " "while outside of rendering execution"
            )

        ctx = self._metadata_stack[-1]
        return ctx.request

    @property
    def context_processors_data(self) -> Dict:
        """
        Retrieve data injected by
        [`context_processors`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#configuring-an-engine).

        This data is also available from within the component's template, without having to
        return this data from
        [`get_context_data()`](../api#django_components.Component.get_context_data).

        Unlike regular Django templates, the context processors are applied to components either when:

        - The component is rendered with `RequestContext` (Regular Django behavior)
        - The component is rendered with a regular `Context` (or none), but the `request` kwarg
          of [`Component.render()`](../api#django_components.Component.render) is set.
        - The component is nested in another component that matches one of the two conditions above.

        See
        [`Component.request`](../api#django_components.Component.request)
        on how the `request`
        ([HTTPRequest](https://docs.djangoproject.com/en/5.1/ref/request-response/#django.http.HttpRequest))
        object is passed to and within the components.

        Raises `RuntimeError` if accessed outside of rendering execution.

        **Example:**

        ```py
        class MyComponent(Component):
            def get_context_data(self):
                user = self.context_processors_data['user']
                return {
                    'is_logged_in': user.is_authenticated,
                }
        ```
        """
        if not len(self._metadata_stack):
            raise RuntimeError(
                f"{self.name}: Tried to access Component's `context_processors_data` attribute "
                "while outside of rendering execution"
            )

        context = self.input.context
        request = self.request

        if request is None:
            return {}
        else:
            return gen_context_processors_data(context, request)

    # NOTE: We cache the Template instance. When the template is taken from a file
    #       via `get_template_name`, then we leverage Django's template caching with `get_template()`.
    #       Otherwise, we use our own `cached_template()` to cache the template.
    #
    #       This is important to keep in mind, because the implication is that we should
    #       treat Templates AND their nodelists as IMMUTABLE.
    def _get_template(self, context: Context, component_id: str) -> Template:
        template_name = self.get_template_name(context)
        # TODO_REMOVE_IN_V1 - Remove `self.get_template_string` in v1
        template_getter = getattr(self, "get_template_string", self.get_template)
        template_body = template_getter(context)

        # `get_template_name()`, `get_template()`, and `template` are mutually exclusive
        #
        # Note that `template` and `template_name` are also mutually exclusive, but this
        # is checked when lazy-loading the template from `template_name`. So if user specified
        # `template_name`, then `template` will be populated with the content of that file.
        if self.template is not None and template_name is not None:
            raise ImproperlyConfigured(
                "Received non-null value from both 'template/template_name' and 'get_template_name' in"
                f" Component {type(self).__name__}. Only one of the two must be set."
            )
        if self.template is not None and template_body is not None:
            raise ImproperlyConfigured(
                "Received non-null value from both 'template/template_name' and 'get_template' in"
                f" Component {type(self).__name__}. Only one of the two must be set."
            )
        if template_name is not None and template_body is not None:
            raise ImproperlyConfigured(
                "Received non-null value from both 'get_template_name' and 'get_template' in"
                f" Component {type(self).__name__}. Only one of the two must be set."
            )

        if template_name is not None:
            return get_template(template_name).template

        template_body = template_body if template_body is not None else self.template
        if template_body is not None:
            # We got template string, so we convert it to Template
            if isinstance(template_body, str):
                trace_component_msg("COMP_LOAD", component_name=self.name, component_id=component_id, slot_name=None)
                template: Template = cached_template(
                    template_string=template_body,
                    name=self.template_file or self.name,
                    origin=Origin(
                        name=self.template_file or get_import_path(self.__class__),
                        template_name=self.template_file or self.name,
                    ),
                )
            else:
                template = template_body

            return template

        raise ImproperlyConfigured(
            f"Either 'template_file' or 'template' must be set for Component {type(self).__name__}."
        )

    def inject(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Use this method to retrieve the data that was passed to a `{% provide %}` tag
        with the corresponding key.

        To retrieve the data, `inject()` must be called inside a component that's
        inside the `{% provide %}` tag.

        You may also pass a default that will be used if the `provide` tag with given
        key was NOT found.

        This method mut be used inside the `get_context_data()` method and raises
        an error if called elsewhere.

        Example:

        Given this template:
        ```django
        {% provide "provider" hello="world" %}
            {% component "my_comp" %}
            {% endcomponent %}
        {% endprovide %}
        ```

        And given this definition of "my_comp" component:
        ```py
        from django_components import Component, register

        @register("my_comp")
        class MyComp(Component):
            template = "hi {{ data.hello }}!"
            def get_context_data(self):
                data = self.inject("provider")
                return {"data": data}
        ```

        This renders into:
        ```
        hi world!
        ```

        As the `{{ data.hello }}` is taken from the "provider".
        """
        if self.input is None:
            raise RuntimeError(
                f"Method 'inject()' of component '{self.name}' was called outside of 'get_context_data()'"
            )

        return get_injected_context_var(self.name, self.input.context, key, default)

    @classmethod
    def as_view(cls, **initkwargs: Any) -> ViewFn:
        """
        Shortcut for calling `Component.View.as_view` and passing component instance to it.
        """

        # NOTE: `Component.View` may not be available at the time that URLs are being
        # defined. So we return a view that calls `View.as_view()` only once it's actually called.
        def outer_view(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            # This method may be called as class method or as instance method.
            # If called as class method, create a new instance.
            if isinstance(cls, Component):
                comp: Component = cls
            else:
                comp = cls()

            # `view` is a built-in extension defined in `extensions.view`. It subclasses
            # from Django's `View` class, and adds the `component` attribute to it.
            view_cls = cast(View, cls.View)  # type: ignore[attr-defined]
            inner_view = view_cls.as_view(**initkwargs, component=comp)
            return inner_view(request, *args, **kwargs)

        return outer_view

    # #####################################
    # RENDERING
    # #####################################

    @classmethod
    def render_to_response(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        type: RenderType = "document",
        request: Optional[HttpRequest] = None,
        *response_args: Any,
        **response_kwargs: Any,
    ) -> HttpResponse:
        """
        Render the component and wrap the content in the response class.

        The response class is taken from `Component.response_class`. Defaults to `django.http.HttpResponse`.

        This is the interface for the `django.views.View` class which allows us to
        use components as Django views with `component.as_view()`.

        Inputs:
        - `args` - Positional args for the component. This is the same as calling the component
          as `{% component "my_comp" arg1 arg2 ... %}`
        - `kwargs` - Kwargs for the component. This is the same as calling the component
          as `{% component "my_comp" key1=val1 key2=val2 ... %}`
        - `slots` - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
            Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
            or render function.
        - `escape_slots_content` - Whether the content from `slots` should be escaped.
        - `context` - A context (dictionary or Django's Context) within which the component
          is rendered. The keys on the context can be accessed from within the template.
            - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
              component's args and kwargs.
        - `type` - Configure how to handle JS and CSS dependencies.
            - `"document"` (default) - JS dependencies are inserted into `{% component_js_dependencies %}`,
              or to the end of the `<body>` tag. CSS dependencies are inserted into
              `{% component_css_dependencies %}`, or the end of the `<head>` tag.
        - `request` - The request object. This is only required when needing to use RequestContext,
                      e.g. to enable template `context_processors`.

        Any additional args and kwargs are passed to the `response_class`.

        Example:
        ```py
        MyComponent.render_to_response(
            args=[1, "two", {}],
            kwargs={
                "key": 123,
            },
            slots={
                "header": 'STATIC TEXT HERE',
                "footer": lambda ctx, slot_kwargs, slot_ref: f'CTX: {ctx['hello']} SLOT_DATA: {slot_kwargs['abc']}',
            },
            escape_slots_content=False,
            # HttpResponse input
            status=201,
            headers={...},
        )
        # HttpResponse(content=..., status=201, headers=...)
        ```
        """
        content = cls.render(
            args=args,
            kwargs=kwargs,
            context=context,
            slots=slots,
            escape_slots_content=escape_slots_content,
            type=type,
            render_dependencies=True,
            request=request,
        )
        return cls.response_class(content, *response_args, **response_kwargs)

    @classmethod
    def render(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        type: RenderType = "document",
        render_dependencies: bool = True,
        request: Optional[HttpRequest] = None,
    ) -> str:
        """
        Render the component into a string.

        Inputs:
        - `args` - Positional args for the component. This is the same as calling the component
          as `{% component "my_comp" arg1 arg2 ... %}`
        - `kwargs` - Kwargs for the component. This is the same as calling the component
          as `{% component "my_comp" key1=val1 key2=val2 ... %}`
        - `slots` - Component slot fills. This is the same as pasing `{% fill %}` tags to the component.
            Accepts a dictionary of `{ slot_name: slot_content }` where `slot_content` can be a string
            or render function.
        - `escape_slots_content` - Whether the content from `slots` should be escaped.
        - `context` - A context (dictionary or Django's Context) within which the component
          is rendered. The keys on the context can be accessed from within the template.
            - NOTE: In "isolated" mode, context is NOT accessible, and data MUST be passed via
              component's args and kwargs.
        - `type` - Configure how to handle JS and CSS dependencies.
            - `"document"` (default) - JS dependencies are inserted into `{% component_js_dependencies %}`,
              or to the end of the `<body>` tag. CSS dependencies are inserted into
              `{% component_css_dependencies %}`, or the end of the `<head>` tag.
        - `render_dependencies` - Set this to `False` if you want to insert the resulting HTML into another component.
        - `request` - The request object. This is only required when needing to use RequestContext,
                      e.g. to enable template `context_processors`.
        Example:
        ```py
        MyComponent.render(
            args=[1, "two", {}],
            kwargs={
                "key": 123,
            },
            slots={
                "header": 'STATIC TEXT HERE',
                "footer": lambda ctx, slot_kwargs, slot_ref: f'CTX: {ctx['hello']} SLOT_DATA: {slot_kwargs['abc']}',
            },
            escape_slots_content=False,
        )
        ```
        """
        # This method may be called as class method or as instance method.
        # If called as class method, create a new instance.
        if isinstance(cls, Component):
            comp: Component = cls
        else:
            comp = cls()

        return comp._render(context, args, kwargs, slots, escape_slots_content, type, render_dependencies, request)

    # This is the internal entrypoint for the render function
    def _render(
        self,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        type: RenderType = "document",
        render_dependencies: bool = True,
        request: Optional[HttpRequest] = None,
    ) -> str:
        # Modify the error to display full component path (incl. slots)
        with component_error_message([self.name]):
            try:
                return self._render_impl(
                    context, args, kwargs, slots, escape_slots_content, type, render_dependencies, request
                )
            except Exception as err:
                raise err from None

    def _render_impl(
        self,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[ArgsType] = None,
        kwargs: Optional[KwargsType] = None,
        slots: Optional[SlotsType] = None,
        escape_slots_content: bool = True,
        type: RenderType = "document",
        render_dependencies: bool = True,
        request: Optional[HttpRequest] = None,
    ) -> str:
        # NOTE: We must run validation before we normalize the slots, because the normalization
        #       wraps them in functions.
        self._validate_inputs(args or (), kwargs or {}, slots or {})

        # Allow to pass down Request object via context.
        # `context` may be passed explicitly via `Component.render()` and `Component.render_to_response()`,
        # or implicitly via `{% component %}` tag.
        if request is None and context:
            # If the context is `RequestContext`, it has `request` attribute
            request = getattr(context, "request", None)
            # Check if this is a nested component and whether parent has request
            if request is None:
                parent_id = context.get(_COMPONENT_CONTEXT_KEY, None)
                if parent_id:
                    parent_comp_ctx = component_context_cache[parent_id]
                    request = parent_comp_ctx.request

        # Allow to provide no args/kwargs/slots/context
        args = cast(ArgsType, args or ())
        kwargs = cast(KwargsType, kwargs or {})
        slots_untyped = self._normalize_slot_fills(slots or {}, escape_slots_content)
        slots = cast(SlotsType, slots_untyped)
        # Use RequestContext if request is provided, so that child non-component template tags
        # can access the request object too.
        context = context or (RequestContext(request) if request else Context())

        # Allow to provide a dict instead of Context
        # NOTE: This if/else is important to avoid nested Contexts,
        # See https://github.com/django-components/django-components/issues/414
        if not isinstance(context, Context):
            context = RequestContext(request, context) if request else Context(context)

        # Required for compatibility with Django's {% extends %} tag
        # See https://github.com/django-components/django-components/pull/859
        context.render_context.push({BLOCK_CONTEXT_KEY: context.render_context.get(BLOCK_CONTEXT_KEY, BlockContext())})

        # By adding the current input to the stack, we temporarily allow users
        # to access the provided context, slots, etc. Also required so users can
        # call `self.inject()` from within `get_context_data()`.
        #
        # This is handled as a stack, as users can potentially call `component.render()`
        # from within component hooks. Thus, then they do so, `component.id` will be the ID
        # of the deepest-most call to `component.render()`.
        render_id = gen_id()
        metadata = MetadataItem(
            render_id=render_id,
            input=RenderInput(
                context=context,
                slots=slots,
                args=args,
                kwargs=kwargs,
                type=type,
                render_dependencies=render_dependencies,
            ),
            is_filled=None,
            request=request,
        )

        # Allow plugins to modify or validate the inputs
        extensions.on_component_input(
            OnComponentInputContext(
                component=self,
                component_cls=self.__class__,
                component_id=render_id,
                args=args,  # type: ignore[arg-type]
                kwargs=kwargs,  # type: ignore[arg-type]
                slots=slots,  # type: ignore[arg-type]
                context=context,
            )
        )

        # We pass down the components the info about the component's parent.
        # This is used for correctly resolving slot fills, correct rendering order,
        # or CSS scoping.
        if context.get(_COMPONENT_CONTEXT_KEY, None):
            parent_id = cast(str, context[_COMPONENT_CONTEXT_KEY])
            parent_comp_ctx = component_context_cache[parent_id]
            component_path = [*parent_comp_ctx.component_path, self.name]
            post_render_callbacks = parent_comp_ctx.post_render_callbacks
        else:
            parent_id = None
            component_path = [self.name]
            post_render_callbacks = {}

        trace_component_msg(
            "COMP_PREP_START",
            component_name=self.name,
            component_id=render_id,
            slot_name=None,
            component_path=component_path,
            extra=f"Received {len(args)} args, {len(kwargs)} kwargs, {len(slots)} slots, Available slots: {slots}",
        )

        # Register the component to provide
        register_provide_reference(context, render_id)

        # This is data that will be accessible (internally) from within the component's template
        component_ctx = ComponentContext(
            component_class=self.__class__,
            component_name=self.name,
            component_id=render_id,
            component_path=component_path,
            # Template name is set only once we've resolved the component's Template instance.
            template_name=None,
            fills=slots_untyped,
            is_dynamic_component=getattr(self, "_is_dynamic_component", False),
            # This field will be modified from within `SlotNodes.render()`:
            # - The `default_slot` will be set to the first slot that has the `default` attribute set.
            #   If multiple slots have the `default` attribute set, yet have different name, then
            #   we will raise an error.
            default_slot=None,
            outer_context=snapshot_context(self.outer_context) if self.outer_context is not None else None,
            registry=self.registry,
            # Pass down Request object via context
            request=request,
            post_render_callbacks=post_render_callbacks,
        )

        # Instead of passing the ComponentContext directly through the Context, the entry on the Context
        # contains only a key to retrieve the ComponentContext from `component_context_cache`.
        #
        # This way, the flow is easier to debug. Because otherwise, if you try to print out
        # or inspect the Context object, your screen is filled with the deeply nested ComponentContext objects.
        component_context_cache[render_id] = component_ctx

        # Allow to access component input and metadata like component ID from within these hook
        with self._with_metadata(metadata):
            context_processors_data = self.context_processors_data
            context_data = self.get_context_data(*args, **kwargs)
            # TODO - enable JS and CSS vars - EXPOSE AND DOCUMENT AND MAKE NON-NULL
            js_data = self.get_js_data(*args, **kwargs) if hasattr(self, "get_js_data") else {}  # type: ignore
            css_data = self.get_css_data(*args, **kwargs) if hasattr(self, "get_css_data") else {}  # type: ignore
        self._validate_outputs(data=context_data)

        extensions.on_component_data(
            OnComponentDataContext(
                component=self,
                component_cls=self.__class__,
                component_id=render_id,
                context_data=cast(Dict, context_data),
                js_data=cast(Dict, js_data),
                css_data=cast(Dict, css_data),
            )
        )

        # Process Component's JS and CSS
        cache_component_js(self.__class__)
        js_input_hash = cache_component_js_vars(self.__class__, js_data) if js_data else None

        cache_component_css(self.__class__)
        css_input_hash = cache_component_css_vars(self.__class__, css_data) if css_data else None

        with _prepare_template(self, context, context_data, metadata) as template:
            component_ctx.template_name = template.name

            # For users, we expose boolean variables that they may check
            # to see if given slot was filled, e.g.:
            # `{% if variable > 8 and component_vars.is_filled.header %}`
            is_filled = SlotIsFilled(slots_untyped)
            metadata.is_filled = is_filled

            with context.update(
                {
                    # Make data from context processors available inside templates
                    **context_processors_data,
                    # Private context fields
                    _COMPONENT_CONTEXT_KEY: render_id,
                    # NOTE: Public API for variables accessible from within a component's template
                    # See https://github.com/django-components/django-components/issues/280#issuecomment-2081180940
                    "component_vars": ComponentVars(
                        is_filled=is_filled,
                    ),
                }
            ):
                # Make a "snapshot" of the context as it was at the time of the render call.
                #
                # Previously, we recursively called `Template.render()` as this point, but due to recursion
                # this was limiting the number of nested components to only about 60 levels deep.
                #
                # Now, we make a flat copy, so that the context copy is static and doesn't change even if
                # we leave the `with context.update` blocks.
                #
                # This makes it possible to render nested components with a queue, avoiding recursion limits.
                context_snapshot = snapshot_context(context)

        # Cleanup
        context.render_context.pop()

        # Instead of rendering component at the time we come across the `{% component %}` tag
        # in the template, we defer rendering in order to scalably handle deeply nested components.
        #
        # See `_gen_component_renderer()` for more details.
        deferred_render = self._gen_component_renderer(
            render_id=render_id,
            template=template,
            context=context_snapshot,
            metadata=metadata,
            component_path=component_path,
            css_input_hash=css_input_hash,
            js_input_hash=js_input_hash,
            css_scope_id=None,  # TODO - Implement CSS scoping
        )

        # Remove component from caches
        def on_component_rendered(html: str) -> str:
            with self._with_metadata(metadata):
                # Allow to optionally override/modify the rendered content
                new_output = self.on_render_after(context_snapshot, template, html)
                html = new_output if new_output is not None else html

            del component_context_cache[render_id]  # type: ignore[arg-type]
            unregister_provide_reference(render_id)  # type: ignore[arg-type]

            if app_settings.DEBUG_HIGHLIGHT_COMPONENTS:
                html = apply_component_highlight("component", html, f"{self.name} ({render_id})")

            return html

        post_render_callbacks[render_id] = on_component_rendered

        # After the component and all its children are rendered, we resolve
        # all inserted HTML comments into <script> and <link> tags (if render_dependencies=True)
        def on_html_rendered(html: str) -> str:
            if render_dependencies:
                html = _render_dependencies(html, type)
            return html

        trace_component_msg(
            "COMP_PREP_END",
            component_name=self.name,
            component_id=render_id,
            slot_name=None,
            component_path=component_path,
        )

        return component_post_render(
            renderer=deferred_render,
            render_id=render_id,
            component_name=self.name,
            parent_id=parent_id,
            on_component_rendered_callbacks=post_render_callbacks,
            on_html_rendered=on_html_rendered,
        )

    # Creates a renderer function that will be called only once, when the component is to be rendered.
    #
    # By encapsulating components' output as render function, we can render components top-down,
    # starting from root component, and moving down.
    #
    # This way, when it comes to rendering a particular component, we have already rendered its parent,
    # and we KNOW if there were any HTML attributes that were passed from parent to children.
    #
    # Thus, the returned renderer function accepts the extra HTML attributes that were passed from parent,
    # and returns the updated HTML content.
    #
    # Because the HTML attributes are all boolean (e.g. `data-djc-id-a1b3c4`), they are passed as a list.
    #
    # This whole setup makes it possible for multiple components to resolve to the same HTML element.
    # E.g. if CompA renders CompB, and CompB renders a <div>, then the <div> element will have
    # IDs of both CompA and CompB.
    # ```html
    # <div djc-id-a1b3cf djc-id-f3d3cf>...</div>
    # ```
    def _gen_component_renderer(
        self,
        render_id: str,
        template: Template,
        context: Context,
        metadata: MetadataItem,
        component_path: List[str],
        css_input_hash: Optional[str],
        js_input_hash: Optional[str],
        css_scope_id: Optional[str],
    ) -> ComponentRenderer:
        component = self
        component_name = self.name
        component_cls = self.__class__

        def renderer(root_attributes: Optional[List[str]] = None) -> Tuple[str, Dict[str, List[str]]]:
            trace_component_msg(
                "COMP_RENDER_START",
                component_name=component_name,
                component_id=render_id,
                slot_name=None,
                component_path=component_path,
            )

            # Allow to access component input and metadata like component ID from within `on_render` hook
            with component._with_metadata(metadata):
                component.on_render_before(context, template)

                # Emit signal that the template is about to be rendered
                template_rendered.send(sender=template, template=template, context=context)
                # Get the component's HTML
                html_content = template.render(context)

            # Add necessary HTML attributes to work with JS and CSS variables
            updated_html, child_components = set_component_attrs_for_js_and_css(
                html_content=html_content,
                component_id=render_id,
                css_input_hash=css_input_hash,
                css_scope_id=css_scope_id,
                root_attributes=root_attributes,
            )

            # Prepend an HTML comment to instructs how and what JS and CSS scripts are associated with it.
            updated_html = insert_component_dependencies_comment(
                updated_html,
                component_cls=component_cls,
                component_id=render_id,
                js_input_hash=js_input_hash,
                css_input_hash=css_input_hash,
            )

            trace_component_msg(
                "COMP_RENDER_END",
                component_name=component_name,
                component_id=render_id,
                slot_name=None,
                component_path=component_path,
            )

            return updated_html, child_components

        return renderer

    def _normalize_slot_fills(
        self,
        fills: Mapping[SlotName, SlotContent],
        escape_content: bool = True,
    ) -> Dict[SlotName, Slot]:
        # Preprocess slots to escape content if `escape_content=True`
        norm_fills = {}

        # NOTE: `gen_escaped_content_func` is defined as a separate function, instead of being inlined within
        #       the forloop, because the value the forloop variable points to changes with each loop iteration.
        def gen_escaped_content_func(content: SlotFunc, slot_name: str) -> Slot:
            # Case: Already Slot, already escaped, and names tracing names assigned, so nothing to do.
            if isinstance(content, Slot) and content.escaped and content.slot_name and content.component_name:
                return content

            # Otherwise, we create a new instance of Slot, whether `content` was already Slot or not.
            # This is so that user can potentially define a single `Slot` and use it in multiple components.
            if not isinstance(content, Slot) or not content.escaped:

                def content_fn(ctx: Context, slot_data: Dict, slot_ref: SlotRef) -> SlotResult:
                    rendered = content(ctx, slot_data, slot_ref)
                    return conditional_escape(rendered) if escape_content else rendered

                content_func = cast(SlotFunc, content_fn)
            else:
                content_func = content.content_func

            # Populate potentially missing fields so we can trace the component and slot
            if isinstance(content, Slot):
                used_component_name = content.component_name or self.name
                used_slot_name = content.slot_name or slot_name
                used_nodelist = content.nodelist
            else:
                used_component_name = self.name
                used_slot_name = slot_name
                used_nodelist = None

            slot = Slot(
                content_func=content_func,
                component_name=used_component_name,
                slot_name=used_slot_name,
                nodelist=used_nodelist,
                escaped=True,
            )

            return slot

        for slot_name, content in fills.items():
            if content is None:
                continue
            elif not callable(content):
                slot = _nodelist_to_slot_render_func(
                    component_name=self.name,
                    slot_name=slot_name,
                    nodelist=NodeList([TextNode(conditional_escape(content) if escape_content else content)]),
                    data_var=None,
                    default_var=None,
                )
            else:
                slot = gen_escaped_content_func(content, slot_name)

            norm_fills[slot_name] = slot

        return norm_fills

    # #####################################
    # VALIDATION
    # #####################################

    def _get_types(self) -> Optional[Tuple[Any, Any, Any, Any, Any, Any]]:
        """
        Extract the types passed to the Component class.

        So if a component subclasses Component class like so

        ```py
        class MyComp(Component[MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData]):
            ...
        ```

        Then we want to extract the tuple (MyArgs, MyKwargs, MySlots, MyData, MyJsData, MyCssData).

        Returns `None` if types were not provided. That is, the class was subclassed
        as:

        ```py
        class MyComp(Component):
            ...
        ```
        """
        # For efficiency, the type extraction is done only once.
        # If `self._types` is `False`, that means that the types were not specified.
        # If `self._types` is `None`, then this is the first time running this method.
        # Otherwise, `self._types` should be a tuple of (Args, Kwargs, Data, Slots)
        if self._types == False:  # noqa: E712
            return None
        elif self._types:
            return self._types

        # Since a class can extend multiple classes, e.g.
        #
        # ```py
        # class MyClass(BaseOne, BaseTwo, ...):
        #     ...
        # ```
        #
        # Then we need to find the base class that is our `Component` class.
        #
        # NOTE: __orig_bases__ is a tuple of _GenericAlias
        # See https://github.com/python/cpython/blob/709ef004dffe9cee2a023a3c8032d4ce80513582/Lib/typing.py#L1244
        # And https://github.com/python/cpython/issues/101688
        generics_bases: Tuple[Any, ...] = self.__orig_bases__  # type: ignore[attr-defined]
        component_generics_base = None
        for base in generics_bases:
            origin_cls = base.__origin__
            if origin_cls == Component or issubclass(origin_cls, Component):
                component_generics_base = base
                break

        if not component_generics_base:
            # If we get here, it means that the Component class wasn't supplied any generics
            self._types = False
            return None

        # If we got here, then we've found ourselves the typed Component class, e.g.
        #
        # `Component(Tuple[int], MyKwargs, MySlots, Any, Any, Any)`
        #
        # By accessing the __args__, we access individual types between the brackets, so
        #
        # (Tuple[int], MyKwargs, MySlots, Any, Any, Any)
        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = component_generics_base.__args__

        self._types = args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type
        return self._types

    def _validate_inputs(self, args: Tuple, kwargs: Any, slots: Any) -> None:
        maybe_inputs = self._get_types()
        if maybe_inputs is None:
            return
        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = maybe_inputs

        # Validate args
        validate_typed_tuple(args, args_type, f"Component '{self.name}'", "positional argument")
        # Validate kwargs
        validate_typed_dict(kwargs, kwargs_type, f"Component '{self.name}'", "keyword argument")
        # Validate slots
        validate_typed_dict(slots, slots_type, f"Component '{self.name}'", "slot")

    def _validate_outputs(self, data: Any) -> None:
        maybe_inputs = self._get_types()
        if maybe_inputs is None:
            return
        args_type, kwargs_type, slots_type, data_type, js_data_type, css_data_type = maybe_inputs

        # Validate data
        validate_typed_dict(data, data_type, f"Component '{self.name}'", "data")


# Perf
# Each component may use different start and end tags. We represent this
# as individual subclasses of `ComponentNode`. However, multiple components
# may use the same start & end tag combination, e.g. `{% component %}` and `{% endcomponent %}`.
# So we cache the already-created subclasses to be reused.
component_node_subclasses_by_name: Dict[str, Tuple[Type["ComponentNode"], ComponentRegistry]] = {}


class ComponentNode(BaseNode):
    """
    Renders one of the components that was previously registered with
    [`@register()`](./api.md#django_components.register)
    decorator.

    **Args:**

    - `name` (str, required): Registered name of the component to render
    - All other args and kwargs are defined based on the component itself.

    If you defined a component `"my_table"`

    ```python
    from django_component import Component, register

    @register("my_table")
    class MyTable(Component):
        template = \"\"\"
          <table>
            <thead>
              {% for header in headers %}
                <th>{{ header }}</th>
              {% endfor %}
            </thead>
            <tbody>
              {% for row in rows %}
                <tr>
                  {% for cell in row %}
                    <td>{{ cell }}</td>
                  {% endfor %}
                </tr>
              {% endfor %}
            <tbody>
          </table>
        \"\"\"

        def get_context_data(self, rows: List, headers: List):
            return {
                "rows": rows,
                "headers": headers,
            }
    ```

    Then you can render this component by referring to `MyTable` via its
    registered name `"my_table"`:

    ```django
    {% component "my_table" rows=rows headers=headers ... / %}
    ```

    ### Component input

    Positional and keyword arguments can be literals or template variables.

    The component name must be a single- or double-quotes string and must
    be either:

    - The first positional argument after `component`:

        ```django
        {% component "my_table" rows=rows headers=headers ... / %}
        ```

    - Passed as kwarg `name`:

        ```django
        {% component rows=rows headers=headers name="my_table" ... / %}
        ```

    ### Inserting into slots

    If the component defined any [slots](../concepts/fundamentals/slots.md), you can
    pass in the content to be placed inside those slots by inserting [`{% fill %}`](#fill) tags,
    directly within the `{% component %}` tag:

    ```django
    {% component "my_table" rows=rows headers=headers ... / %}
      {% fill "pagination" %}
        < 1 | 2 | 3 >
      {% endfill %}
    {% endcomponent %}
    ```

    ### Isolating components

    By default, components behave similarly to Django's
    [`{% include %}`](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#include),
    and the template inside the component has access to the variables defined in the outer template.

    You can selectively isolate a component, using the `only` flag, so that the inner template
    can access only the data that was explicitly passed to it:

    ```django
    {% component "name" positional_arg keyword_arg=value ... only %}
    ```
    """

    tag = "component"
    end_tag = "endcomponent"
    allowed_flags = [COMP_ONLY_FLAG]

    def __init__(
        self,
        # ComponentNode inputs
        name: str,
        registry: ComponentRegistry,  # noqa F811
        # BaseNode inputs
        params: List[TagAttr],
        flags: Optional[Dict[str, bool]] = None,
        nodelist: Optional[NodeList] = None,
        node_id: Optional[str] = None,
    ) -> None:
        super().__init__(params=params, flags=flags, nodelist=nodelist, node_id=node_id)

        self.name = name
        self.registry = registry

    @classmethod
    def parse(  # type: ignore[override]
        cls,
        parser: Parser,
        token: Token,
        registry: ComponentRegistry,  # noqa F811
        name: str,
        start_tag: str,
        end_tag: str,
    ) -> "ComponentNode":
        # Set the component-specific start and end tags by subclassing the BaseNode
        subcls_name = cls.__name__ + "_" + name

        # We try to reuse the same subclass for the same start tag, so we can
        # avoid creating a new subclass for each time `{% component %}` is called.
        if start_tag not in component_node_subclasses_by_name:
            subcls: Type[ComponentNode] = type(subcls_name, (cls,), {"tag": start_tag, "end_tag": end_tag})
            component_node_subclasses_by_name[start_tag] = (subcls, registry)

            # Remove the cache entry when either the registry or the component are deleted
            finalize(subcls, lambda: component_node_subclasses_by_name.pop(start_tag, None))
            finalize(registry, lambda: component_node_subclasses_by_name.pop(start_tag, None))

        cached_subcls, cached_registry = component_node_subclasses_by_name[start_tag]

        if cached_registry is not registry:
            raise RuntimeError(
                f"Detected two Components from different registries using the same start tag '{start_tag}'"
            )
        elif cached_subcls.end_tag != end_tag:
            raise RuntimeError(
                f"Detected two Components using the same start tag '{start_tag}' but with different end tags"
            )

        # Call `BaseNode.parse()` as if with the context of subcls.
        node: ComponentNode = super(cls, cached_subcls).parse(  # type: ignore[attr-defined]
            parser,
            token,
            registry=cached_registry,
            name=name,
        )
        return node

    def render(self, context: Context, *args: Any, **kwargs: Any) -> str:
        # Do not render nested `{% component %}` tags in other `{% component %}` tags
        # at the stage when we are determining if the latter has named fills or not.
        if _is_extracting_fill(context):
            return ""

        component_cls: Type[Component] = self.registry.get(self.name)

        slot_fills = resolve_fills(context, self.nodelist, self.name)

        component: Component = component_cls(
            registered_name=self.name,
            outer_context=context,
            registry=self.registry,
        )

        # Prevent outer context from leaking into the template of the component
        if self.flags[COMP_ONLY_FLAG] or self.registry.settings.context_behavior == ContextBehavior.ISOLATED:
            context = make_isolated_context_copy(context)

        output = component._render(
            context=context,
            args=args,
            kwargs=kwargs,
            slots=slot_fills,
            # NOTE: When we render components inside the template via template tags,
            # do NOT render deps, because this may be decided by outer component
            render_dependencies=False,
        )

        return output


@contextmanager
def _maybe_bind_template(context: Context, template: Template) -> Generator[None, Any, None]:
    if context.template is None:
        with context.bind_template(template):
            yield
    else:
        yield


@contextmanager
def _prepare_template(
    component: Component,
    context: Context,
    context_data: Any,
    metadata: MetadataItem,
) -> Generator[Template, Any, None]:
    with context.update(context_data):
        # Associate the newly-created Context with a Template, otherwise we get
        # an error when we try to use `{% include %}` tag inside the template?
        # See https://github.com/django-components/django-components/issues/580
        # And https://github.com/django-components/django-components/issues/634
        with component._with_metadata(metadata):
            template = component._get_template(context, component_id=metadata.render_id)

        if not is_template_cls_patched(template):
            raise RuntimeError(
                "Django-components received a Template instance which was not patched."
                "If you are using Django's Template class, check if you added django-components"
                "to INSTALLED_APPS. If you are using a custom template class, then you need to"
                "manually patch the class."
            )

        # Set `Template._djc_is_component_nested` based on whether we're currently INSIDE
        # the `{% extends %}` tag.
        # Part of fix for https://github.com/django-components/django-components/issues/508
        # See django_monkeypatch.py
        template._djc_is_component_nested = bool(context.render_context.get(BLOCK_CONTEXT_KEY))

        with _maybe_bind_template(context, template):
            yield template
