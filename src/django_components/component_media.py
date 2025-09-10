# ruff: noqa: PTH100, PTH118, PTH120, PTH207
import glob
import os
import sys
from collections import deque
from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from weakref import WeakKeyDictionary

from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media as MediaCls
from django.template import Template
from django.utils.safestring import SafeData
from typing_extensions import TypeGuard

from django_components.extension import OnCssLoadedContext, OnJsLoadedContext, extensions
from django_components.template import ensure_unique_template, load_component_template
from django_components.util.loader import get_component_dirs, resolve_file
from django_components.util.logger import logger
from django_components.util.misc import flatten, get_import_path, get_module_info, is_glob

if TYPE_CHECKING:
    from django_components.component import Component


T = TypeVar("T")


# These are all the attributes that are handled by ComponentMedia and lazily-resolved
COMP_MEDIA_LAZY_ATTRS = ("media", "template", "template_file", "js", "js_file", "css", "css_file", "_template")


# Sentinel value to indicate that a media attribute is not set.
# We use this to differntiate between setting template to `None` and not setting it at all.
# If not set, we will use the template from the parent component.
# If set to `None`, then this component has no template.
class Unset:
    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "<UNSET>"


UNSET = Unset()


ComponentMediaInputPath = Union[
    str,
    bytes,
    SafeData,
    Path,
    os.PathLike,
    Callable[[], Union[str, bytes, SafeData, Path, os.PathLike]],
]
"""
A type representing an entry in [Media.js](../api#django_components.ComponentMediaInput.js)
or [Media.css](../api#django_components.ComponentMediaInput.css).

If an entry is a [SafeString](https://dev.to/doridoro/django-safestring-afj) (or has `__html__` method),
then entry is assumed to be a formatted HTML tag. Otherwise, it's assumed to be a path to a file.

**Example:**

```py
class MyComponent
    class Media:
        js = [
            "path/to/script.js",
            b"script.js",
            SafeString("<script src='path/to/script.js'></script>"),
        ]
        css = [
            Path("path/to/style.css"),
            lambda: "path/to/style.css",
            lambda: Path("path/to/style.css"),
        ]
```
"""


# This is the interface of the class that user is expected to define on the component class, e.g.:
# ```py
# class MyComponent(Component):
#     class Media:
#         js = "path/to/script.js"
#         css = "path/to/style.css"
# ```
class ComponentMediaInput(Protocol):
    """
    Defines JS and CSS media files associated with a [`Component`](../api#django_components.Component).

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
    """

    css: Optional[
        Union[
            ComponentMediaInputPath,
            List[ComponentMediaInputPath],
            Dict[str, ComponentMediaInputPath],
            Dict[str, List[ComponentMediaInputPath]],
        ]
    ] = None
    """
    CSS files associated with a [`Component`](../api#django_components.Component).

    - If a string, it's assumed to be a path to a CSS file.

    - If a list, each entry is assumed to be a path to a CSS file.

    - If a dict, the keys are media types (e.g. "all", "print", "screen", etc.), and the values are either:
        - A string, assumed to be a path to a CSS file.
        - A list, each entry is assumed to be a path to a CSS file.

    Each entry can be a string, bytes, SafeString, PathLike, or a callable that returns one of the former
    (see [`ComponentMediaInputPath`](../api#django_components.ComponentMediaInputPath)).

    Examples:
    ```py
    class MyComponent(Component):
        class Media:
            css = "path/to/style.css"
    ```

    ```py
    class MyComponent(Component):
        class Media:
            css = ["path/to/style1.css", "path/to/style2.css"]
    ```

    ```py
    class MyComponent(Component):
        class Media:
            css = {
                "all": "path/to/style.css",
                "print": "path/to/print.css",
            }
    ```

    ```py
    class MyComponent(Component):
        class Media:
            css = {
                "all": ["path/to/style1.css", "path/to/style2.css"],
                "print": "path/to/print.css",
            }
    ```
    """

    js: Optional[Union[ComponentMediaInputPath, List[ComponentMediaInputPath]]] = None
    """
    JS files associated with a [`Component`](../api#django_components.Component).

    - If a string, it's assumed to be a path to a JS file.

    - If a list, each entry is assumed to be a path to a JS file.

    Each entry can be a string, bytes, SafeString, PathLike, or a callable that returns one of the former
    (see [`ComponentMediaInputPath`](../api#django_components.ComponentMediaInputPath)).

    Examples:
    ```py
    class MyComponent(Component):
        class Media:
            js = "path/to/script.js"
    ```

    ```py
    class MyComponent(Component):
        class Media:
            js = ["path/to/script1.js", "path/to/script2.js"]
    ```

    ```py
    class MyComponent(Component):
        class Media:
            js = lambda: ["path/to/script1.js", "path/to/script2.js"]
    ```
    """

    extend: Union[bool, List[Type["Component"]]] = True
    """
    Configures whether the component should inherit the media files from the parent component.

    - If `True`, the component inherits the media files from the parent component.
    - If `False`, the component does not inherit the media files from the parent component.
    - If a list of components classes, the component inherits the media files ONLY from these specified components.

    Read more in [Media inheritance](../../concepts/fundamentals/secondary_js_css_files/#media-inheritance) section.

    **Example:**

    Disable media inheritance:

    ```python
    class ParentComponent(Component):
        class Media:
            js = ["parent.js"]

    class MyComponent(ParentComponent):
        class Media:
            extend = False  # Don't inherit parent media
            js = ["script.js"]

    print(MyComponent.media._js)  # ["script.js"]
    ```

    Specify which components to inherit from. In this case, the media files are inherited ONLY
    from the specified components, and NOT from the original parent components:

    ```python
    class ParentComponent(Component):
        class Media:
            js = ["parent.js"]

    class MyComponent(ParentComponent):
        class Media:
            # Only inherit from these, ignoring the files from the parent
            extend = [OtherComponent1, OtherComponent2]

            js = ["script.js"]

    print(MyComponent.media._js)  # ["script.js", "other1.js", "other2.js"]
    ```
    """


