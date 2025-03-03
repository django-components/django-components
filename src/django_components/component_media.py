import os
import sys
from collections import deque
from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Protocol, Tuple, Type, Union, cast

from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media as MediaCls
from django.template import Template, TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.safestring import SafeData

from django_components.util.loader import get_component_dirs, resolve_file
from django_components.util.logger import logger
from django_components.util.misc import get_import_path

if TYPE_CHECKING:
    from django_components.component import Component


# These are all the attributes that are handled by ComponentMedia and lazily-resolved
COMP_MEDIA_LAZY_ATTRS = ("media", "template", "template_file", "js", "js_file", "css", "css_file")


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

    Read more in [Controlling Media Inheritance](../concepts/fundamentals/defining_js_css_html_files.md#controlling-media-inheritance) section.

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
    """  # noqa: E501


@dataclass
class ComponentMedia:
    comp_cls: Type["Component"]
    resolved: bool = False
    Media: Optional[Type[ComponentMediaInput]] = None
    template: Optional[str] = None
    template_file: Optional[str] = None
    js: Optional[str] = None
    js_file: Optional[str] = None
    css: Optional[str] = None
    css_file: Optional[str] = None

    def __post_init__(self) -> None:
        for inlined_attr in ("template", "js", "css"):
            file_attr = f"{inlined_attr}_file"
            if getattr(self, inlined_attr) is not None and getattr(self, file_attr) is not None:
                raise ImproperlyConfigured(
                    f"Received non-null value from both '{inlined_attr}' and '{file_attr}' in"
                    f" Component {self.comp_cls.__name__}. Only one of the two must be set."
                )
        # Make a copy of the original state, so we can reset it in tests
        self._original = copy(self)

    # Return ComponentMedia to its original state before the media was resolved
    def reset(self) -> None:
        self.__dict__.update(self._original.__dict__)
        self.resolved = False


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
        comp_cls = cast(Type["Component"], cls)

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
                print(
                    f"WARNING: Setting attribute '{name}' on component '{cls.__name__}' after the media files were"
                    " already resolved. This may lead to unexpected behavior."
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
        Media=attrs.get("Media", None),
        template=attrs.get("template", None),
        template_file=attrs.get("template_file", None),
        js=attrs.get("js", None),
        js_file=attrs.get("js_file", None),
        css=attrs.get("css", None),
        css_file=attrs.get("css_file", None),
    )

    def get_comp_media_attr(attr: str) -> Any:
        if attr == "media":
            return _get_comp_cls_media(comp_cls)
        else:
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
        value = getattr(comp_media, attr, None)

        # For each of the pairs of inlined_content + file (e.g. `js` + `js_file`), if at least one of the two
        # is defined, we interpret it such that this (sub)class has overridden what was set by the parent class(es),
        # and we won't search further up the MRO.
        def check_pair_empty(inline_attr: str, file_attr: str) -> bool:
            inline_attr_empty = getattr(comp_media, inline_attr, None) is None
            file_attr_empty = getattr(comp_media, file_attr, None) is None
            return inline_attr_empty and file_attr_empty

        if attr in ("js", "js_file"):
            if check_pair_empty("js", "js_file"):
                continue
            else:
                return value
        if attr in ("css", "css_file"):
            if check_pair_empty("css", "css_file"):
                continue
            else:
                return value
        if attr in ("template", "template_file"):
            if check_pair_empty("template", "template_file"):
                continue
            else:
                return value

        # For the other attributes, simply search for the closest non-null
        if value is not None:
            return value
    return None


media_cache: Dict[Type["Component"], MediaCls] = {}


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

        # Prepare base classes
        media_input = getattr(curr_cls, "Media", None)
        media_extend = getattr(media_input, "extend", True)

        # This ensures the same behavior as Django's Media class, where:
        # - If `Media.extend == True`, then the media files are inherited from the parent classes.
        # - If `Media.extend == False`, then the media files are NOT inherited from the parent classes.
        # - If `Media.extend == [Component1, Component2, ...]`, then the media files are inherited only
        #   from the specified classes.
        if media_extend is True:
            bases = curr_cls.__bases__
        elif media_extend is False:
            bases = tuple()
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
        def get_context_data(self):
            assert isinstance(self.media, MyMedia)
    ```
    """
    # Do not resolve if this is a base class
    if get_import_path(comp_cls) == "django_components.component.Component" or comp_media.resolved:
        comp_media.resolved = True
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
    comp_media.template = _get_asset(
        comp_cls,
        comp_media,
        inlined_attr="template",
        file_attr="template_file",
        comp_dirs=comp_dirs,
        type="template",
    )
    comp_media.js = _get_asset(
        comp_cls, comp_media, inlined_attr="js", file_attr="js_file", comp_dirs=comp_dirs, type="static"
    )
    comp_media.css = _get_asset(
        comp_cls, comp_media, inlined_attr="css", file_attr="css_file", comp_dirs=comp_dirs, type="static"
    )

    comp_media.resolved = True


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
                    media.css[media_type] = [path_or_list]  # type: ignore
                # {"all": ["style.css"]}
                else:
                    media.css[media_type] = path_or_list  # type: ignore
        else:
            raise ValueError(f"Media.css must be str, list, or dict, got {type(media.css)}")

    if hasattr(media, "js") and media.js:
        # Allow: class Media: js = "script.js"
        if _is_media_filepath(media.js):
            media.js = [media.js]  # type: ignore
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


def _map_media_filepaths(media: Type[ComponentMediaInput], map_fn: Callable[[Any], Any]) -> None:
    if hasattr(media, "css") and media.css:
        if not isinstance(media.css, dict):
            raise ValueError(f"Media.css must be a dict, got {type(media.css)}")

        for media_type, path_list in media.css.items():
            media.css[media_type] = list(map(map_fn, path_list))  # type: ignore[assignment]

    if hasattr(media, "js") and media.js:
        if not isinstance(media.js, (list, tuple)):
            raise ValueError(f"Media.css must be a list, got {type(media.css)}")

        media.js = list(map(map_fn, media.js))


def _is_media_filepath(filepath: Any) -> bool:
    if callable(filepath):
        return True

    if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
        return True

    elif isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
        return True

    if isinstance(filepath, bytes):
        return True

    if isinstance(filepath, str):
        return True

    return False


def _normalize_media_filepath(filepath: ComponentMediaInputPath) -> Union[str, SafeData]:
    if callable(filepath):
        filepath = filepath()

    if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
        return filepath

    if isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
        # In case of Windows OS, convert to forward slashes
        filepath = Path(filepath.__fspath__()).as_posix()

    if isinstance(filepath, bytes):
        filepath = filepath.decode("utf-8")

    if isinstance(filepath, str):
        return filepath

    raise ValueError(
        "Unknown filepath. Must be str, bytes, PathLike, SafeString, or a function that returns one of the former"
    )


def _resolve_component_relative_files(
    comp_cls: Type["Component"], comp_media: ComponentMedia, comp_dirs: List[Path]
) -> None:
    """
    Check if component's HTML, JS and CSS files refer to files in the same directory
    as the component class. If so, modify the attributes so the class Django's rendering
    will pick up these files correctly.
    """
    # First check if we even need to resolve anything. If the class doesn't define any
    # HTML/JS/CSS files, just skip.
    will_resolve_files = False
    if (
        getattr(comp_media, "template_file", None)
        or getattr(comp_media, "js_file", None)
        or getattr(comp_media, "css_file", None)
    ):
        will_resolve_files = True
    elif not will_resolve_files and getattr(comp_media, "Media", None):
        if getattr(comp_media.Media, "css", None) or getattr(comp_media.Media, "js", None):
            will_resolve_files = True

    if not will_resolve_files:
        return

    component_name = comp_cls.__qualname__
    # Derive the full path of the file where the component was defined
    module_name = comp_cls.__module__
    module_obj = sys.modules[module_name]
    file_path = module_obj.__file__

    if not file_path:
        logger.debug(
            f"Could not resolve the path to the file for component '{component_name}'."
            " Paths for HTML, JS or CSS templates will NOT be resolved relative to the component file."
        )
        return

    # Get the directory where the component class is defined
    try:
        comp_dir_abs, comp_dir_rel = _get_dir_path_from_component_path(file_path, comp_dirs)
    except RuntimeError:
        # If no dir was found, we assume that the path is NOT relative to the component dir
        logger.debug(
            f"No component directory found for component '{component_name}' in {file_path}"
            " If this component defines HTML, JS or CSS templates relatively to the component file,"
            " then check that the component's directory is accessible from one of the paths"
            " specified in the Django's 'COMPONENTS.dirs' settings."
        )
        return

    # Check if filepath refers to a file that's in the same directory as the component class.
    # If yes, modify the path to refer to the relative file.
    # If not, don't modify anything.
    def resolve_media_file(filepath: Union[str, SafeData]) -> Union[str, SafeData]:
        if isinstance(filepath, str):
            filepath_abs = os.path.join(comp_dir_abs, filepath)
            # NOTE: The paths to resources need to use POSIX (forward slashes) for Django to wor
            #       See https://github.com/django-components/django-components/issues/796
            filepath_rel_to_comp_dir = Path(os.path.join(comp_dir_rel, filepath)).as_posix()

            if os.path.isfile(filepath_abs):
                # NOTE: It's important to use `repr`, so we don't trigger __str__ on SafeStrings
                logger.debug(
                    f"Interpreting template '{repr(filepath)}' of component '{module_name}'"
                    " relatively to component file"
                )

                return filepath_rel_to_comp_dir

        # If resolved absolute path does NOT exist or filepath is NOT a string, then return as is
        logger.debug(
            f"Interpreting template '{repr(filepath)}' of component '{module_name}'"
            " relatively to components directory"
        )
        return filepath

    # Check if template name is a local file or not
    if getattr(comp_media, "template_file", None):
        comp_media.template_file = resolve_media_file(comp_media.template_file)
    if getattr(comp_media, "js_file", None):
        comp_media.js_file = resolve_media_file(comp_media.js_file)
    if getattr(comp_media, "css_file", None):
        comp_media.css_file = resolve_media_file(comp_media.css_file)

    if hasattr(comp_media, "Media") and comp_media.Media:
        _map_media_filepaths(comp_media.Media, resolve_media_file)


def _get_dir_path_from_component_path(
    abs_component_file_path: str,
    candidate_dirs: Union[List[str], List[Path]],
) -> Tuple[str, str]:
    comp_dir_path_abs = os.path.dirname(abs_component_file_path)

    # From all dirs defined in settings.COMPONENTS.dirs, find one that's the parent
    # to the component file.
    root_dir_abs = None
    for candidate_dir in candidate_dirs:
        candidate_dir_abs = os.path.abspath(candidate_dir)
        if comp_dir_path_abs.startswith(candidate_dir_abs):
            root_dir_abs = candidate_dir_abs
            break

    if root_dir_abs is None:
        raise RuntimeError(
            f"Failed to resolve template directory for component file '{abs_component_file_path}'",
        )

    # Derive the path from matched COMPONENTS.dirs to the dir where the current component file is.
    comp_dir_path_rel = os.path.relpath(comp_dir_path_abs, candidate_dir_abs)

    # Return both absolute and relative paths:
    # - Absolute path is used to check if the file exists
    # - Relative path is used for defining the import on the component class
    return comp_dir_path_abs, comp_dir_path_rel


def _get_asset(
    comp_cls: Type["Component"],
    comp_media: ComponentMedia,
    inlined_attr: str,
    file_attr: str,
    comp_dirs: List[Path],
    type: Literal["template", "static"],
) -> Optional[str]:
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
    asset_content = getattr(comp_media, inlined_attr, None)
    asset_file = getattr(comp_media, file_attr, None)

    if asset_file is not None:
        # Check if the file is in one of the components' directories
        full_path = resolve_file(asset_file, comp_dirs)

        if full_path is None:
            # If not, check if it's in the static files
            if type == "static":
                full_path = finders.find(asset_file)
            # Or in the templates
            elif type == "template":
                try:
                    template: Template = get_template(asset_file)
                    full_path = template.origin.name
                except TemplateDoesNotExist:
                    pass

        if full_path is None:
            # NOTE: The short name, e.g. `js` or `css` is used in the error message for convenience
            raise ValueError(f"Could not find {inlined_attr} file {asset_file}")
        asset_content = Path(full_path).read_text()

    return asset_content
