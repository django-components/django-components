import sys
from dataclasses import dataclass
from types import MethodType
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from weakref import ReferenceType, WeakValueDictionary, finalize

from django.forms.widgets import Media as MediaCls
from django.http import HttpRequest, HttpResponse
from django.template.base import NodeList, Parser, Template, Token
from django.template.context import Context, RequestContext
from django.template.loader_tags import BLOCK_CONTEXT_KEY, BlockContext
from django.test.signals import template_rendered
from django.views import View

from django_components.app_settings import ContextBehavior
from django_components.component_media import ComponentMediaInput, ComponentMediaMeta
from django_components.component_registry import ComponentRegistry
from django_components.component_registry import registry as registry_
from django_components.constants import COMP_ID_PREFIX
from django_components.context import _COMPONENT_CONTEXT_KEY, make_isolated_context_copy
from django_components.dependencies import (
    DependenciesStrategy,
    cache_component_css,
    cache_component_css_vars,
    cache_component_js,
    cache_component_js_vars,
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
    OnComponentRenderedContext,
    extensions,
)
from django_components.extensions.cache import ComponentCache
from django_components.extensions.debug_highlight import ComponentDebugHighlight
from django_components.extensions.defaults import ComponentDefaults
from django_components.extensions.view import ComponentView, ViewFn
from django_components.node import BaseNode
from django_components.perfutil.component import ComponentRenderer, component_context_cache, component_post_render
from django_components.perfutil.provide import register_provide_reference, unregister_provide_reference
from django_components.provide import get_injected_context_var
from django_components.slots import (
    Slot,
    SlotIsFilled,
    SlotName,
    SlotResult,
    _is_extracting_fill,
    normalize_slot_fills,
    resolve_fills,
)
from django_components.template import cache_component_template_file, prepare_component_template
from django_components.util.context import gen_context_processors_data, snapshot_context
from django_components.util.exception import component_error_message
from django_components.util.logger import trace_component_msg
from django_components.util.misc import default, gen_id, hash_comp_cls, to_dict
from django_components.util.template_tag import TagAttr
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


# NOTE: `ReferenceType` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    AllComponents = List[ReferenceType[Type["Component"]]]
    CompHashMapping = WeakValueDictionary[str, Type["Component"]]
else:
    AllComponents = List[ReferenceType]
    CompHashMapping = WeakValueDictionary


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


# NOTE: Initially, we fetched components by their registered name, but that didn't work
# for multiple registries and unregistered components.
#
# To have unique identifiers that works across registries, we rely
# on component class' module import path (e.g. `path.to.my.MyComponent`).
#
# But we also don't want to expose the module import paths to the outside world, as
# that information could be potentially exploited. So, instead, each component is
# associated with a hash that's derived from its module import path, ensuring uniqueness,
# consistency and privacy.
#
# E.g. `path.to.my.secret.MyComponent` -> `ab01f32`
#
# For easier debugging, we then prepend the hash with the component class name, so that
# we can easily identify the component class by its hash.
#
# E.g. `path.to.my.secret.MyComponent` -> `MyComponent_ab01f32`
#
# The associations are defined as WeakValue map, so deleted components can be garbage
# collected and automatically deleted from the dict.
comp_cls_id_mapping: CompHashMapping = WeakValueDictionary()


def get_component_by_class_id(comp_cls_id: str) -> Type["Component"]:
    """
    Get a component class by its unique ID.

    Each component class is associated with a unique hash that's derived from its module import path.

    E.g. `path.to.my.secret.MyComponent` -> `MyComponent_ab01f32`

    This hash is available under [`class_id`](../api#django_components.Component.class_id)
    on the component class.

    Raises `KeyError` if the component class is not found.

    NOTE: This is mainly intended for extensions.
    """
    return comp_cls_id_mapping[comp_cls_id]


@dataclass(frozen=True)
class ComponentInput:
    """
    Object holding the inputs that were passed to [`Component.render()`](../api#django_components.Component.render)
    or the [`{% component %}`](../template_tags#component) template tag.

    This object is available only during render under [`Component.input`](../api#django_components.Component.input).

    Read more about the [Render API](../../concepts/fundamentals/render_api).
    """

    context: Context
    """
    Django's [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
    passed to `Component.render()`
    """
    args: List
    """Positional arguments (as list) passed to `Component.render()`"""
    kwargs: Dict
    """Keyword arguments (as dict) passed to `Component.render()`"""
    slots: Dict[SlotName, Slot]
    """Slots (as dict) passed to `Component.render()`"""
    deps_strategy: DependenciesStrategy
    """Dependencies strategy passed to `Component.render()`"""
    # TODO_v1 - Remove, superseded by `deps_strategy`
    type: DependenciesStrategy
    """Deprecated. Will be removed in v1. Use `deps_strategy` instead."""
    # TODO_v1 - Remove, superseded by `deps_strategy`
    render_dependencies: bool
    """Deprecated. Will be removed in v1. Use `deps_strategy="ignore"` instead."""


class ComponentVars(NamedTuple):
    """
    Type for the variables available inside the component templates.

    All variables here are scoped under `component_vars.`, so e.g. attribute
    `kwargs` on this class is accessible inside the template as:

    ```django
    {{ component_vars.kwargs }}
    ```
    """

    args: Any
    """
    The `args` argument as passed to
    [`Component.get_template_data()`](../api/#django_components.Component.get_template_data).

    This is the same [`Component.args`](../api/#django_components.Component.args)
    that's available on the component instance.

    If you defined the [`Component.Args`](../api/#django_components.Component.Args) class,
    then the `args` property will return an instance of that class.

    Otherwise, `args` will be a plain list.

    **Example:**

    With `Args` class:

    ```djc_py
    from django_components import Component, register

    @register("table")
    class Table(Component):
        class Args(NamedTuple):
            page: int
            per_page: int

        template = '''
            <div>
                <h1>Table</h1>
                <p>Page: {{ component_vars.args.page }}</p>
                <p>Per page: {{ component_vars.args.per_page }}</p>
            </div>
        '''
    ```

    Without `Args` class:

    ```djc_py
    from django_components import Component, register

    @register("table")
    class Table(Component):
        template = '''
            <div>
                <h1>Table</h1>
                <p>Page: {{ component_vars.args.0 }}</p>
                <p>Per page: {{ component_vars.args.1 }}</p>
            </div>
        '''
    ```
    """

    kwargs: Any
    """
    The `kwargs` argument as passed to
    [`Component.get_template_data()`](../api/#django_components.Component.get_template_data).

    This is the same [`Component.kwargs`](../api/#django_components.Component.kwargs)
    that's available on the component instance.

    If you defined the [`Component.Kwargs`](../api/#django_components.Component.Kwargs) class,
    then the `kwargs` property will return an instance of that class.

    Otherwise, `kwargs` will be a plain dict.

    **Example:**

    With `Kwargs` class:

    ```djc_py
    from django_components import Component, register

    @register("table")
    class Table(Component):
        class Kwargs(NamedTuple):
            page: int
            per_page: int

        template = '''
            <div>
                <h1>Table</h1>
                <p>Page: {{ component_vars.kwargs.page }}</p>
                <p>Per page: {{ component_vars.kwargs.per_page }}</p>
            </div>
        '''
    ```

    Without `Kwargs` class:

    ```djc_py
    from django_components import Component, register

    @register("table")
    class Table(Component):
        template = '''
            <div>
                <h1>Table</h1>
                <p>Page: {{ component_vars.kwargs.page }}</p>
                <p>Per page: {{ component_vars.kwargs.per_page }}</p>
            </div>
        '''
    ```
    """

    slots: Any
    """
    The `slots` argument as passed to
    [`Component.get_template_data()`](../api/#django_components.Component.get_template_data).

    This is the same [`Component.slots`](../api/#django_components.Component.slots)
    that's available on the component instance.

    If you defined the [`Component.Slots`](../api/#django_components.Component.Slots) class,
    then the `slots` property will return an instance of that class.

    Otherwise, `slots` will be a plain dict.

    **Example:**

    With `Slots` class:

    ```djc_py
    from django_components import Component, SlotInput, register

    @register("table")
    class Table(Component):
        class Slots(NamedTuple):
            footer: SlotInput

        template = '''
            <div>
                {% component "pagination" %}
                    {% fill "footer" body=component_vars.slots.footer / %}
                {% endcomponent %}
            </div>
        '''
    ```

    Without `Slots` class:

    ```djc_py
    from django_components import Component, SlotInput, register

    @register("table")
    class Table(Component):
        template = '''
            <div>
                {% component "pagination" %}
                    {% fill "footer" body=component_vars.slots.footer / %}
                {% endcomponent %}
            </div>
        '''
    ```
    """

    # TODO_v1 - Remove, superseded by `component_vars.slots`
    is_filled: Dict[str, bool]
    """
    Deprecated. Will be removed in v1. Use [`component_vars.slots`](../template_vars#django_components.component.ComponentVars.slots) instead.
    Note that `component_vars.slots` no longer escapes the slot names.

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
        def get_template_data(self, args, kwargs, slots, context):
            return {
                "my_slot_filled": "my_slot" in slots
            }
    ```
    """  # noqa: E501


def _gen_component_id() -> str:
    return COMP_ID_PREFIX + gen_id()


def _get_component_name(cls: Type["Component"], registered_name: Optional[str] = None) -> str:
    return default(registered_name, cls.__name__)


# Descriptor to pass getting/setting of `template_name` onto `template_file`
class ComponentTemplateNameDescriptor:
    def __get__(self, instance: Optional["Component"], cls: Type["Component"]) -> Any:
        obj = default(instance, cls)
        return obj.template_file  # type: ignore[attr-defined]

    def __set__(self, instance_or_cls: Union["Component", Type["Component"]], value: Any) -> None:
        cls = instance_or_cls if isinstance(instance_or_cls, type) else instance_or_cls.__class__
        cls.template_file = value


class ComponentMeta(ComponentMediaMeta):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict) -> Type:
        # If user set `template_name` on the class, we instead set it to `template_file`,
        # because we want `template_name` to be the descriptor that proxies to `template_file`.
        if "template_name" in attrs:
            attrs["template_file"] = attrs.pop("template_name")
        attrs["template_name"] = ComponentTemplateNameDescriptor()

        cls = super().__new__(mcs, name, bases, attrs)

        # If the component defined `template_file`, then associate this Component class
        # with that template file path.
        # This way, when we will be instantiating `Template` in order to load the Component's template,
        # and its template_name matches this path, then we know that the template belongs to this Component class.
        if "template_file" in attrs and attrs["template_file"]:
            cache_component_template_file(cls)

        return cls

    # This runs when a Component class is being deleted
    def __del__(cls) -> None:
        # Skip if `extensions` was deleted before this registry
        if not extensions:
            return

        comp_cls = cast(Type["Component"], cls)
        extensions.on_component_class_deleted(OnComponentClassDeletedContext(comp_cls))


# Internal data that are made available within the component's template
@dataclass
class ComponentContext:
    component: "Component"
    component_path: List[str]
    template_name: Optional[str]
    default_slot: Optional[str]
    outer_context: Optional[Context]
    # When we render a component, the root component, together with all the nested Components,
    # shares this dictionary for storing callbacks that are called from within `component_post_render`.
    # This is so that we can pass them all in when the root component is passed to `component_post_render`.
    post_render_callbacks: Dict[str, Callable[[str], str]]