@dataclass
class ComponentMedia:
    comp_cls: Type["Component"]
    resolved: bool = False
    resolved_relative_files: bool = False
    Media: Union[Type[ComponentMediaInput], Unset, None] = UNSET
    template: Union[str, Unset, None] = UNSET
    template_file: Union[str, Unset, None] = UNSET
    js: Union[str, Unset, None] = UNSET
    js_file: Union[str, Unset, None] = UNSET
    css: Union[str, Unset, None] = UNSET
    css_file: Union[str, Unset, None] = UNSET
    # Template instance that was loaded for this component
    _template: Union[Template, Unset, None] = UNSET

    def __post_init__(self) -> None:
        for inlined_attr in ("template", "js", "css"):
            file_attr = f"{inlined_attr}_file"

            inlined_val = getattr(self, inlined_attr)
            file_val = getattr(self, file_attr)
            # NOTE: We raise if Component class received both inlined and file values:
            # ```py
            # class MyComp(Component):
            #     js = "..."
            #     js_file = "..."
            # ```
            #
            # But both `None` are allowed:
            # ```py
            # class MyComp(Component):
            #     js = None
            #     js_file = None
            # ```
            if (inlined_val is not UNSET and file_val is not UNSET) and not (inlined_val is None and file_val is None):
                raise ImproperlyConfigured(
                    f"Received non-empty value from both '{inlined_attr}' and '{file_attr}' in"
                    f" Component {self.comp_cls.__name__}. Only one of the two must be set.",
                )
        # Make a copy of the original state, so we can reset it in tests
        self._original = copy(self)

    # Return ComponentMedia to its original state before the media was resolved
    def reset(self) -> None:
        self.__dict__.update(self._original.__dict__)
        self.resolved = False
        self.resolved_relative_files = False


# This metaclass is all about one thing - lazily resolving the media files.
#
# All the CSS/JS/HTML associated with a component - e.g. the `js`, `js_file`, `template_file` or `Media` class,
# are all class attributes. And some of these attributes need to be resolved, e.g. to find the files
# that `js_file`, `css_file` and `template_file` point to.
#
# Some of the resolutions we need to do is:
# - Component's HTML/JS/CSS files can be defined as relative to the component class file. So for each file,
#   we check the relative path points to an actual file, and if so, we use that path.
# - If the component defines `js_file` or `css_file`, we load the content of the file and set it to `js` or `css`.
#   - Note 1: These file paths still may be relative to the component, so the paths are resolved as above,
#             before we load the content.
#   - Note 2: We don't support both `js` and `js_file` being set at the same time.
#
# At the same time, we need to do so lazily, otherwise we hit a problem with circular imports when trying to
# use Django settings. This is because the settings are not available at the time when the component class is defined
# (Assuming that components are defined at the top-level of modules).
#
# We achieve this by:
# 1. At class creation, we define a private `ComponentMedia` object that holds all the media-related attributes.
# 2. At the same time, we replace the actual media-related attributes (like `js`) with descriptors that intercept
#    the access to them.
# 3. When the user tries to access the media-related attributes, we resolve the media files if they haven't been
#    resolved yet.
# 4. Any further access to the media-related attributes will return the resolved values.
class ComponentMediaMeta(type):
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: Dict[str, Any]) -> Type:
        # Normalize the various forms of Media inputs we allow
        if "Media" in attrs:
            _normalize_media(attrs["Media"])

        cls = super().__new__(mcs, name, bases, attrs)
        comp_cls = cast("Type[Component]", cls)

        _setup_lazy_media_resolve(comp_cls, attrs)

        return comp_cls

    # `__setattr__` on metaclass allows to intercept when user tries to set an attribute on the class.
    #
    # NOTE: All of attributes likes `Media`, `js`, `js_file`, etc, they are all class attributes.
    #       If they were instance attributes, we could use `@property` decorator.
    #
    # Because we lazily resolve the media, there's a possibility that the user may try to set some media fields
    # after the media fields were already resolved. This is currently not supported, and we do the resolution
    # only once.
    #
    # Thus, we print a warning when user sets the media fields after they were resolved.
    def __setattr__(cls, name: str, value: Any) -> None:
        if name in COMP_MEDIA_LAZY_ATTRS:
            comp_media: Optional[ComponentMedia] = getattr(cls, "_component_media", None)
            if comp_media is not None and comp_media.resolved:
                print(  # noqa: T201
                    f"WARNING: Setting attribute '{name}' on component '{cls.__name__}' after the media files were"
                    " already resolved. This may lead to unexpected behavior.",
                )

        # NOTE: When a metaclass specifies a `__setattr__` method, this overrides the normal behavior of
        #       setting an attribute on the class with Descriptors. So we need to call the normal behavior explicitly.
        # NOTE 2: `__dict__` is used to access the class attributes directly, without triggering the descriptors.
        desc = cls.__dict__.get(name, None)
        if hasattr(desc, "__set__"):
            desc.__set__(cls, value)
        else:
            super().__setattr__(name, value)


# This sets up the lazy resolution of the media attributes.
def _setup_lazy_media_resolve(comp_cls: Type["Component"], attrs: Dict[str, Any]) -> None:
    # Collect all the original values of the lazy attributes, so we can access them from the getter
    comp_cls._component_media = ComponentMedia(
        comp_cls=comp_cls,
        resolved=False,
        # NOTE: We take the values from `attrs` so we consider only the values that were set on THIS class,
        #       and not the values that were inherited from the parent classes.
        Media=attrs.get("Media", UNSET),
        template=attrs.get("template", UNSET),
        template_file=attrs.get("template_file", UNSET),
        js=attrs.get("js", UNSET),
        js_file=attrs.get("js_file", UNSET),
        css=attrs.get("css", UNSET),
        css_file=attrs.get("css_file", UNSET),
    )

    def get_comp_media_attr(attr: str) -> Any:
        if attr == "media":
            return _get_comp_cls_media(comp_cls)
        return _get_comp_cls_attr(comp_cls, attr)

    # Because of the lazy resolution, we want to know when the user tries to access the media attributes.
    # And because these fields are class attributes, we can't use `@property` decorator.
    #
    # Instead, we define a descriptor for each of the media attributes, and set it on the class.
    # Read more on descriptors https://docs.python.org/3/howto/descriptor.html
    class InterceptDescriptor:
        def __init__(self, name: str) -> None:
            self._attr_name = name

        # `__get__` runs when a class/instance attribute is being accessed
        def __get__(self, instance: Optional["Component"], cls: Type["Component"]) -> Any:
            return get_comp_media_attr(self._attr_name)

    for attr in COMP_MEDIA_LAZY_ATTRS:
        setattr(comp_cls, attr, InterceptDescriptor(attr))


# Because the media values are not defined directly on the instance, but held in `_component_media`,
# then simply accessing `_component_media.js` will NOT get the values from parent classes.
#
# So this function is like `getattr`, but for searching for values inside `_component_media`.
def _get_comp_cls_attr(comp_cls: Type["Component"], attr: str) -> Any:
    for base in comp_cls.mro():
        comp_media: Optional[ComponentMedia] = getattr(base, "_component_media", None)
        if comp_media is None:
            continue
        if not comp_media.resolved:
            _resolve_media(base, comp_media)

        # NOTE: We differentiate between `None` and `UNSET`, so that users can set `None` to
        #       override parent class's value and set it to `None`.
        value = getattr(comp_media, attr, UNSET)

        # For each of the pairs of inlined_content + file (e.g. `js` + `js_file`), if at least one of the two
        # is defined, we interpret it such that this (sub)class has overridden what was set by the parent class(es),
        # and we won't search further up the MRO.
        def is_pair_empty(inline_attr: str, file_attr: str) -> bool:
            inline_attr_empty = getattr(comp_media, inline_attr, UNSET) is UNSET  # noqa: B023
            file_attr_empty = getattr(comp_media, file_attr, UNSET) is UNSET  # noqa: B023

            return inline_attr_empty and file_attr_empty

        if attr in ("js", "js_file"):
            is_empty_pair = is_pair_empty("js", "js_file")
        elif attr in ("css", "css_file"):
            is_empty_pair = is_pair_empty("css", "css_file")
        elif attr in ("template", "template_file"):
            is_empty_pair = is_pair_empty("template", "template_file")
        else:
            is_empty_pair = False

        value = UNSET if is_empty_pair else value

        if value is UNSET:
            continue
        return value
    return None


# NOTE: We use weakref to avoid issues with lingering references.
if sys.version_info >= (3, 9):
    media_cache: WeakKeyDictionary[Type["Component"], MediaCls] = WeakKeyDictionary()