class Component(metaclass=ComponentMeta):
    # #####################################
    # PUBLIC API (Configurable by users)
    # #####################################

    Args: ClassVar[Optional[Type]] = None
    """
    Optional typing for positional arguments passed to the component.

    If set and not `None`, then the `args` parameter of the data methods
    ([`get_template_data()`](../api#django_components.Component.get_template_data),
    [`get_js_data()`](../api#django_components.Component.get_js_data),
    [`get_css_data()`](../api#django_components.Component.get_css_data))
    will be the instance of this class:

    ```py
    from typing import NamedTuple
    from django_components import Component

    class Table(Component):
        class Args(NamedTuple):
            color: str
            size: int

        def get_template_data(self, args: Args, kwargs, slots, context):
            assert isinstance(args, Table.Args)

            return {
                "color": args.color,
                "size": args.size,
            }
    ```

    The constructor of this class MUST accept positional arguments:

    ```py
    Args(*args)
    ```

    As such, a good starting point is to set this field to a subclass of
    [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple).

    Use `Args` to:

    - Validate the input at runtime.
    - Set type hints for the positional arguments for data methods like
      [`get_template_data()`](../api#django_components.Component.get_template_data).
    - Document the component inputs.

    You can also use `Args` to validate the positional arguments for
    [`Component.render()`](../api#django_components.Component.render):

    ```py
    Table.render(
        args=Table.Args(color="red", size=10),
    )
    ```

    Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).
    """

    Kwargs: ClassVar[Optional[Type]] = None
    """
    Optional typing for keyword arguments passed to the component.

    If set and not `None`, then the `kwargs` parameter of the data methods
    ([`get_template_data()`](../api#django_components.Component.get_template_data),
    [`get_js_data()`](../api#django_components.Component.get_js_data),
    [`get_css_data()`](../api#django_components.Component.get_css_data))
    will be the instance of this class:

    ```py
    from typing import NamedTuple
    from django_components import Component

    class Table(Component):
        class Kwargs(NamedTuple):
            color: str
            size: int

        def get_template_data(self, args, kwargs: Kwargs, slots, context):
            assert isinstance(kwargs, Table.Kwargs)

            return {
                "color": kwargs.color,
                "size": kwargs.size,
            }
    ```

    The constructor of this class MUST accept keyword arguments:

    ```py
    Kwargs(**kwargs)
    ```

    As such, a good starting point is to set this field to a subclass of
    [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
    or a [dataclass](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass).

    Use `Kwargs` to:

    - Validate the input at runtime.
    - Set type hints for the keyword arguments for data methods like
      [`get_template_data()`](../api#django_components.Component.get_template_data).
    - Document the component inputs.

    You can also use `Kwargs` to validate the keyword arguments for
    [`Component.render()`](../api#django_components.Component.render):

    ```py
    Table.render(
        kwargs=Table.Kwargs(color="red", size=10),
    )
    ```

    Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).
    """

    Slots: ClassVar[Optional[Type]] = None
    """
    Optional typing for slots passed to the component.

    If set and not `None`, then the `slots` parameter of the data methods
    ([`get_template_data()`](../api#django_components.Component.get_template_data),
    [`get_js_data()`](../api#django_components.Component.get_js_data),
    [`get_css_data()`](../api#django_components.Component.get_css_data))
    will be the instance of this class:

    ```py
    from typing import NamedTuple
    from django_components import Component, Slot, SlotInput

    class Table(Component):
        class Slots(NamedTuple):
            header: SlotInput
            footer: Slot

        def get_template_data(self, args, kwargs, slots: Slots, context):
            assert isinstance(slots, Table.Slots)

            return {
                "header": slots.header,
                "footer": slots.footer,
            }
    ```

    The constructor of this class MUST accept keyword arguments:

    ```py
    Slots(**slots)
    ```

    As such, a good starting point is to set this field to a subclass of
    [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
    or a [dataclass](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass).

    Use `Slots` to:

    - Validate the input at runtime.
    - Set type hints for the slots for data methods like
      [`get_template_data()`](../api#django_components.Component.get_template_data).
    - Document the component inputs.

    You can also use `Slots` to validate the slots for
    [`Component.render()`](../api#django_components.Component.render):

    ```py
    Table.render(
        slots=Table.Slots(
            header="HELLO IM HEADER",
            footer=Slot(lambda ctx: ...),
        ),
    )
    ```

    Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

    !!! info

        Components can receive slots as strings, functions, or instances of [`Slot`](../api#django_components.Slot).

        Internally these are all normalized to instances of [`Slot`](../api#django_components.Slot).

        Therefore, the `slots` dictionary available in data methods (like
        [`get_template_data()`](../api#django_components.Component.get_template_data))
        will always be a dictionary of [`Slot`](../api#django_components.Slot) instances.

        To correctly type this dictionary, you should set the fields of `Slots` to
        [`Slot`](../api#django_components.Slot) or [`SlotInput`](../api#django_components.SlotInput):

        [`SlotInput`](../api#django_components.SlotInput) is a union of `Slot`, string, and function types.
    """

    template_file: ClassVar[Optional[str]] = None
    """
    Filepath to the Django template associated with this component.

    The filepath must be either:

    - Relative to the directory where the Component's Python file is defined.
    - Relative to one of the component directories, as set by
      [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
      or
      [`COMPONENTS.app_dirs`](../settings#django_components.app_settings.ComponentsSettings.app_dirs)
      (e.g. `<root>/components/`).
    - Relative to the template directories, as set by Django's `TEMPLATES` setting (e.g. `<root>/templates/`).

    !!! warning

        Only one of [`template_file`](../api#django_components.Component.template_file),
        [`get_template_name`](../api#django_components.Component.get_template_name),
        [`template`](../api#django_components.Component.template)
        or [`get_template`](../api#django_components.Component.get_template) must be defined.

    **Example:**

    Assuming this project layout:

    ```txt
    |- components/
      |- table/
        |- table.html
        |- table.css
        |- table.js
    ```

    Template name can be either relative to the python file (`components/table/table.py`):

    ```python
    class Table(Component):
        template_file = "table.html"
    ```

    Or relative to one of the directories in
    [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
    or
    [`COMPONENTS.app_dirs`](../settings#django_components.app_settings.ComponentsSettings.app_dirs)
    (`components/`):

    ```python
    class Table(Component):
        template_file = "table/table.html"
    ```
    """

    # NOTE: This attribute is managed by `ComponentTemplateNameDescriptor` that's set in the metaclass.
    #       But we still define it here for documenting and type hinting.
    template_name: ClassVar[Optional[str]]
    """
    Alias for [`template_file`](../api#django_components.Component.template_file).

    For historical reasons, django-components used `template_name` to align with Django's
    [TemplateView](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/#django.views.generic.base.TemplateView).

    `template_file` was introduced to align with
    [`js`](../api#django_components.Component.js)/[`js_file`](../api#django_components.Component.js_file)
    and [`css`](../api#django_components.Component.css)/[`css_file`](../api#django_components.Component.css_file).

    Setting and accessing this attribute is proxied to
    [`template_file`](../api#django_components.Component.template_file).
    """

    # TODO_v1 - Remove
    def get_template_name(self, context: Context) -> Optional[str]:
        """
        DEPRECATED: Use instead [`Component.template_file`](../api#django_components.Component.template_file),
        [`Component.template`](../api#django_components.Component.template) or
        [`Component.on_render()`](../api#django_components.Component.on_render).
        Will be removed in v1.

        Same as [`Component.template_file`](../api#django_components.Component.template_file),
        but allows to dynamically resolve the template name at render time.

        See [`Component.template_file`](../api#django_components.Component.template_file)
        for more info and examples.

        !!! warning

            The context is not fully populated at the point when this method is called.

            If you need to access the context, either use
            [`Component.on_render_before()`](../api#django_components.Component.on_render_before) or
            [`Component.on_render()`](../api#django_components.Component.on_render).

        !!! warning

            Only one of
            [`template_file`](../api#django_components.Component.template_file),
            [`get_template_name()`](../api#django_components.Component.get_template_name),
            [`template`](../api#django_components.Component.template)
            or
            [`get_template()`](../api#django_components.Component.get_template)
            must be defined.

        Args:
            context (Context): The Django template\
                [`Context`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context)\
                in which the component is rendered.

        Returns:
            Optional[str]: The filepath to the template.
        """
        return None

    template: Optional[str] = None
    """
    Inlined Django template (as a plain string) associated with this component.

    !!! warning

        Only one of
        [`template_file`](../api#django_components.Component.template_file),
        [`template`](../api#django_components.Component.template),
        [`get_template_name()`](../api#django_components.Component.get_template_name),
        or
        [`get_template()`](../api#django_components.Component.get_template)
        must be defined.

    **Example:**

    ```python
    class Table(Component):
        template = '''
          <div>
            {{ my_var }}
          </div>
        '''
    ```

    **Syntax highlighting**

    When using the inlined template, you can enable syntax highlighting
    with `django_components.types.django_html`.

    Learn more about [syntax highlighting](../../concepts/fundamentals/single_file_components/#syntax-highlighting).

    ```djc_py
    from django_components import Component, types

    class MyComponent(Component):
        template: types.django_html = '''
          <div>
            {{ my_var }}
          </div>
        '''
    ```
    """

    # TODO_v1 - Remove
    def get_template(self, context: Context) -> Optional[Union[str, Template]]:
        """
        DEPRECATED: Use instead [`Component.template_file`](../api#django_components.Component.template_file),
        [`Component.template`](../api#django_components.Component.template) or
        [`Component.on_render()`](../api#django_components.Component.on_render).
        Will be removed in v1.

        Same as [`Component.template`](../api#django_components.Component.template),
        but allows to dynamically resolve the template at render time.

        The template can be either plain string or
        a [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template) instance.

        See [`Component.template`](../api#django_components.Component.template) for more info and examples.

        !!! warning

            Only one of
            [`template`](../api#django_components.Component.template)
            [`template_file`](../api#django_components.Component.template_file),
            [`get_template_name()`](../api#django_components.Component.get_template_name),
            or
            [`get_template()`](../api#django_components.Component.get_template)
            must be defined.

        !!! warning

            The context is not fully populated at the point when this method is called.

            If you need to access the context, either use
            [`Component.on_render_before()`](../api#django_components.Component.on_render_before) or
            [`Component.on_render()`](../api#django_components.Component.on_render).

        Args:
            context (Context): The Django template\
            [`Context`](https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context)\
            in which the component is rendered.

        Returns:
            Optional[Union[str, Template]]: The inlined Django template string or\
            a [`Template`](https://docs.djangoproject.com/en/5.1/topics/templates/#template) instance.
        """
        return None

    # TODO_V2 - Remove this in v2
    def get_context_data(self, *args: Any, **kwargs: Any) -> Optional[Mapping]:
        """
        DEPRECATED: Use [`get_template_data()`](../api#django_components.Component.get_template_data) instead.
        Will be removed in v2.

        Use this method to define variables that will be available in the template.

        Receives the args and kwargs as they were passed to the Component.

        This method has access to the [Render API](../../concepts/fundamentals/render_api).

        Read more about [Template variables](../../concepts/fundamentals/html_js_css_variables).

        **Example:**

        ```py
        class MyComponent(Component):
            def get_context_data(self, name, *args, **kwargs):
                return {
                    "name": name,
                    "id": self.id,
                }

            template = "Hello, {{ name }}!"

        MyComponent.render(name="World")
        ```

        !!! warning

            `get_context_data()` and [`get_template_data()`](../api#django_components.Component.get_template_data)
            are mutually exclusive.

            If both methods return non-empty dictionaries, an error will be raised.
        """
        return None

    def get_template_data(self, args: Any, kwargs: Any, slots: Any, context: Context) -> Optional[Mapping]:
        """
        Use this method to define variables that will be available in the template.

        This method has access to the [Render API](../../concepts/fundamentals/render_api).

        Read more about [Template variables](../../concepts/fundamentals/html_js_css_variables).

        **Example:**

        ```py
        class MyComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "name": kwargs["name"],
                    "id": self.id,
                }

            template = "Hello, {{ name }}!"

        MyComponent.render(name="World")
        ```

        **Args:**

        - `args`: Positional arguments passed to the component.
        - `kwargs`: Keyword arguments passed to the component.
        - `slots`: Slots passed to the component.
        - `context`: [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
           used for rendering the component template.

        **Pass-through kwargs:**

        It's best practice to explicitly define what args and kwargs a component accepts.

        However, if you want a looser setup, you can easily write components that accept any number
        of kwargs, and pass them all to the template
        (similar to [django-cotton](https://github.com/wrabit/django-cotton)).

        To do that, simply return the `kwargs` dictionary itself from `get_template_data()`:

        ```py
        class MyComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                return kwargs
        ```

        **Type hints:**

        To get type hints for the `args`, `kwargs`, and `slots` parameters,
        you can define the [`Args`](../api#django_components.Component.Args),
        [`Kwargs`](../api#django_components.Component.Kwargs), and
        [`Slots`](../api#django_components.Component.Slots) classes on the component class,
        and then directly reference them in the function signature of `get_template_data()`.

        When you set these classes, the `args`, `kwargs`, and `slots` parameters will be
        given as instances of these (`args` instance of `Args`, etc).

        When you omit these classes, or set them to `None`, then the `args`, `kwargs`, and `slots`
        parameters will be given as plain lists / dictionaries, unmodified.

        Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

        **Example:**

        ```py
        from typing import NamedTuple
        from django.template import Context
        from django_components import Component, SlotInput

        class MyComponent(Component):
            class Args(NamedTuple):
                color: str

            class Kwargs(NamedTuple):
                size: int

            class Slots(NamedTuple):
                footer: SlotInput

            def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                assert isinstance(args, MyComponent.Args)
                assert isinstance(kwargs, MyComponent.Kwargs)
                assert isinstance(slots, MyComponent.Slots)

                return {
                    "color": args.color,
                    "size": kwargs.size,
                    "id": self.id,
                }
        ```

        You can also add typing to the data returned from
        [`get_template_data()`](../api#django_components.Component.get_template_data)
        by defining the [`TemplateData`](../api#django_components.Component.TemplateData)
        class on the component class.

        When you set this class, you can return either the data as a plain dictionary,
        or an instance of [`TemplateData`](../api#django_components.Component.TemplateData).

        If you return plain dictionary, the data will be validated against the
        [`TemplateData`](../api#django_components.Component.TemplateData) class
        by instantiating it with the dictionary.

        **Example:**

        ```py
        class MyComponent(Component):
            class TemplateData(NamedTuple):
                color: str
                size: int

            def get_template_data(self, args, kwargs, slots, context):
                return {
                    "color": kwargs["color"],
                    "size": kwargs["size"],
                }
                # or
                return MyComponent.TemplateData(
                    color=kwargs["color"],
                    size=kwargs["size"],
                )
        ```

        !!! warning

            `get_template_data()` and [`get_context_data()`](../api#django_components.Component.get_context_data)
            are mutually exclusive.

            If both methods return non-empty dictionaries, an error will be raised.
        """
        return None

    TemplateData: ClassVar[Optional[Type]] = None
    """
    Optional typing for the data to be returned from
    [`get_template_data()`](../api#django_components.Component.get_template_data).

    If set and not `None`, then this class will be instantiated with the dictionary returned from
    [`get_template_data()`](../api#django_components.Component.get_template_data) to validate the data.

    The constructor of this class MUST accept keyword arguments:

    ```py
    TemplateData(**template_data)
    ```

    You can also return an instance of `TemplateData` directly from
    [`get_template_data()`](../api#django_components.Component.get_template_data)
    to get type hints:

    ```py
    from typing import NamedTuple
    from django_components import Component

    class Table(Component):
        class TemplateData(NamedTuple):
            color: str
            size: int

        def get_template_data(self, args, kwargs, slots, context):
            return Table.TemplateData(
                color=kwargs["color"],
                size=kwargs["size"],
            )
    ```

    A good starting point is to set this field to a subclass of
    [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
    or a [dataclass](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass).

    Use `TemplateData` to:

    - Validate the data returned from
      [`get_template_data()`](../api#django_components.Component.get_template_data) at runtime.
    - Set type hints for this data.
    - Document the component data.

    Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

    !!! info

        If you use a custom class for `TemplateData`, this class needs to be convertable to a dictionary.

        You can implement either:

        1. `_asdict()` method
            ```py
            class MyClass:
                def __init__(self):
                    self.x = 1
                    self.y = 2

                def _asdict(self):
                    return {'x': self.x, 'y': self.y}
            ```

        2. Or make the class dict-like with `__iter__()` and `__getitem__()`
            ```py
            class MyClass:
                def __init__(self):
                    self.x = 1
                    self.y = 2

                def __iter__(self):
                    return iter([('x', self.x), ('y', self.y)])

                def __getitem__(self, key):
                    return getattr(self, key)
            ```
    """

    js: Optional[str] = None
    """
    Main JS associated with this component inlined as string.

    !!! warning

        Only one of [`js`](../api#django_components.Component.js) or
        [`js_file`](../api#django_components.Component.js_file) must be defined.

    **Example:**

    ```py
    class MyComponent(Component):
        js = "console.log('Hello, World!');"
    ```

    **Syntax highlighting**

    When using the inlined template, you can enable syntax highlighting
    with `django_components.types.js`.

    Learn more about [syntax highlighting](../../concepts/fundamentals/single_file_components/#syntax-highlighting).

    ```djc_py
    from django_components import Component, types

    class MyComponent(Component):
        js: types.js = '''
          console.log('Hello, World!');
        '''
    ```
    """

    js_file: ClassVar[Optional[str]] = None
    """
    Main JS associated with this component as file path.

    The filepath must be either:

    - Relative to the directory where the Component's Python file is defined.
    - Relative to one of the component directories, as set by
      [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
      or
      [`COMPONENTS.app_dirs`](../settings#django_components.app_settings.ComponentsSettings.app_dirs)
      (e.g. `<root>/components/`).
    - Relative to the staticfiles directories, as set by Django's `STATICFILES_DIRS` setting (e.g. `<root>/static/`).

    When you create a Component class with `js_file`, these will happen:

    1. If the file path is relative to the directory where the component's Python file is,
       the path is resolved.
    2. The file is read and its contents is set to [`Component.js`](../api#django_components.Component.js).

    !!! warning

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

    def get_js_data(self, args: Any, kwargs: Any, slots: Any, context: Context) -> Optional[Mapping]:
        """
        Use this method to define variables that will be available from within the component's JavaScript code.

        This method has access to the [Render API](../../concepts/fundamentals/render_api).

        The data returned from this method will be serialized to JSON.

        Read more about [JavaScript variables](../../concepts/fundamentals/html_js_css_variables).

        **Example:**

        ```py
        class MyComponent(Component):
            def get_js_data(self, args, kwargs, slots, context):
                return {
                    "name": kwargs["name"],
                    "id": self.id,
                }

            js = '''
                $onLoad(({ name, id }) => {
                    console.log(name, id);
                });
            '''

        MyComponent.render(name="World")
        ```

        **Args:**

        - `args`: Positional arguments passed to the component.
        - `kwargs`: Keyword arguments passed to the component.
        - `slots`: Slots passed to the component.
        - `context`: [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
           used for rendering the component template.

        **Pass-through kwargs:**

        It's best practice to explicitly define what args and kwargs a component accepts.

        However, if you want a looser setup, you can easily write components that accept any number
        of kwargs, and pass them all to the JavaScript code.

        To do that, simply return the `kwargs` dictionary itself from `get_js_data()`:

        ```py
        class MyComponent(Component):
            def get_js_data(self, args, kwargs, slots, context):
                return kwargs
        ```

        **Type hints:**

        To get type hints for the `args`, `kwargs`, and `slots` parameters,
        you can define the [`Args`](../api#django_components.Component.Args),
        [`Kwargs`](../api#django_components.Component.Kwargs), and
        [`Slots`](../api#django_components.Component.Slots) classes on the component class,
        and then directly reference them in the function signature of `get_js_data()`.

        When you set these classes, the `args`, `kwargs`, and `slots` parameters will be
        given as instances of these (`args` instance of `Args`, etc).

        When you omit these classes, or set them to `None`, then the `args`, `kwargs`, and `slots`
        parameters will be given as plain lists / dictionaries, unmodified.

        Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

        **Example:**

        ```py
        from typing import NamedTuple
        from django.template import Context
        from django_components import Component, SlotInput

        class MyComponent(Component):
            class Args(NamedTuple):
                color: str

            class Kwargs(NamedTuple):
                size: int

            class Slots(NamedTuple):
                footer: SlotInput

            def get_js_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                assert isinstance(args, MyComponent.Args)
                assert isinstance(kwargs, MyComponent.Kwargs)
                assert isinstance(slots, MyComponent.Slots)

                return {
                    "color": args.color,
                    "size": kwargs.size,
                    "id": self.id,
                }
        ```

        You can also add typing to the data returned from
        [`get_js_data()`](../api#django_components.Component.get_js_data)
        by defining the [`JsData`](../api#django_components.Component.JsData)
        class on the component class.

        When you set this class, you can return either the data as a plain dictionary,
        or an instance of [`JsData`](../api#django_components.Component.JsData).

        If you return plain dictionary, the data will be validated against the
        [`JsData`](../api#django_components.Component.JsData) class
        by instantiating it with the dictionary.

        **Example:**

        ```py
        class MyComponent(Component):
            class JsData(NamedTuple):
                color: str
                size: int

            def get_js_data(self, args, kwargs, slots, context):
                return {
                    "color": kwargs["color"],
                    "size": kwargs["size"],
                }
                # or
                return MyComponent.JsData(
                    color=kwargs["color"],
                    size=kwargs["size"],
                )
        ```
        """
        return None

    JsData: ClassVar[Optional[Type]] = None
    """
    Optional typing for the data to be returned from
    [`get_js_data()`](../api#django_components.Component.get_js_data).

    If set and not `None`, then this class will be instantiated with the dictionary returned from
    [`get_js_data()`](../api#django_components.Component.get_js_data) to validate the data.

    The constructor of this class MUST accept keyword arguments:

    ```py
    JsData(**js_data)
    ```

    You can also return an instance of `JsData` directly from
    [`get_js_data()`](../api#django_components.Component.get_js_data)
    to get type hints:

    ```py
    from typing import NamedTuple
    from django_components import Component

    class Table(Component):
        class JsData(NamedTuple):
            color: str
            size: int

        def get_js_data(self, args, kwargs, slots, context):
            return Table.JsData(
                color=kwargs["color"],
                size=kwargs["size"],
            )
    ```

    A good starting point is to set this field to a subclass of
    [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
    or a [dataclass](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass).

    Use `JsData` to:

    - Validate the data returned from
      [`get_js_data()`](../api#django_components.Component.get_js_data) at runtime.
    - Set type hints for this data.
    - Document the component data.

    Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

    !!! info

        If you use a custom class for `JsData`, this class needs to be convertable to a dictionary.

        You can implement either:

        1. `_asdict()` method
            ```py
            class MyClass:
                def __init__(self):
                    self.x = 1
                    self.y = 2

                def _asdict(self):
                    return {'x': self.x, 'y': self.y}
            ```

        2. Or make the class dict-like with `__iter__()` and `__getitem__()`
            ```py
            class MyClass:
                def __init__(self):
                    self.x = 1
                    self.y = 2

                def __iter__(self):
                    return iter([('x', self.x), ('y', self.y)])

                def __getitem__(self, key):
                    return getattr(self, key)
            ```
    """

    css: Optional[str] = None
    """
    Main CSS associated with this component inlined as string.

    !!! warning

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

    **Syntax highlighting**

    When using the inlined template, you can enable syntax highlighting
    with `django_components.types.css`.

    Learn more about [syntax highlighting](../../concepts/fundamentals/single_file_components/#syntax-highlighting).

    ```djc_py
    from django_components import Component, types

    class MyComponent(Component):
        css: types.css = '''
          .my-class {
            color: red;
          }
        '''
    ```
    """

    css_file: ClassVar[Optional[str]] = None
    """
    Main CSS associated with this component as file path.

    The filepath must be either:

    - Relative to the directory where the Component's Python file is defined.
    - Relative to one of the component directories, as set by
      [`COMPONENTS.dirs`](../settings#django_components.app_settings.ComponentsSettings.dirs)
      or
      [`COMPONENTS.app_dirs`](../settings#django_components.app_settings.ComponentsSettings.app_dirs)
      (e.g. `<root>/components/`).
    - Relative to the staticfiles directories, as set by Django's `STATICFILES_DIRS` setting (e.g. `<root>/static/`).

    When you create a Component class with `css_file`, these will happen:

    1. If the file path is relative to the directory where the component's Python file is,
       the path is resolved.
    2. The file is read and its contents is set to [`Component.css`](../api#django_components.Component.css).

    !!! warning

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

    def get_css_data(self, args: Any, kwargs: Any, slots: Any, context: Context) -> Optional[Mapping]:
        """
        Use this method to define variables that will be available from within the component's CSS code.

        This method has access to the [Render API](../../concepts/fundamentals/render_api).

        The data returned from this method will be serialized to string.

        Read more about [CSS variables](../../concepts/fundamentals/html_js_css_variables).

        **Example:**

        ```py
        class MyComponent(Component):
            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "color": kwargs["color"],
                }

            css = '''
                .my-class {
                    color: var(--color);
                }
            '''

        MyComponent.render(color="red")
        ```

        **Args:**

        - `args`: Positional arguments passed to the component.
        - `kwargs`: Keyword arguments passed to the component.
        - `slots`: Slots passed to the component.
        - `context`: [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
           used for rendering the component template.

        **Pass-through kwargs:**

        It's best practice to explicitly define what args and kwargs a component accepts.

        However, if you want a looser setup, you can easily write components that accept any number
        of kwargs, and pass them all to the CSS code.

        To do that, simply return the `kwargs` dictionary itself from `get_css_data()`:

        ```py
        class MyComponent(Component):
            def get_css_data(self, args, kwargs, slots, context):
                return kwargs
        ```

        **Type hints:**

        To get type hints for the `args`, `kwargs`, and `slots` parameters,
        you can define the [`Args`](../api#django_components.Component.Args),
        [`Kwargs`](../api#django_components.Component.Kwargs), and
        [`Slots`](../api#django_components.Component.Slots) classes on the component class,
        and then directly reference them in the function signature of `get_css_data()`.

        When you set these classes, the `args`, `kwargs`, and `slots` parameters will be
        given as instances of these (`args` instance of `Args`, etc).

        When you omit these classes, or set them to `None`, then the `args`, `kwargs`, and `slots`
        parameters will be given as plain lists / dictionaries, unmodified.

        Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

        **Example:**

        ```py
        from typing import NamedTuple
        from django.template import Context
        from django_components import Component, SlotInput

        class MyComponent(Component):
            class Args(NamedTuple):
                color: str

            class Kwargs(NamedTuple):
                size: int

            class Slots(NamedTuple):
                footer: SlotInput

            def get_css_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                assert isinstance(args, MyComponent.Args)
                assert isinstance(kwargs, MyComponent.Kwargs)
                assert isinstance(slots, MyComponent.Slots)

                return {
                    "color": args.color,
                    "size": kwargs.size,
                }
        ```

        You can also add typing to the data returned from
        [`get_css_data()`](../api#django_components.Component.get_css_data)
        by defining the [`CssData`](../api#django_components.Component.CssData)
        class on the component class.

        When you set this class, you can return either the data as a plain dictionary,
        or an instance of [`CssData`](../api#django_components.Component.CssData).

        If you return plain dictionary, the data will be validated against the
        [`CssData`](../api#django_components.Component.CssData) class
        by instantiating it with the dictionary.

        **Example:**

        ```py
        class MyComponent(Component):
            class CssData(NamedTuple):
                color: str
                size: int

            def get_css_data(self, args, kwargs, slots, context):
                return {
                    "color": kwargs["color"],
                    "size": kwargs["size"],
                }
                # or
                return MyComponent.CssData(
                    color=kwargs["color"],
                    size=kwargs["size"],
                )
        ```
        """
        return None

    CssData: ClassVar[Optional[Type]] = None
    """
    Optional typing for the data to be returned from
    [`get_css_data()`](../api#django_components.Component.get_css_data).

    If set and not `None`, then this class will be instantiated with the dictionary returned from
    [`get_css_data()`](../api#django_components.Component.get_css_data) to validate the data.

    The constructor of this class MUST accept keyword arguments:

    ```py
    CssData(**css_data)
    ```

    You can also return an instance of `CssData` directly from
    [`get_css_data()`](../api#django_components.Component.get_css_data)
    to get type hints:

    ```py
    from typing import NamedTuple
    from django_components import Component

    class Table(Component):
        class CssData(NamedTuple):
            color: str
            size: int

        def get_css_data(self, args, kwargs, slots, context):
            return Table.CssData(
                color=kwargs["color"],
                size=kwargs["size"],
            )
    ```

    A good starting point is to set this field to a subclass of
    [`NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
    or a [dataclass](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass).

    Use `CssData` to:

    - Validate the data returned from
      [`get_css_data()`](../api#django_components.Component.get_css_data) at runtime.
    - Set type hints for this data.
    - Document the component data.

    Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

    !!! info

        If you use a custom class for `CssData`, this class needs to be convertable to a dictionary.

        You can implement either:

        1. `_asdict()` method
            ```py
            class MyClass:
                def __init__(self):
                    self.x = 1
                    self.y = 2

                def _asdict(self):
                    return {'x': self.x, 'y': self.y}
            ```

        2. Or make the class dict-like with `__iter__()` and `__getitem__()`
            ```py
            class MyClass:
                def __init__(self):
                    self.x = 1
                    self.y = 2

                def __iter__(self):
                    return iter([('x', self.x), ('y', self.y)])

                def __getitem__(self, key):
                    return getattr(self, key)
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

    media_class: ClassVar[Type[MediaCls]] = MediaCls
    """
    Set the [Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#assets-as-a-static-definition)
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

    Media: ClassVar[Optional[Type[ComponentMediaInput]]] = None
    """
    Defines JS and CSS media files associated with this component.

    This `Media` class behaves similarly to
    [Django's Media class](https://docs.djangoproject.com/en/5.2/topics/forms/media/#assets-as-a-static-definition):

    - Paths are generally handled as static file paths, and resolved URLs are rendered to HTML with
      `media_class.render_js()` or `media_class.render_css()`.
    - A path that starts with `http`, `https`, or `/` is considered a URL, skipping the static file resolution.
      This path is still rendered to HTML with `media_class.render_js()` or `media_class.render_css()`.
    - A `SafeString` (with `__html__` method) is considered an already-formatted HTML tag, skipping both static file
        resolution and rendering with `media_class.render_js()` or `media_class.render_css()`.
    - You can set [`extend`](../api#django_components.ComponentMediaInput.extend) to configure
      whether to inherit JS / CSS from parent components. See
      [Media inheritance](../../concepts/fundamentals/secondary_js_css_files/#media-inheritance).

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

    response_class: ClassVar[Type[HttpResponse]] = HttpResponse
    """
    This attribute configures what class is used to generate response from
    [`Component.render_to_response()`](../api/#django_components.Component.render_to_response).

    The response class should accept a string as the first argument.

    Defaults to
    [`django.http.HttpResponse`](https://docs.djangoproject.com/en/5.2/ref/request-response/#httpresponse-objects).

    **Example:**

    ```py
    from django.http import HttpResponse
    from django_components import Component

    class MyHttpResponse(HttpResponse):
        ...

    class MyComponent(Component):
        response_class = MyHttpResponse

    response = MyComponent.render_to_response()
    assert isinstance(response, MyHttpResponse)
    ```
    """

    # #####################################
    # PUBLIC API - HOOKS (Configurable by users)
    # #####################################

    def on_render_before(self, context: Context, template: Optional[Template]) -> None:
        """
        Hook that runs just before the component's template is rendered.

        You can use this hook to access or modify the context or the template.
        """
        pass

    def on_render_after(self, context: Context, template: Optional[Template], content: str) -> Optional[SlotResult]:
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
    # BUILT-IN EXTENSIONS
    # #####################################

    # NOTE: These are the classes and instances added by defaults extensions. These fields
    # are actually set at runtime, and so here they are only marked for typing.
    Cache: ClassVar[Type[ComponentCache]]
    """
    The fields of this class are used to configure the component caching.

    Read more about [Component caching](../../concepts/advanced/component_caching).

    **Example:**

    ```python
    from django_components import Component

    class MyComponent(Component):
        class Cache:
            enabled = True
            ttl = 60 * 60 * 24  # 1 day
            cache_name = "my_cache"
    ```
    """
    cache: ComponentCache
    """
    Instance of [`ComponentCache`](../api#django_components.ComponentCache) available at component render time.
    """
    Defaults: ClassVar[Type[ComponentDefaults]]
    """
    The fields of this class are used to set default values for the component's kwargs.

    Read more about [Component defaults](../../concepts/fundamentals/component_defaults).

    **Example:**

    ```python
    from django_components import Component, Default

    class MyComponent(Component):
        class Defaults:
            position = "left"
            selected_items = Default(lambda: [1, 2, 3])
    ```
    """
    defaults: ComponentDefaults
    """
    Instance of [`ComponentDefaults`](../api#django_components.ComponentDefaults) available at component render time.
    """
    View: ClassVar[Type[ComponentView]]
    """
    The fields of this class are used to configure the component views and URLs.

    This class is a subclass of
    [`django.views.View`](https://docs.djangoproject.com/en/5.2/ref/class-based-views/base/#view).
    The [`Component`](../api#django_components.Component) instance is available
    via `self.component`.

    Override the methods of this class to define the behavior of the component.

    Read more about [Component views and URLs](../../concepts/fundamentals/component_views_urls).

    **Example:**

    ```python
    class MyComponent(Component):
        class View:
            def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
                return HttpResponse("Hello, world!")
    ```
    """
    view: ComponentView
    """
    Instance of [`ComponentView`](../api#django_components.ComponentView) available at component render time.
    """
    DebugHighlight: ClassVar[Type[ComponentDebugHighlight]]
    """
    The fields of this class are used to configure the component debug highlighting.

    Read more about [Component debug highlighting](../../guides/other/troubleshooting#component-and-slot-highlighting).
    """
    debug_highlight: ComponentDebugHighlight

    # #####################################
    # MISC
    # #####################################

    class_id: ClassVar[str]
    """
    Unique ID of the component class, e.g. `MyComponent_ab01f2`.

    This is derived from the component class' module import path, e.g. `path.to.my.MyComponent`.
    """

    # TODO_V1 - Remove this in v1
    @property
    def _class_hash(self) -> str:
        """Deprecated. Use `Component.class_id` instead."""
        return self.class_id

    _template: Optional[Template] = None
    """
    Cached [`Template`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template)
    instance for the [`Component`](../api#django_components.Component),
    created from
    [`Component.template`](#django_components.Component.template) or
    [`Component.template_file`](#django_components.Component.template_file).
    """

    # TODO_v3 - Django-specific property to prevent calling the instance as a function.
    do_not_call_in_templates: ClassVar[bool] = True
    """
    Django special property to prevent calling the instance as a function
    inside Django templates.

    Read more about Django's
    [`do_not_call_in_templates`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#variables-and-lookups).
    """

    # TODO_v1 - Change params order to match `Component.render()`
    def __init__(
        self,
        registered_name: Optional[str] = None,
        outer_context: Optional[Context] = None,
        registry: Optional[ComponentRegistry] = None,  # noqa F811
        context: Optional[Context] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        slots: Optional[Any] = None,
        deps_strategy: Optional[DependenciesStrategy] = None,
        request: Optional[HttpRequest] = None,
        id: Optional[str] = None,
    ):
        # TODO_v1 - Remove this whole block in v1. This is for backwards compatibility with pre-v0.140
        #           where one could do:
        #           `MyComp("my_comp").render(kwargs={"a": 1})`.
        #           Instead, the new syntax is:
        #           `MyComp.render(registered_name="my_comp", kwargs={"a": 1})`.
        # NOTE: We check for `id` as a proxy to decide if the component was instantiated by django-components
        #       or by the user. The `id` is set when a Component is instantiated from within `Component.render()`.
        if id is None:
            # Update the `render()` and `render_to_response()` methods to so they use the `registered_name`,
            # `outer_context`, and `registry` as passed to the constructor.
            #
            # To achieve that, we want to re-assign the class methods as instance methods that pass the instance
            # attributes to the class methods.
            # For that we have to "unwrap" the class methods via __func__.
            # See https://stackoverflow.com/a/76706399/9788634
            def primed_render(self: Component, *args: Any, **kwargs: Any) -> Any:
                return self.__class__.render(
                    *args,
                    **{
                        "registered_name": registered_name,
                        "outer_context": outer_context,
                        "registry": registry,
                        **kwargs,
                    },
                )

            def primed_render_to_response(self: Component, *args: Any, **kwargs: Any) -> Any:
                return self.__class__.render_to_response(
                    *args,
                    **{
                        "registered_name": registered_name,
                        "outer_context": outer_context,
                        "registry": registry,
                        **kwargs,
                    },
                )

            self.render_to_response = MethodType(primed_render_to_response, self)  # type: ignore
            self.render = MethodType(primed_render, self)  # type: ignore

        deps_strategy = cast(DependenciesStrategy, default(deps_strategy, "document"))

        self.id = default(id, _gen_component_id, factory=True)
        self.name = _get_component_name(self.__class__, registered_name)
        self.registered_name: Optional[str] = registered_name
        self.args = default(args, [])
        self.kwargs = default(kwargs, {})
        self.slots = default(slots, {})
        self.context = default(context, Context())
        # TODO_v1 - Remove `is_filled`, superseded by `Component.slots`
        self.is_filled = SlotIsFilled(to_dict(self.slots))
        self.input = ComponentInput(
            context=self.context,
            # NOTE: Convert args / kwargs / slots to plain lists / dicts
            args=cast(List, args if isinstance(self.args, list) else list(self.args)),
            kwargs=cast(Dict, kwargs if isinstance(self.kwargs, dict) else to_dict(self.kwargs)),
            slots=cast(Dict, slots if isinstance(self.slots, dict) else to_dict(self.slots)),
            deps_strategy=deps_strategy,
            # TODO_v1 - Remove, superseded by `deps_strategy`
            type=deps_strategy,
            # TODO_v1 - Remove, superseded by `deps_strategy`
            render_dependencies=deps_strategy != "ignore",
        )
        self.request = request
        self.outer_context: Optional[Context] = outer_context
        self.registry = default(registry, registry_)

        extensions._init_component_instance(self)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls.class_id = hash_comp_cls(cls)
        comp_cls_id_mapping[cls.class_id] = cls

        # Make sure that subclassed component will store it's own template, not the parent's.
        cls._template = None

        ALL_COMPONENTS.append(cached_ref(cls))  # type: ignore[arg-type]
        extensions._init_component_class(cls)
        extensions.on_component_class_created(OnComponentClassCreatedContext(cls))

    ########################################
    # INSTANCE PROPERTIES
    ########################################

    name: str
    """
    The name of the component.

    If the component was registered, this will be the name under which the component was registered in
    the [`ComponentRegistry`](../api#django_components.ComponentRegistry).

    Otherwise, this will be the name of the class.

    **Example:**

    ```py
    @register("my_component")
    class RegisteredComponent(Component):
        def get_template_data(self, args, kwargs, slots, context):
            return {
                "name": self.name,  # "my_component"
            }

    class UnregisteredComponent(Component):
        def get_template_data(self, args, kwargs, slots, context):
            return {
                "name": self.name,  # "UnregisteredComponent"
            }
    ```
    """

    registered_name: Optional[str]
    """
    If the component was rendered with the [`{% component %}`](../template_tags#component) template tag,
    this will be the name under which the component was registered in
    the [`ComponentRegistry`](../api#django_components.ComponentRegistry).

    Otherwise, this will be `None`.

    **Example:**

    ```py
    @register("my_component")
    class MyComponent(Component):
        template = "{{ name }}"

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "name": self.registered_name,
            }
    ```

    Will print `my_component` in the template:

    ```django
    {% component "my_component" / %}
    ```

    And `None` when rendered in Python:

    ```python
    MyComponent.render()
    # None
    ```
    """

    id: str
    """
    This ID is unique for every time a [`Component.render()`](../api#django_components.Component.render)
    (or equivalent) is called (AKA "render ID").

    This is useful for logging or debugging.

    The ID is a 7-letter alphanumeric string in the format `cXXXXXX`,
    where `XXXXXX` is a random string of 6 alphanumeric characters (case-sensitive).

    E.g. `c1A2b3c`.

    A single render ID has a chance of collision 1 in 57 billion. However, due to birthday paradox,
    the chance of collision increases to 1% when approaching ~33K render IDs.

    Thus, there is currently a soft-cap of ~30K components rendered on a single page.

    If you need to expand this limit, please open an issue on GitHub.

    **Example:**

    ```py
    class MyComponent(Component):
        def get_template_data(self, args, kwargs, slots, context):
            print(f"Rendering '{self.id}'")

    MyComponent.render()
    # Rendering 'ab3c4d'
    ```
    """

    input: ComponentInput
    """
    Input holds the data that were passed to the current component at render time.

    This includes:

    - [`args`](../api/#django_components.ComponentInput.args) - List of positional arguments
    - [`kwargs`](../api/#django_components.ComponentInput.kwargs) - Dictionary of keyword arguments
    - [`slots`](../api/#django_components.ComponentInput.slots) - Dictionary of slots. Values are normalized to
        [`Slot`](../api/#django_components.Slot) instances
    - [`context`](../api/#django_components.ComponentInput.context) -
        [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
        object that should be used to render the component
    - And other kwargs passed to [`Component.render()`](../api/#django_components.Component.render)
        like `deps_strategy`

    Read more on [Component inputs](../../concepts/fundamentals/render_api/#other-inputs).

    **Example:**

    ```python
    class Table(Component):
        def get_template_data(self, args, kwargs, slots, context):
            # Access component's inputs, slots and context
            assert self.args == [123, "str"]
            assert self.kwargs == {"variable": "test", "another": 1}
            footer_slot = self.slots["footer"]
            some_var = self.input.context["some_var"]

    rendered = TestComponent.render(
        kwargs={"variable": "test", "another": 1},
        args=[123, "str"],
        slots={"footer": "MY_SLOT"},
    )
    ```
    """

    args: Any
    """
    The `args` argument as passed to
    [`Component.get_template_data()`](../api/#django_components.Component.get_template_data).

    This is part of the [Render API](../../concepts/fundamentals/render_api).

    If you defined the [`Component.Args`](../api/#django_components.Component.Args) class,
    then the `args` property will return an instance of that class.

    Otherwise, `args` will be a plain list.

    **Example:**

    With `Args` class:

    ```python
    from django_components import Component

    class Table(Component):
        class Args(NamedTuple):
            page: int
            per_page: int

        def on_render_before(self, context: Context, template: Template) -> None:
            assert self.args.page == 123
            assert self.args.per_page == 10

    rendered = Table.render(
        args=[123, 10],
    )
    ```

    Without `Args` class:

    ```python
    from django_components import Component

    class Table(Component):
        def on_render_before(self, context: Context, template: Template) -> None:
            assert self.args[0] == 123
            assert self.args[1] == 10
    ```
    """

    kwargs: Any
    """
    The `kwargs` argument as passed to
    [`Component.get_template_data()`](../api/#django_components.Component.get_template_data).

    This is part of the [Render API](../../concepts/fundamentals/render_api).

    If you defined the [`Component.Kwargs`](../api/#django_components.Component.Kwargs) class,
    then the `kwargs` property will return an instance of that class.

    Otherwise, `kwargs` will be a plain dict.

    **Example:**

    With `Kwargs` class:

    ```python
    from django_components import Component

    class Table(Component):
        class Kwargs(NamedTuple):
            page: int
            per_page: int

        def on_render_before(self, context: Context, template: Template) -> None:
            assert self.kwargs.page == 123
            assert self.kwargs.per_page == 10

    rendered = Table.render(
        kwargs={
            "page": 123,
            "per_page": 10,
        },
    )
    ```

    Without `Kwargs` class:

    ```python
    from django_components import Component

    class Table(Component):
        def on_render_before(self, context: Context, template: Template) -> None:
            assert self.kwargs["page"] == 123
            assert self.kwargs["per_page"] == 10
    ```
    """

    slots: Any
    """
    The `slots` argument as passed to
    [`Component.get_template_data()`](../api/#django_components.Component.get_template_data).

    This is part of the [Render API](../../concepts/fundamentals/render_api).

    If you defined the [`Component.Slots`](../api/#django_components.Component.Slots) class,
    then the `slots` property will return an instance of that class.

    Otherwise, `slots` will be a plain dict.

    **Example:**

    With `Slots` class:

    ```python
    from django_components import Component, Slot, SlotInput

    class Table(Component):
        class Slots(NamedTuple):
            header: SlotInput
            footer: SlotInput

        def on_render_before(self, context: Context, template: Template) -> None:
            assert isinstance(self.slots.header, Slot)
            assert isinstance(self.slots.footer, Slot)

    rendered = Table.render(
        slots={
            "header": "MY_HEADER",
            "footer": lambda ctx: "FOOTER: " + ctx.data["user_id"],
        },
    )
    ```

    Without `Slots` class:

    ```python
    from django_components import Component, Slot, SlotInput

    class Table(Component):
        def on_render_before(self, context: Context, template: Template) -> None:
            assert isinstance(self.slots["header"], Slot)
            assert isinstance(self.slots["footer"], Slot)
    ```
    """

    context: Context
    """
    The `context` argument as passed to
    [`Component.get_template_data()`](../api/#django_components.Component.get_template_data).

    This is Django's [Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
    with which the component template is rendered.

    If the root component or template was rendered with
    [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
    then this will be an instance of `RequestContext`.

    Whether the context variables defined in `context` are available to the template depends on the
    [context behavior mode](../settings#django_components.app_settings.ComponentsSettings.context_behavior):

    - In `"django"` context behavior mode, the template will have access to the keys of this context.

    - In `"isolated"` context behavior mode, the template will NOT have access to this context,
        and data MUST be passed via component's args and kwargs.
    """

    outer_context: Optional[Context]
    """
    When a component is rendered with the [`{% component %}`](../template_tags#component) tag,
    this is the Django's [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
    object that was used just outside of the component.

    ```django
    {% with abc=123 %}
        {{ abc }} {# <--- This is in outer context #}
        {% component "my_component" / %}
    {% endwith %}
    ```

    This is relevant when your components are isolated, for example when using
    the ["isolated"](../settings#django_components.app_settings.ComponentsSettings.context_behavior)
    context behavior mode or when using the `only` flag.

    When components are isolated, each component has its own instance of Context,
    so `outer_context` is different from the `context` argument.
    """

    registry: ComponentRegistry
    """
    The [`ComponentRegistry`](../api/#django_components.ComponentRegistry) instance
    that was used to render the component.
    """

    # TODO_v1 - Remove, superseded by `Component.slots`
    is_filled: SlotIsFilled
    """
    Deprecated. Will be removed in v1. Use [`Component.slots`](../api/#django_components.Component.slots) instead.
    Note that `Component.slots` no longer escapes the slot names.

    Dictionary describing which slots have or have not been filled.

    This attribute is available for use only within:

    You can also access this variable from within the template as

    [`{{ component_vars.is_filled.slot_name }}`](../template_vars#django_components.component.ComponentVars.is_filled)

    """  # noqa: E501

    request: Optional[HttpRequest]
    """
    [HTTPRequest](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpRequest)
    object passed to this component.

    **Example:**

    ```py
    class MyComponent(Component):
        def get_template_data(self, args, kwargs, slots, context):
            user_id = self.request.GET['user_id']
            return {
                'user_id': user_id,
            }
    ```

    **Passing `request` to a component:**

    In regular Django templates, you have to use
    [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
    to pass the `HttpRequest` object to the template.

    With Components, you can either use `RequestContext`, or pass the `request` object
    explicitly via [`Component.render()`](../api#django_components.Component.render) and
    [`Component.render_to_response()`](../api#django_components.Component.render_to_response).

    When a component is nested in another, the child component uses parent's `request` object.
    """

    @property
    def context_processors_data(self) -> Dict:
        """
        Retrieve data injected by
        [`context_processors`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#configuring-an-engine).

        This data is also available from within the component's template, without having to
        return this data from
        [`get_template_data()`](../api#django_components.Component.get_template_data).

        In regular Django templates, you need to use
        [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
        to apply context processors.

        In Components, the context processors are applied to components either when:

        - The component is rendered with
            [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
            (Regular Django behavior)
        - The component is rendered with a regular
            [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context) (or none),
            but the `request` kwarg of [`Component.render()`](../api#django_components.Component.render) is set.
        - The component is nested in another component that matches any of these conditions.

        See
        [`Component.request`](../api#django_components.Component.request)
        on how the `request`
        ([HTTPRequest](https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpRequest))
        object is passed to and within the components.

        NOTE: This dictionary is generated dynamically, so any changes to it will not be persisted.

        **Example:**

        ```py
        class MyComponent(Component):
            def get_template_data(self, args, kwargs, slots, context):
                user = self.context_processors_data['user']
                return {
                    'is_logged_in': user.is_authenticated,
                }
        ```
        """
        request = self.request

        if request is None:
            return {}
        else:
            return gen_context_processors_data(self.context, request)

    # #####################################
    # MISC
    # #####################################

    def inject(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Use this method to retrieve the data that was passed to a [`{% provide %}`](../template_tags#provide) tag
        with the corresponding key.

        To retrieve the data, `inject()` must be called inside a component that's
        inside the [`{% provide %}`](../template_tags#provide) tag.

        You may also pass a default that will be used if the [`{% provide %}`](../template_tags#provide) tag
        with given key was NOT found.

        This method is part of the [Render API](../../concepts/fundamentals/render_api), and
        raises an error if called from outside the rendering execution.

        Read more about [Provide / Inject](../../concepts/advanced/provide_inject).

        **Example:**

        Given this template:
        ```django
        {% provide "my_provide" message="hello" %}
            {% component "my_comp" / %}
        {% endprovide %}
        ```

        And given this definition of "my_comp" component:
        ```py
        from django_components import Component, register

        @register("my_comp")
        class MyComp(Component):
            template = "hi {{ message }}!"

            def get_template_data(self, args, kwargs, slots, context):
                data = self.inject("my_provide")
                message = data.message
                return {"message": message}
        ```

        This renders into:
        ```
        hi hello!
        ```

        As the `{{ message }}` is taken from the "my_provide" provider.
        """
        return get_injected_context_var(self.name, self.input.context, key, default)

    @classmethod
    def as_view(cls, **initkwargs: Any) -> ViewFn:
        """
        Shortcut for calling `Component.View.as_view` and passing component instance to it.

        Read more on [Component views and URLs](../../concepts/fundamentals/component_views_urls).
        """

        # NOTE: `Component.View` may not be available at the time that URLs are being
        # defined. So we return a view that calls `View.as_view()` only once it's actually called.
        def outer_view(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            # `view` is a built-in extension defined in `extensions.view`. It subclasses
            # from Django's `View` class, and adds the `component` attribute to it.
            view_cls = cast(View, cls.View)  # type: ignore[attr-defined]

            # TODO_v1 - Remove `component` and use only `component_cls` instead.
            inner_view = view_cls.as_view(**initkwargs, component=cls(), component_cls=cls)
            return inner_view(request, *args, **kwargs)

        return outer_view

    # #####################################
    # RENDERING
    # #####################################

    @classmethod
    def render_to_response(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        slots: Optional[Any] = None,
        deps_strategy: DependenciesStrategy = "document",
        # TODO_v1 - Remove, superseded by `deps_strategy`
        type: Optional[DependenciesStrategy] = None,
        # TODO_v1 - Remove, superseded by `deps_strategy="ignore"`
        render_dependencies: bool = True,
        request: Optional[HttpRequest] = None,
        outer_context: Optional[Context] = None,
        # TODO_v2 - Remove `registered_name` and `registry`
        registry: Optional[ComponentRegistry] = None,
        registered_name: Optional[str] = None,
        **response_kwargs: Any,
    ) -> HttpResponse:
        """
        Render the component and wrap the content in an HTTP response class.

        `render_to_response()` takes the same inputs as
        [`Component.render()`](../api/#django_components.Component.render).
        See that method for more information.

        After the component is rendered, the HTTP response class is instantiated with the rendered content.

        Any additional kwargs are passed to the response class.

        **Example:**

        ```python
        Button.render_to_response(
            args=["John"],
            kwargs={
                "surname": "Doe",
                "age": 30,
            },
            slots={
                "footer": "i AM A SLOT",
            },
            # HttpResponse kwargs
            status=201,
            headers={...},
        )
        # HttpResponse(content=..., status=201, headers=...)
        ```

        **Custom response class:**

        You can set a custom response class on the component via
        [`Component.response_class`](../api/#django_components.Component.response_class).
        Defaults to
        [`django.http.HttpResponse`](https://docs.djangoproject.com/en/5.2/ref/request-response/#httpresponse-objects).

        ```python
        from django.http import HttpResponse
        from django_components import Component

        class MyHttpResponse(HttpResponse):
            ...

        class MyComponent(Component):
            response_class = MyHttpResponse

        response = MyComponent.render_to_response()
        assert isinstance(response, MyHttpResponse)
        ```
        """
        content = cls.render(
            args=args,
            kwargs=kwargs,
            context=context,
            slots=slots,
            deps_strategy=deps_strategy,
            # TODO_v1 - Remove, superseded by `deps_strategy`
            type=type,
            # TODO_v1 - Remove, superseded by `deps_strategy`
            render_dependencies=render_dependencies,
            request=request,
            outer_context=outer_context,
            # TODO_v2 - Remove `registered_name` and `registry`
            registry=registry,
            registered_name=registered_name,
        )
        return cls.response_class(content, **response_kwargs)

    @classmethod
    def render(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        slots: Optional[Any] = None,
        deps_strategy: DependenciesStrategy = "document",
        # TODO_v1 - Remove, superseded by `deps_strategy`
        type: Optional[DependenciesStrategy] = None,
        # TODO_v1 - Remove, superseded by `deps_strategy="ignore"`
        render_dependencies: bool = True,
        request: Optional[HttpRequest] = None,
        outer_context: Optional[Context] = None,
        # TODO_v2 - Remove `registered_name` and `registry`
        registry: Optional[ComponentRegistry] = None,
        registered_name: Optional[str] = None,
    ) -> str:
        """
        Render the component into a string. This is the equivalent of calling
        the [`{% component %}`](../template_tags#component) tag.

        ```python
        Button.render(
            args=["John"],
            kwargs={
                "surname": "Doe",
                "age": 30,
            },
            slots={
                "footer": "i AM A SLOT",
            },
        )
        ```

        **Inputs:**

        - `args` - Optional. A list of positional args for the component. This is the same as calling the component
          as:

            ```django
            {% component "button" arg1 arg2 ... %}
            ```

        - `kwargs` - Optional. A dictionary of keyword arguments for the component. This is the same as calling
          the component as:

            ```django
            {% component "button" key1=val1 key2=val2 ... %}
            ```

        - `slots` - Optional. A dictionary of slot fills. This is the same as passing [`{% fill %}`](../template_tags#fill)
            tags to the component.

            ```django
            {% component "button" %}
                {% fill "content" %}
                    Click me!
                {% endfill %}
            {% endcomponent %}
            ```

            Dictionary keys are the slot names. Dictionary values are the slot fills.

            Slot fills can be strings, render functions, or [`Slot`](../api/#django_components.Slot) instances:

            ```python
            Button.render(
                slots={
                    "content": "Click me!"
                    "content2": lambda ctx: "Click me!",
                    "content3": Slot(lambda ctx: "Click me!"),
                },
            )
            ```

        - `context` - Optional. Plain dictionary or Django's
            [Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context).
            The context within which the component is rendered.

            When a component is rendered within a template with the [`{% component %}`](../template_tags#component)
            tag, this will be set to the
            [Context](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context)
            instance that is used for rendering the template.

            When you call `Component.render()` directly from Python, you can ignore this input most of the time.
            Instead use `args`, `kwargs`, and `slots` to pass data to the component.

            You can pass
            [`RequestContext`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.RequestContext)
            to the `context` argument, so that the component will gain access to the request object and will use
            [context processors](https://docs.djangoproject.com/en/5.2/ref/templates/api/#using-requestcontext).
            Read more on [Working with HTTP requests](../../concepts/fundamentals/http_request).

            ```py
            Button.render(
                context=RequestContext(request),
            )
            ```

            For advanced use cases, you can use `context` argument to "pre-render" the component in Python, and then
            pass the rendered output as plain string to the template. With this, the inner component is rendered as if
            it was within the template with [`{% component %}`](../template_tags#component).

            ```py
            class Button(Component):
                def render(self, context, template):
                    # Pass `context` to Icon component so it is rendered
                    # as if nested within Button.
                    icon = Icon.render(
                        context=context,
                        args=["icon-name"],
                        deps_strategy="ignore",
                    )
                    # Update context with icon
                    with context.update({"icon": icon}):
                        return template.render(context)
            ```

            Whether the variables defined in `context` are available to the template depends on the
            [context behavior mode](../settings#django_components.app_settings.ComponentsSettings.context_behavior):

            - In `"django"` context behavior mode, the template will have access to the keys of this context.

            - In `"isolated"` context behavior mode, the template will NOT have access to this context,
                and data MUST be passed via component's args and kwargs.

        - `deps_strategy` - Optional. Configure how to handle JS and CSS dependencies. Read more about
            [Dependencies rendering](../../concepts/fundamentals/rendering_components#dependencies-rendering).

            There are six strategies:

            - [`"document"`](../../concepts/advanced/rendering_js_css#document) (default)
                - Smartly inserts JS / CSS into placeholders or into `<head>` and `<body>` tags.
                - Inserts extra script to allow `fragment` types to work.
                - Assumes the HTML will be rendered in a JS-enabled browser.
            - [`"fragment"`](../../concepts/advanced/rendering_js_css#fragment)
                - A lightweight HTML fragment to be inserted into a document with AJAX.
                - No JS / CSS included.
            - [`"simple"`](../../concepts/advanced/rendering_js_css#simple)
                - Smartly insert JS / CSS into placeholders or into `<head>` and `<body>` tags.
                - No extra script loaded.
            - [`"prepend"`](../../concepts/advanced/rendering_js_css#prepend)
                - Insert JS / CSS before the rendered HTML.
                - No extra script loaded.
            - [`"append"`](../../concepts/advanced/rendering_js_css#append)
                - Insert JS / CSS after the rendered HTML.
                - No extra script loaded.
            - [`"ignore"`](../../concepts/advanced/rendering_js_css#ignore)
                - HTML is left as-is. You can still process it with a different strategy later with
                  [`render_dependencies()`](../api/#django_components.render_dependencies).
                - Used for inserting rendered HTML into other components.

        - `request` - Optional. HTTPRequest object. Pass a request object directly to the component to apply
            [context processors](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context.update).

            Read more about [Working with HTTP requests](../../concepts/fundamentals/http_request).

        **Type hints:**

        `Component.render()` is NOT typed. To add type hints, you can wrap the inputs
        in component's [`Args`](../api/#django_components.Component.Args),
        [`Kwargs`](../api/#django_components.Component.Kwargs),
        and [`Slots`](../api/#django_components.Component.Slots) classes.

        Read more on [Typing and validation](../../concepts/fundamentals/typing_and_validation).

        ```python
        from typing import NamedTuple, Optional
        from django_components import Component, Slot, SlotInput

        # Define the component with the types
        class Button(Component):
            class Args(NamedTuple):
                name: str

            class Kwargs(NamedTuple):
                surname: str
                age: int

            class Slots(NamedTuple):
                my_slot: Optional[SlotInput] = None
                footer: SlotInput

        # Add type hints to the render call
        Button.render(
            args=Button.Args(
                name="John",
            ),
            kwargs=Button.Kwargs(
                surname="Doe",
                age=30,
            ),
            slots=Button.Slots(
                footer=Slot(lambda ctx: "Click me!"),
            ),
        )
        ```
        """  # noqa: 501

        # TODO_v1 - Remove, superseded by `deps_strategy`
        if type is not None:
            if deps_strategy != "document":
                raise ValueError(
                    "Component.render() received both `type` and `deps_strategy` arguments. "
                    "Only one should be given. The `type` argument is deprecated. Use `deps_strategy` instead."
                )
            deps_strategy = type

        # TODO_v1 - Remove, superseded by `deps_strategy="ignore"`
        if not render_dependencies:
            deps_strategy = "ignore"

        return cls._render_with_error_trace(
            context=context,
            args=args,
            kwargs=kwargs,
            slots=slots,
            deps_strategy=deps_strategy,
            request=request,
            outer_context=outer_context,
            # TODO_v2 - Remove `registered_name` and `registry`
            registry=registry,
            registered_name=registered_name,
        )

    # This is the internal entrypoint for the render function
    @classmethod
    def _render_with_error_trace(
        cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        slots: Optional[Any] = None,
        deps_strategy: DependenciesStrategy = "document",
        request: Optional[HttpRequest] = None,
        outer_context: Optional[Context] = None,
        # TODO_v2 - Remove `registered_name` and `registry`
        registry: Optional[ComponentRegistry] = None,
        registered_name: Optional[str] = None,
    ) -> str:
        component_name = _get_component_name(cls, registered_name)

        # Modify the error to display full component path (incl. slots)
        with component_error_message([component_name]):
            return cls._render_impl(
                context=context,
                args=args,
                kwargs=kwargs,
                slots=slots,
                deps_strategy=deps_strategy,
                request=request,
                outer_context=outer_context,
                # TODO_v2 - Remove `registered_name` and `registry`
                registry=registry,
                registered_name=registered_name,
            )

    @classmethod
    def _render_impl(
        comp_cls,
        context: Optional[Union[Dict[str, Any], Context]] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        slots: Optional[Any] = None,
        deps_strategy: DependenciesStrategy = "document",
        request: Optional[HttpRequest] = None,
        outer_context: Optional[Context] = None,
        # TODO_v2 - Remove `registered_name` and `registry`
        registry: Optional[ComponentRegistry] = None,
        registered_name: Optional[str] = None,
    ) -> str:
        ######################################
        # 1. Handle inputs
        ######################################

        # Allow to pass down Request object via context.
        # `context` may be passed explicitly via `Component.render()` and `Component.render_to_response()`,
        # or implicitly via `{% component %}` tag.
        if request is None and context:
            # If the context is `RequestContext`, it has `request` attribute
            request = getattr(context, "request", None)
            # Check if this is a nested component and whether parent has request
            if request is None:
                _, parent_comp_ctx = _get_parent_component_context(context)
                if parent_comp_ctx:
                    request = parent_comp_ctx.component.request

        component_name = _get_component_name(comp_cls, registered_name)

        # Allow to provide no args/kwargs/slots/context
        # NOTE: We make copies of args / kwargs / slots, so that plugins can modify them
        # without affecting the original values.
        args_list: List[Any] = list(default(args, []))
        kwargs_dict = to_dict(default(kwargs, {}))
        slots_dict = normalize_slot_fills(
            to_dict(default(slots, {})),
            component_name=component_name,
        )
        # Use RequestContext if request is provided, so that child non-component template tags
        # can access the request object too.
        context = context if context is not None else (RequestContext(request) if request else Context())

        # Allow to provide a dict instead of Context
        # NOTE: This if/else is important to avoid nested Contexts,
        # See https://github.com/django-components/django-components/issues/414
        if not isinstance(context, (Context, RequestContext)):
            context = RequestContext(request, context) if request else Context(context)

        render_id = _gen_component_id()

        component = comp_cls(
            id=render_id,
            args=args_list,
            kwargs=kwargs_dict,
            slots=slots_dict,
            context=context,
            request=request,
            deps_strategy=deps_strategy,
            outer_context=outer_context,
            # TODO_v2 - Remove `registered_name` and `registry`
            registry=registry,
            registered_name=registered_name,
        )

        # Allow plugins to modify or validate the inputs
        result_override = extensions.on_component_input(
            OnComponentInputContext(
                component=component,
                component_cls=comp_cls,
                component_id=render_id,
                args=args_list,
                kwargs=kwargs_dict,
                slots=slots_dict,
                context=context,
            )
        )

        # The component rendering was short-circuited by an extension, skipping
        # the rest of the rendering process. This may be for example a cached content.
        if result_override is not None:
            return result_override

        # If user doesn't specify `Args`, `Kwargs`, `Slots` types, then we pass them in as plain
        # dicts / lists.
        component.args = comp_cls.Args(*args_list) if comp_cls.Args is not None else args_list
        component.kwargs = comp_cls.Kwargs(**kwargs_dict) if comp_cls.Kwargs is not None else kwargs_dict
        component.slots = comp_cls.Slots(**slots_dict) if comp_cls.Slots is not None else slots_dict

        ######################################
        # 2. Prepare component state
        ######################################

        # Required for compatibility with Django's {% extends %} tag
        # See https://github.com/django-components/django-components/pull/859
        context.render_context.push(  # type: ignore[union-attr]
            {BLOCK_CONTEXT_KEY: context.render_context.get(BLOCK_CONTEXT_KEY, BlockContext())}  # type: ignore
        )

        # We pass down the components the info about the component's parent.
        # This is used for correctly resolving slot fills, correct rendering order,
        # or CSS scoping.
        parent_id, parent_comp_ctx = _get_parent_component_context(context)
        if parent_comp_ctx is not None:
            component_path = [*parent_comp_ctx.component_path, component_name]
            post_render_callbacks = parent_comp_ctx.post_render_callbacks
        else:
            component_path = [component_name]
            post_render_callbacks = {}

        trace_component_msg(
            "COMP_PREP_START",
            component_name=component_name,
            component_id=render_id,
            slot_name=None,
            component_path=component_path,
            extra=(
                f"Received {len(args_list)} args, {len(kwargs_dict)} kwargs, {len(slots_dict)} slots,"
                f" Available slots: {slots_dict}"
            ),
        )

        # Register the component to provide
        register_provide_reference(context, render_id)

        # This is data that will be accessible (internally) from within the component's template
        component_ctx = ComponentContext(
            component=component,
            component_path=component_path,
            # Template name is set only once we've resolved the component's Template instance.
            template_name=None,
            # This field will be modified from within `SlotNodes.render()`:
            # - The `default_slot` will be set to the first slot that has the `default` attribute set.
            # - If multiple slots have the `default` attribute set, yet have different name, then
            #   we will raise an error.
            default_slot=None,
            # NOTE: This is only a SNAPSHOT of the outer context.
            outer_context=snapshot_context(outer_context) if outer_context is not None else None,
            post_render_callbacks=post_render_callbacks,
        )

        # Instead of passing the ComponentContext directly through the Context, the entry on the Context
        # contains only a key to retrieve the ComponentContext from `component_context_cache`.
        #
        # This way, the flow is easier to debug. Because otherwise, if you tried to print out
        # or inspect the Context object, your screen would be filled with the deeply nested ComponentContext objects.
        # But now, the printed Context may simply look like this:
        # `[{ "True": True, "False": False, "None": None }, {"_DJC_COMPONENT_CTX": "c1A2b3c"}]`
        component_context_cache[render_id] = component_ctx

        ######################################
        # 3. Call data methods
        ######################################

        template_data, js_data, css_data = component._call_data_methods(context, args_list, kwargs_dict)

        extensions.on_component_data(
            OnComponentDataContext(
                component=component,
                component_cls=comp_cls,
                component_id=render_id,
                # TODO_V1 - Remove `context_data`
                context_data=template_data,
                template_data=template_data,
                js_data=js_data,
                css_data=css_data,
            )
        )

        # Process Component's JS and CSS
        cache_component_js(comp_cls)
        js_input_hash = cache_component_js_vars(comp_cls, js_data) if js_data else None

        cache_component_css(comp_cls)
        css_input_hash = cache_component_css_vars(comp_cls, css_data) if css_data else None

        #############################################################################
        # 4. Make Context copy
        #
        # NOTE: To support infinite recursion, we make a copy of the context.
        #       This way we don't have to call the whole component tree in one go recursively,
        #       but instead can render one component at a time.
        #############################################################################

        # TODO_v1 - Currently we have to pass `template_data` to `prepare_component_template()`,
        #     so that `get_template_string()`, `get_template_name()`, and `get_template()`
        #     have access to the data from `get_template_data()`.
        #
        #     Because of that there is one layer of `Context.update()` called inside `prepare_component_template()`.
        #
        #     Once `get_template_string()`, `get_template_name()`, and `get_template()` are removed,
        #     we can remove that layer of `Context.update()`, and NOT pass `template_data`
        #     to `prepare_component_template()`.
        #
        #     Then we can simply apply `template_data` to the context in the same layer
        #     where we apply `context_processor_data` and `component_vars`.
        with prepare_component_template(component, template_data) as template:
            # Set `Template._djc_is_component_nested` based on whether we're currently INSIDE
            # the `{% extends %}` tag.
            # Part of fix for https://github.com/django-components/django-components/issues/508
            # See django_monkeypatch.py
            if template is not None:
                template._djc_is_component_nested = bool(
                    context.render_context.get(BLOCK_CONTEXT_KEY)  # type: ignore[union-attr]
                )

            # Capture the template name so we can print better error messages (currently used in slots)
            component_ctx.template_name = template.name if template else None

            with context.update(  # type: ignore[union-attr]
                {
                    # Make data from context processors available inside templates
                    **component.context_processors_data,
                    # Private context fields
                    _COMPONENT_CONTEXT_KEY: render_id,
                    # NOTE: Public API for variables accessible from within a component's template
                    # See https://github.com/django-components/django-components/issues/280#issuecomment-2081180940
                    "component_vars": ComponentVars(
                        args=component.args,
                        kwargs=component.kwargs,
                        slots=component.slots,
                        # TODO_v1 - Remove this, superseded by `component_vars.slots`
                        #
                        # For users, we expose boolean variables that they may check
                        # to see if given slot was filled, e.g.:
                        # `{% if variable > 8 and component_vars.is_filled.header %}`
                        is_filled=component.is_filled,
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
        context.render_context.pop()  # type: ignore[union-attr]

        ######################################
        # 5. Render component
        #
        # NOTE: To support infinite recursion, we don't directly call `Template.render()`.
        #       Instead, we defer rendering of the component - we prepare a callback that will
        #       be called when the rendering process reaches this component.
        ######################################

        # Instead of rendering component at the time we come across the `{% component %}` tag
        # in the template, we defer rendering in order to scalably handle deeply nested components.
        #
        # See `_gen_component_renderer()` for more details.
        deferred_render = component._gen_component_renderer(
            template=template,
            context=context_snapshot,
            component_path=component_path,
            css_input_hash=css_input_hash,
            js_input_hash=js_input_hash,
            css_scope_id=None,  # TODO - Implement CSS scoping
        )

        # This is triggered when a component is rendered, but the component's parents
        # may not have been rendered yet.
        def on_component_rendered(html: str) -> str:
            # Allow to optionally override/modify the rendered content
            new_output = component.on_render_after(context_snapshot, template, html)
            html = default(new_output, html)

            # Remove component from caches
            del component_context_cache[render_id]  # type: ignore[arg-type]
            unregister_provide_reference(render_id)  # type: ignore[arg-type]

            html = extensions.on_component_rendered(
                OnComponentRenderedContext(
                    component=component,
                    component_cls=comp_cls,
                    component_id=render_id,
                    result=html,
                )
            )

            return html

        post_render_callbacks[render_id] = on_component_rendered

        # This is triggered after a full component tree was rendered, we resolve
        # all inserted HTML comments into <script> and <link> tags.
        def on_html_rendered(html: str) -> str:
            html = _render_dependencies(html, deps_strategy)
            return html

        trace_component_msg(
            "COMP_PREP_END",
            component_name=component_name,
            component_id=render_id,
            slot_name=None,
            component_path=component_path,
        )

        return component_post_render(
            renderer=deferred_render,
            render_id=render_id,
            component_name=component_name,
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
    # Because the HTML attributes are all boolean (e.g. `data-djc-id-ca1b3c4`), they are passed as a list.
    #
    # This whole setup makes it possible for multiple components to resolve to the same HTML element.
    # E.g. if CompA renders CompB, and CompB renders a <div>, then the <div> element will have
    # IDs of both CompA and CompB.
    # ```html
    # <div djc-id-a1b3cf djc-id-f3d3cf>...</div>
    # ```
    def _gen_component_renderer(
        self,
        template: Template,
        context: Context,
        component_path: List[str],
        css_input_hash: Optional[str],
        js_input_hash: Optional[str],
        css_scope_id: Optional[str],
    ) -> ComponentRenderer:
        component = self
        render_id = component.id
        component_name = component.name
        component_cls = component.__class__

        def renderer(root_attributes: Optional[List[str]] = None) -> Tuple[str, Dict[str, List[str]]]:
            trace_component_msg(
                "COMP_RENDER_START",
                component_name=component_name,
                component_id=render_id,
                slot_name=None,
                component_path=component_path,
            )

            component.on_render_before(context, template)

            # Emit signal that the template is about to be rendered
            template_rendered.send(sender=template, template=template, context=context)

            if template is not None:
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
            else:
                updated_html = ""
                child_components = {}

            trace_component_msg(
                "COMP_RENDER_END",
                component_name=component_name,
                component_id=render_id,
                slot_name=None,
                component_path=component_path,
            )

            return updated_html, child_components

        return renderer

    def _call_data_methods(
        self,
        context: Context,
        # TODO_V2 - Remove `raw_args` and `raw_kwargs` in v2
        raw_args: List,
        raw_kwargs: Dict,
    ) -> Tuple[Dict, Dict, Dict]:
        # Template data
        maybe_template_data = self.get_template_data(self.args, self.kwargs, self.slots, self.context)
        new_template_data = to_dict(default(maybe_template_data, {}))

        # TODO_V2 - Remove this in v2
        legacy_template_data = to_dict(default(self.get_context_data(*raw_args, **raw_kwargs), {}))
        if legacy_template_data and new_template_data:
            raise RuntimeError(
                f"Component {self.name} has both `get_context_data()` and `get_template_data()` methods. "
                "Please remove one of them."
            )
        template_data = new_template_data or legacy_template_data

        # TODO - Enable JS and CSS vars - expose, and document
        # JS data
        maybe_js_data = self.get_js_data(self.args, self.kwargs, self.slots, context)
        js_data = to_dict(default(maybe_js_data, {}))

        # CSS data
        maybe_css_data = self.get_css_data(self.args, self.kwargs, self.slots, context)
        css_data = to_dict(default(maybe_css_data, {}))

        # Validate outputs
        if self.TemplateData is not None and not isinstance(template_data, self.TemplateData):
            self.TemplateData(**template_data)
        if self.JsData is not None and not isinstance(js_data, self.JsData):
            self.JsData(**js_data)
        if self.CssData is not None and not isinstance(css_data, self.CssData):
            self.CssData(**css_data)

        return template_data, js_data, css_data


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

    The `{% component %}` tag takes:

    - Component's registered name as the first positional argument,
    - Followed by any number of positional and keyword arguments.

    ```django
    {% load component_tags %}
    <div>
        {% component "button" name="John" job="Developer" / %}
    </div>
    ```

    The component name must be a string literal.

    ### Inserting slot fills

    If the component defined any [slots](../concepts/fundamentals/slots.md), you can
    "fill" these slots by placing the [`{% fill %}`](#fill) tags within the `{% component %}` tag:

    ```django
    {% component "my_table" rows=rows headers=headers %}
      {% fill "pagination" %}
        < 1 | 2 | 3 >
      {% endfill %}
    {% endcomponent %}
    ```

    You can even nest [`{% fill %}`](#fill) tags within
    [`{% if %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#if),
    [`{% for %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#for)
    and other tags:

    ```django
    {% component "my_table" rows=rows headers=headers %}
        {% if rows %}
            {% fill "pagination" %}
                < 1 | 2 | 3 >
            {% endfill %}
        {% endif %}
    {% endcomponent %}
    ```

    ### Isolating components

    By default, components behave similarly to Django's
    [`{% include %}`](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#include),
    and the template inside the component has access to the variables defined in the outer template.

    You can selectively isolate a component, using the `only` flag, so that the inner template
    can access only the data that was explicitly passed to it:

    ```django
    {% component "name" positional_arg keyword_arg=value ... only %}
    ```

    Alternatively, you can set all components to be isolated by default, by setting
    [`context_behavior`](../settings#django_components.app_settings.ComponentsSettings.context_behavior)
    to `"isolated"` in your settings:

    ```python
    # settings.py
    COMPONENTS = {
        "context_behavior": "isolated",
    }
    ```

    ### Omitting the `component` keyword

    If you would like to omit the `component` keyword, and simply refer to your
    components by their registered names:

    ```django
    {% button name="John" job="Developer" / %}
    ```

    You can do so by setting the "shorthand" [Tag formatter](../../concepts/advanced/tag_formatters)
    in the settings:

    ```python
    # settings.py
    COMPONENTS = {
        "tag_formatter": "django_components.component_shorthand_formatter",
    }
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
        contents: Optional[str] = None,
        template_name: Optional[str] = None,
        template_component: Optional[Type["Component"]] = None,
    ) -> None:
        super().__init__(
            params=params,
            flags=flags,
            nodelist=nodelist,
            node_id=node_id,
            contents=contents,
            template_name=template_name,
            template_component=template_component,
        )

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

        slot_fills = resolve_fills(context, self, self.name)

        # Prevent outer context from leaking into the template of the component
        if self.flags[COMP_ONLY_FLAG] or self.registry.settings.context_behavior == ContextBehavior.ISOLATED:
            inner_context = make_isolated_context_copy(context)
        else:
            inner_context = context

        output = component_cls._render_with_error_trace(
            context=inner_context,
            args=args,
            kwargs=kwargs,
            slots=slot_fills,
            # NOTE: When we render components inside the template via template tags,
            # do NOT render deps, because this may be decided by outer component
            deps_strategy="ignore",
            registered_name=self.name,
            outer_context=context,
            registry=self.registry,
        )

        return output


def _get_parent_component_context(context: Context) -> Union[Tuple[None, None], Tuple[str, ComponentContext]]:
    parent_id = context.get(_COMPONENT_CONTEXT_KEY, None)
    if parent_id is None:
        return None, None

    # NOTE: This may happen when slots are rendered outside of the component's render context.
    # See https://github.com/django-components/django-components/issues/1189
    if parent_id not in component_context_cache:
        return None, None

    parent_comp_ctx = component_context_cache[parent_id]
    return parent_id, parent_comp_ctx