else:
    media_cache: WeakKeyDictionary = WeakKeyDictionary()


def _get_comp_cls_media(comp_cls: Type["Component"]) -> Any:
    # Component's `media` attribute is a special case, because it should inherit all the JS/CSS files
    # from the parent classes. So we need to walk up the MRO and merge all the Media classes.
    #
    # But before we do that, we need to ensure that all parent classes have resolved their `media` attributes.
    # Because to be able to construct `media` for a Component class, all its parent classes must have resolved
    # their `media`.
    #
    # So we will:
    # 0. Cache the resolved media, so we don't have to resolve it again, and so we can store it even for classes
    #   that don't have `Media` attribute.
    # 1. If the current class HAS `media` in the cache, we used that
    # 2. Otherwise, we check if its parent bases have `media` in the cache,
    # 3. If ALL parent bases have `media` in the cache, we can resolve the child class's `media`,
    #    and put it in the cache.
    # 4. If ANY of the parent bases DOESN'T, then we add those parent bases to the stack (so they are processed
    #    right after this. And we add the child class right after that.
    #
    #    E.g. `stack = [*cls.__bases__, cls, *stack]`
    #
    #    That way, we go up one level of the bases, and then we eventually come back down to the
    #    class that we tried to resolve. But the second time, we will have `media` resolved for all its parent bases.
    bases_stack = deque([comp_cls])
    while bases_stack:
        curr_cls = bases_stack.popleft()

        if curr_cls in media_cache:
            continue

        comp_media: Optional[ComponentMedia] = getattr(curr_cls, "_component_media", None)
        if comp_media is not None and not comp_media.resolved:
            _resolve_media(curr_cls, comp_media)

        # Prepare base classes
        # NOTE: If the `Component.Media` class is explicitly set to `None`, then we should not inherit
        #       from any parent classes.
        #       ```py
        #       class MyComponent(Component):
        #           Media = None
        #       ```
        #       But if the `Component.Media` class is NOT set, then we inherit from the parent classes.
        #       ```py
        #       class MyComponent(Component):
        #           pass
        #       ```
        media_input = getattr(curr_cls, "Media", UNSET)
        default_extend = media_input is not None
        media_extend = getattr(media_input, "extend", default_extend)

        # This ensures the same behavior as Django's Media class, where:
        # - If `Media.extend == True`, then the media files are inherited from the parent classes.
        # - If `Media.extend == False`, then the media files are NOT inherited from the parent classes.
        # - If `Media.extend == [Component1, Component2, ...]`, then the media files are inherited only
        #   from the specified classes.
        if media_extend is True:
            bases = curr_cls.__bases__
        elif media_extend is False:
            bases = ()
        else:
            bases = media_extend

        unresolved_bases = [base for base in bases if base not in media_cache]
        if unresolved_bases:
            # Put the current class's bases at the FRONT of the queue, and put the current class back right after that.
            # E.g. `[parentCls1, parentCls2, currCls, ...]`
            # That way, we first resolve the parent classes, and then the current class.
            bases_stack.extendleft(reversed([*unresolved_bases, curr_cls]))
            continue

        # Now, if we got here, then either all the bases of the current class have had their `media` resolved,
        # or the current class has NO bases. So now we construct the `media` for the current class.
        media_cls = getattr(curr_cls, "media_class", MediaCls)
        # NOTE: If the class is a component and and it was not yet resolved, accessing `Media` should resolve it.
        media_js = getattr(media_input, "js", [])
        media_css = getattr(media_input, "css", {})
        media: MediaCls = media_cls(js=media_js, css=media_css)

        # We have the current class's `media`, now we add the JS and CSS from the parent classes.
        # NOTE: Django's implementation of `Media` should ensure that duplicate files are not added.
        for base in bases:
            base_media = media_cache.get(base, None)
            if base_media is None:
                continue

            # Add JS / CSS from the base class's Media to the current class's Media.
            # We make use of the fact that Django's Media class does this with `__add__` method.
            #
            # However, the `__add__` converts our `media_cls` to Django's Media class.
            # So we also have to convert it back to `media_cls`.
            merged_media = media + base_media
            media = media_cls(js=merged_media._js, css=merged_media._css)

        # Lastly, cache the merged-up Media, so we don't have to search further up the MRO the next time
        media_cache[curr_cls] = media

    return media_cache[comp_cls]


def _resolve_media(comp_cls: Type["Component"], comp_media: ComponentMedia) -> None:
    """
    Resolve the media files associated with the component.

    ### 1. Media are resolved relative to class definition file

    E.g. if in a directory `my_comp` you have `script.js` and `my_comp.py`,
    and `my_comp.py` looks like this:

    ```py
    class MyComponent(Component):
        class Media:
            js = "script.js"
    ```

    Then `script.js` will be understood as relative to the component file.
    To obtain the final path, we make it relative to a component directory (as set in `COMPONENTS.dirs`
    and `COMPONENTS.app_dirs`; and `STATICFILES_DIRS` for JS and CSS). So if the parent directory is `components/`,
    and the component file is inside `components/my_comp/my_comp.py`, then the final path will be relative
    to `components/`, thus `./my_comp/script.js`.

    If the relative path does not point to an actual file, the path is kept as is.

    ### 2. Subclass `Media` class with `media_class`

    Django's `MediaDefiningClass` creates an instance of `Media` class under the `media` attribute.
    We do the same, but we allow to override the class that will be instantiated with `media_class` attribute:

    ```py
    class MyMedia(Media):
        def render_js(self):
            ...

    class MyComponent(Component):
        media_class = MyMedia
        def get_template_data(self, args, kwargs, slots, context):
            assert isinstance(self.media, MyMedia)
    ```
    """
    if comp_media.resolved:
        return

    comp_media.resolved = True

    # Do not resolve if this is a base class
    if get_import_path(comp_cls) == "django_components.component.Component":
        return

    comp_dirs = get_component_dirs()

    # Once the inputs are normalized, attempt to resolve the HTML/JS/CSS filepaths
    # as relative to the directory where the component class is defined.
    _resolve_component_relative_files(comp_cls, comp_media, comp_dirs=comp_dirs)

    # If the component defined `template_file`, `js_file` or `css_file`, instead of `template`/`js`/`css`,
    # we resolve them now.
    # Effectively, even if the Component class defined `js_file` (or others), at "runtime" the `js` attribute
    # will be set to the content of the file.
    # So users can access `Component.js` even if they defined `Component.js_file`.
    template_str, template_obj = _get_asset(
        comp_cls,
        comp_media,
        inlined_attr="template",
        file_attr="template_file",
        comp_dirs=comp_dirs,
    )
    comp_media.template = template_str

    js_str, _ = _get_asset(comp_cls, comp_media, inlined_attr="js", file_attr="js_file", comp_dirs=comp_dirs)
    comp_media.js = js_str

    css_str, _ = _get_asset(comp_cls, comp_media, inlined_attr="css", file_attr="css_file", comp_dirs=comp_dirs)
    comp_media.css = css_str

    # If `Component.template` or `Component.template_file` were explicitly set on this class,
    # then Template instance was already created.
    #
    # Otherwise, search for Template instance in parent classes, and make a copy of it.
    if not isinstance(template_obj, Unset):
        comp_media._template = template_obj
    else:
        parent_template = _get_comp_cls_attr(comp_cls, "_template")

        # One of base classes has set `template` or `template_file` to `None`,
        # or none of the base classes had set `template` or `template_file`
        if parent_template is None:
            comp_media._template = parent_template

        # One of base classes has set `template` or `template_file` to string.
        # Make a copy of the Template instance.
        else:
            comp_media._template = ensure_unique_template(comp_cls, parent_template)


def _normalize_media(media: Type[ComponentMediaInput]) -> None:
    """
    Resolve the `Media` class associated with the component.

    We support following cases:

    1. As plain strings
        ```py
        class MyComponent(Component):
            class Media:
                js = "path/to/script.js"
                css = "path/to/style.css"
        ```

    2. As lists
        ```py
        class MyComponent(Component):
            class Media:
                js = ["path/to/script1.js", "path/to/script2.js"]
                css = ["path/to/style1.css", "path/to/style2.css"]
        ```

    3. [CSS ONLY] Dicts of strings
        ```py
        class MyComponent(Component):
            class Media:
                css = {
                    "all": "path/to/style1.css",
                    "print": "path/to/style2.css",
                }
        ```

    Moreover, unlike Django's Media class, here, the JS/CSS files can be defined as str, bytes, PathLike, SafeString,
    or function of thereof. E.g.:

    ```py
    def lazy_eval_css():
        # do something
        return path

    class MyComponent(Component):
        class Media:
            js = b"script.js"
            css = lazy_eval_css
    ```
    """
    if hasattr(media, "css") and media.css:
        # Allow: class Media: css = "style.css"
        if _is_media_filepath(media.css):
            media.css = {"all": [media.css]}  # type: ignore[assignment]

        # Allow: class Media: css = ["style.css"]
        elif isinstance(media.css, (list, tuple)):
            media.css = {"all": media.css}

        # Allow: class Media: css = {"all": "style.css"}
        #        class Media: css = {"all": ["style.css"]}
        elif isinstance(media.css, dict):
            for media_type, path_or_list in media.css.items():
                # {"all": "style.css"}
                if _is_media_filepath(path_or_list):
                    media.css[media_type] = [path_or_list]  # type: ignore[misc]
                # {"all": ["style.css"]}
                else:
                    media.css[media_type] = path_or_list  # type: ignore[misc]
        else:
            raise ValueError(f"Media.css must be str, list, or dict, got {type(media.css)}")

    if hasattr(media, "js") and media.js:
        # Allow: class Media: js = "script.js"
        if _is_media_filepath(media.js):
            media.js = [media.js]  # type: ignore[misc]
        # Allow: class Media: js = ["script.js"]
        else:
            # JS is already a list, no action needed
            pass

    # Now that the Media class has a predictable shape, get all the various JS/CSS paths
    # that user has defined, and normalize them too.
    #
    # Because we can accept:
    # str, bytes, PathLike, SafeData (AKA Django's "path as object") or a callable
    #
    # And we want to convert that to:
    # str and SafeData
    _map_media_filepaths(media, _normalize_media_filepath)


def _map_media_filepaths(media: Type[ComponentMediaInput], map_fn: Callable[[Sequence[Any]], Iterable[Any]]) -> None:
    if hasattr(media, "css") and media.css:
        if not isinstance(media.css, dict):
            raise ValueError(f"Media.css must be a dict, got {type(media.css)}")

        for media_type, path_list in media.css.items():
            media.css[media_type] = list(map_fn(path_list))  # type: ignore[assignment]

    if hasattr(media, "js") and media.js:
        if not isinstance(media.js, (list, tuple)):
            raise ValueError(f"Media.css must be a list, got {type(media.css)}")

        media.js = list(map_fn(media.js))


def _is_media_filepath(filepath: Any) -> bool:
    # Case callable
    if callable(filepath):
        return True

    # Case SafeString
    if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
        return True

    # Case PathLike
    if isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
        return True

    # Case bytes
    if isinstance(filepath, bytes):
        return True

    # Case str
    return isinstance(filepath, str)


def _normalize_media_filepath(filepaths: Sequence[ComponentMediaInputPath]) -> List[Union[str, SafeData]]:
    normalized: List[Union[str, SafeData]] = []
    for filepath in filepaths:
        if callable(filepath):
            filepath = filepath()  # noqa: PLW2901

        if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
            normalized.append(filepath)
            continue

        if isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
            # In case of Windows OS, convert to forward slashes
            filepath = Path(filepath.__fspath__()).as_posix()  # noqa: PLW2901

        if isinstance(filepath, bytes):
            filepath = filepath.decode("utf-8")  # noqa: PLW2901

        if isinstance(filepath, str):
            normalized.append(filepath)
            continue

        raise ValueError(
            f"Unknown filepath {filepath} of type {type(filepath)}. Must be str, bytes, PathLike, SafeString,"
            " or a function that returns one of the former",
        )

    return normalized


def _resolve_component_relative_files(
    comp_cls: Type["Component"],
    comp_media: ComponentMedia,
    comp_dirs: List[Path],
) -> None:
    """
    Check if component's HTML, JS and CSS files refer to files in the same directory
    as the component class. If so, modify the attributes so the class Django's rendering
    will pick up these files correctly.
    """
    if comp_media.resolved_relative_files:
        return

    comp_media.resolved_relative_files = True

    # First check if we even need to resolve anything. If the class doesn't define any
    # HTML/JS/CSS files, just skip.
    will_resolve_files = False
    if is_set(comp_media.template_file) or is_set(comp_media.js_file) or is_set(comp_media.css_file):
        will_resolve_files = True
    elif not will_resolve_files and is_set(comp_media.Media):
        has_media_files = getattr(comp_media.Media, "css", None) or getattr(comp_media.Media, "js", None)
        if has_media_files:
            will_resolve_files = True

    if not will_resolve_files:
        return

    component_name = comp_cls.__qualname__
    # Get the full path of the file where the component was defined
    _module, module_name, module_file_path = get_module_info(comp_cls)
    if not module_file_path:
        logger.debug(
            f"Could not resolve the path to the file for component '{component_name}'."
            " Paths for HTML, JS or CSS templates will NOT be resolved relative to the component file.",
        )
        return

    # Get the directory where the component class is defined
    matched_component_dir = _find_component_dir_containing_file(comp_dirs, module_file_path)

    # If no dir was found (e.g. the component was defined at runtime), we assume that the media paths
    # are NOT relative.
    if matched_component_dir is None:
        logger.debug(
            f"No component directory found for component '{component_name}' in {module_file_path}"
            " If this component defines HTML, JS or CSS templates relatively to the component file,"
            " then check that the component's directory is accessible from one of the paths"
            " specified in the Django's 'COMPONENTS.dirs' settings.",
        )
        return

    matched_component_dir_abs = os.path.abspath(matched_component_dir)
    # Derive the path from matched `COMPONENTS.dirs` to the dir where the current component file is.
    component_module_dir_path_abs = os.path.dirname(module_file_path)

    # Check if filepath refers to a file that's in the same directory as the component class.
    # If yes, modify the path to refer to the relative file.
    # If not, don't modify anything.
    def resolve_relative_media_file(
        filepath: Union[str, SafeData],
        allow_glob: bool,
    ) -> List[Union[str, SafeData]]:
        resolved_filepaths, has_matched = resolve_media_file(
            filepath,
            allow_glob,
            static_files_dir=matched_component_dir_abs,
            media_root_dir=component_module_dir_path_abs,
        )

        # NOTE: It's important to use `repr`, so we don't trigger __str__ on SafeStrings
        if has_matched:
            logger.debug(
                f"Interpreting file '{filepath!r}' of component '{module_name}' relatively to component file",
            )
        else:
            logger.debug(
                f"Interpreting file '{filepath!r}' of component '{module_name}' relatively to components directory",
            )

        return resolved_filepaths

    # Check if filepath is a glob pattern that points to files relative to the components directory
    # (as defined by `COMPONENTS.dirs` and `COMPONENTS.app_dirs` settings) in which the component is defined.
    # If yes, modify the path to refer to the globbed files.
    # If not, don't modify anything.
    def resolve_static_media_file(
        filepath: Union[str, SafeData],
        allow_glob: bool,
    ) -> List[Union[str, SafeData]]:
        resolved_filepaths, _ = resolve_media_file(
            filepath,
            allow_glob,
            static_files_dir=matched_component_dir_abs,
            media_root_dir=matched_component_dir_abs,
        )
        return resolved_filepaths

    # Check if template name is a local file or not
    if is_set(comp_media.template_file):
        comp_media.template_file = resolve_relative_media_file(comp_media.template_file, allow_glob=False)[0]
    if is_set(comp_media.js_file):
        comp_media.js_file = resolve_relative_media_file(comp_media.js_file, allow_glob=False)[0]
    if is_set(comp_media.css_file):
        comp_media.css_file = resolve_relative_media_file(comp_media.css_file, allow_glob=False)[0]

    if is_set(comp_media.Media):
        _map_media_filepaths(
            comp_media.Media,
            # Media files can be defined as a glob patterns that match multiple files.
            # Thus, flatten the list of lists returned by `resolve_relative_media_file`.
            lambda filepaths: flatten(resolve_relative_media_file(f, allow_glob=True) for f in filepaths),
        )

        # Go over the JS / CSS media files again, but this time, if there are still any globs,
        # try to resolve them relative to the root directory (as defined by `COMPONENTS.dirs
        # and `COMPONENTS.app_dirs` settings).
        _map_media_filepaths(
            comp_media.Media,
            # Media files can be defined as a glob patterns that match multiple files.
            # Thus, flatten the list of lists returned by `resolve_static_media_file`.
            lambda filepaths: flatten(resolve_static_media_file(f, allow_glob=True) for f in filepaths),
        )


# Check if filepath refers to a file that's in the same directory as the component class.
# If yes, modify the path to refer to the relative file.
# If not, don't modify anything.
def resolve_media_file(
    filepath: Union[str, SafeData],
    allow_glob: bool,
    static_files_dir: str,
    media_root_dir: str,
) -> Tuple[List[Union[str, SafeData]], bool]:
    # If filepath is NOT a string, then return as is
    if not isinstance(filepath, str):
        return [filepath], False

    filepath_abs_or_glob = os.path.join(media_root_dir, filepath)

    # If the path is a URL, don't resolve it
    # (e.g. https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.0.2/chart.min.js)
    # This is defined based on Django's `Media.absolute_path()` method.
    is_url_path = filepath.startswith(("http://", "https://", "://", "/"))

    # If the path is a URL, don't resolve it
    if is_url_path:
        return [filepath], False

    # The path may be a glob, which we need to resolve
    if allow_glob and is_glob(filepath_abs_or_glob):
        # Since globs are matched against the files, then we know that these files exist.
        matched_abs_filepaths = glob.glob(filepath_abs_or_glob)
    # But if we were given non-glob file path, then we need to check if it exists.
    elif Path(filepath_abs_or_glob).exists():
        matched_abs_filepaths = [filepath_abs_or_glob]
    else:
        matched_abs_filepaths = []

    # If there are no matches, return the original filepath
    if not matched_abs_filepaths:
        return [filepath], False

    resolved_filepaths: List[str] = []
    for matched_filepath_abs in matched_abs_filepaths:
        # Derive the path from matched `COMPONENTS.dirs` to the media file.
        # NOTE: The paths to resources need to use POSIX (forward slashes) for Django to work
        #       See https://github.com/django-components/django-components/issues/796
        # NOTE: Since these paths matched the glob, we know that these files exist.
        filepath_rel_to_comp_dir = Path(os.path.relpath(matched_filepath_abs, static_files_dir)).as_posix()
        resolved_filepaths.append(filepath_rel_to_comp_dir)

    return resolved_filepaths, True


def _find_component_dir_containing_file(
    component_dirs: Sequence[Union[str, Path]],
    target_file_path: str,
) -> Optional[Union[str, Path]]:
    """
    From all directories that may contain components (such as those defined in `COMPONENTS.dirs`),
    find the one that's the parent to the given file.
    """
    abs_target_file_path = os.path.abspath(target_file_path)

    for component_dir in component_dirs:
        component_dir_abs = os.path.abspath(component_dir)
        if abs_target_file_path.startswith(component_dir_abs):
            return component_dir

    return None


def _get_asset(
    comp_cls: Type["Component"],
    comp_media: ComponentMedia,
    inlined_attr: Literal["template", "js", "css"],
    file_attr: Literal["template_file", "js_file", "css_file"],
    comp_dirs: List[Path],
) -> Tuple[Union[str, Unset, None], Union[Template, Unset, None]]:  # Tuple of (content, Template)
    """
    In case of Component's JS or CSS, one can either define that as "inlined" or as a file.

    E.g.
    ```python
    class MyComp(Component):
        js = '''
            console.log('Hello, world!');
        '''
    ```
    or
    ```python
    class MyComp(Component):
        js_file = "my_comp.js"
    ```

    This method resolves the content like above.

    - `inlined_attr` - The attribute name for the inlined content.
    - `file_attr` - The attribute name for the file name.

    These are mutually exclusive, so only one of the two can be set at class creation.
    """
    asset_content = getattr(comp_media, inlined_attr, UNSET)
    asset_file = getattr(comp_media, file_attr, UNSET)

    # No inlined content, nor file name
    # ```py
    # class MyComp(Component):
    #     pass
    # ```
    if asset_content is UNSET and asset_file is UNSET:
        return UNSET, UNSET

    # Either file or content attr was set to `None`
    # ```py
    # class MyComp(Component):
    #     js_file = None
    # ```
    # or
    # ```py
    # class MyComp(Component):
    #     js = None
    # ```
    # or
    # ```py
    # class MyComp(Component):
    #     js = None
    #     js_file = None
    # ```
    if (asset_content in (UNSET, None) and asset_file is None) or (
        asset_content is None and asset_file in (UNSET, None)
    ):
        return None, None

    # Received both inlined content and file name
    # ```py
    # class MyComp(Component):
    #     js = "..."
    #     js_file = "..."
    # ```
    #
    # Or received file name / content AND explicit `None`
    # ```py
    # class MyComp(Component):
    #     js = "..."
    #     js_file = None
    # ```
    # or
    # ```py
    # class MyComp(Component):
    #     js = None
    #     js_file = "..."
    # ```
    if asset_content is not UNSET and asset_file is not UNSET:
        raise ValueError(
            f"Received both '{inlined_attr}' and '{file_attr}' in Component {comp_cls.__qualname__}."
            " Only one of the two must be set.",
        )

    # At this point we can tell that only EITHER `asset_content` OR `asset_file` is set.

    # If the content was inlined into the component (e.g. `Component.template = "..."`)
    # then there's nothing to resolve. Use it as is.
    if not isinstance(asset_content, Unset):
        if asset_content is None:
            return None, None

        content: str = asset_content

        # If we got inlined `Component.template`, then create a Template instance from it
        # to trigger the extension hooks that may modify the template string.
        if inlined_attr == "template":
            # NOTE: `load_component_template()` applies `on_template_loaded()` and `on_template_compiled()` hooks.
            template = load_component_template(comp_cls, filepath=None, content=content)
            return template.source, template

    # This else branch assumes that we were given a file name (possibly None)
    # Load the contents of the file.
    else:
        if asset_file is None:
            return None, None

        asset_file = cast("str", asset_file)

        if inlined_attr == "template":
            # NOTE: `load_component_template()` applies `on_template_loaded()` and `on_template_compiled()` hooks.
            template = load_component_template(comp_cls, filepath=asset_file, content=None)
            return template.source, template

        # Following code concerns with loading JS / CSS files.
        # Here we have a few options:
        #
        # 1. Check if the file is in one of the components' directories
        full_path = resolve_file(asset_file, comp_dirs)

        # 2. If not, check if it's in the static files
        if full_path is None:
            full_path = finders.find(asset_file)

        if full_path is None:
            # NOTE: The short name, e.g. `js` or `css` is used in the error message for convenience
            raise ValueError(f"Could not find {inlined_attr} file {asset_file}")

        # NOTE: Use explicit encoding for compat with Windows, see #1074
        content = Path(full_path).read_text(encoding="utf8")

    # NOTE: `on_template_loaded()` is already applied inside `load_component_template()`
    #       but we still need to call extension hooks for JS / CSS content (whether inlined or not).
    if inlined_attr == "js":
        content = extensions.on_js_loaded(
            OnJsLoadedContext(
                component_cls=comp_cls,
                content=content,
            ),
        )
    elif inlined_attr == "css":
        content = extensions.on_css_loaded(
            OnCssLoadedContext(
                component_cls=comp_cls,
                content=content,
            ),
        )

    return content, None


def is_set(value: Union[T, Unset, None]) -> TypeGuard[T]:
    return value is not None and value is not UNSET
