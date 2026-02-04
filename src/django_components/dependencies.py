"""All code related to management of component dependencies (JS and CSS scripts)"""

import base64
import html.parser
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import md5
from typing import (
    TYPE_CHECKING,
    Literal,
    NamedTuple,
    TypeAlias,
    TypeVar,
    cast,
)

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseNotFound
from django.template import Context, TemplateSyntaxError
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.safestring import SafeString, mark_safe
from djc_core.html_transformer import set_html_attributes

from django_components.attributes import format_attributes
from django_components.cache import get_component_media_cache
from django_components.extension import OnDependenciesContext, extensions
from django_components.node import BaseNode
from django_components.util.css import serialize_css_var_value
from django_components.util.misc import extract_regex_matches, is_nonempty_str

if TYPE_CHECKING:
    from django_components.component import Component


TDep = TypeVar("TDep", bound="Dependency")


ScriptType: TypeAlias = Literal["css", "js"]
InternalDependenciesStrategy: TypeAlias = Literal["document", "fragment", "simple"]
DependenciesStrategy: TypeAlias = Literal["document", "fragment", "simple", "prepend", "append", "ignore"]
"""
Type for the available strategies for rendering JS and CSS dependencies.

Read more about the [dependencies strategies](../concepts/advanced/rendering_js_css.md).
"""

DEPS_STRATEGIES = ("document", "fragment", "simple", "prepend", "append", "ignore")


DependencyKind: TypeAlias = Literal["component", "variables", "core", "extra"]
"""
Type for the kind of [`Dependency`](api.md#django_components.Dependency) objects.

- `"core"`: Required for Django Components library to work.
- `"component"`: Dependency from a component's `Component.js` or `Component.css`.
- `"variables"`: Dependency from a component's JS/CSS variables.
- `"extra"`: Any other dependencies, e.g. from `Component.Media.js/css`.
"""

# JavaScript MIME type essence and legacy types (classic script).
# See https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types#textjavascript
_JAVASCRIPT_MIME_TYPES = frozenset(
    {
        "text/javascript",
        "application/javascript",
        "application/ecmascript",
        "application/x-ecmascript",
        "application/x-javascript",
        "text/ecmascript",
        "text/javascript1.0",
        "text/javascript1.1",
        "text/javascript1.2",
        "text/javascript1.3",
        "text/javascript1.4",
        "text/javascript1.5",
        "text/jscript",
        "text/livescript",
        "text/x-ecmascript",
        "text/x-javascript",
    }
)


def _script_type_should_wrap(attrs: dict[str, str | bool]) -> bool:
    """
    Return True if inline script content should be wrapped in an IIFE.

    Wrap when: no type, empty type, or a JavaScript MIME type (classic script).

    Do not wrap when: type is "importmap", "module", "speculationrules", or any other value.

    See https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/script/type
    """
    type_val = attrs.get("type")

    # No type attribute, or empty type attribute
    if type_val is None:
        return True
    # Boolean attribute - same as no type attribute
    if isinstance(type_val, bool):
        return True

    type_str = (type_val.strip().lower() if isinstance(type_val, str) else str(type_val)).strip()

    # "text/javascript", etc
    if type_str == "" or type_str in _JAVASCRIPT_MIME_TYPES:  # noqa: SIM103
        return True
    # "importmap", "module", "speculationrules", etc are not classic JS
    return False


@dataclass
class Dependency:
    """
    Base class for JS/CSS dependency that will be rendered as `<script>`, `<style>`,
    or `<link>` tag.

    The content of the dependency (JS/CSS) can be either:

    - Inlined as content (`<script>...</script>` or `<style>...</style>`)
    - Fetched from a URL (`<script src="...">` or `<link rel="stylesheet" href="...">`)

    Read more about [Rendering JS and CSS](../concepts/advanced/rendering_js_css.md).
    """

    content: str | None
    """Text inside the `<script>` or `<style>` tag. Can be `None` for external dependencies."""
    url: str | None = None
    """If set, will render as `<script src="...">` or `<link rel="stylesheet" href="...">`.
    Otherwise renders as `<script>...</script>` or `<style>...</style>`."""
    attrs: dict[str, str | bool] = field(default_factory=dict)
    """Extra HTML attributes (values can be `True` for boolean attributes)"""
    kind: DependencyKind = "extra"
    """
    Metadata about the kind of dependency:

    - `"core"`: Required for Django Components library to work.
    - `"component"`: Dependency from a component's `Component.js` or `Component.css`.
    - `"variables"`: Dependency from a component's JS/CSS variables.
    - `"extra"`: Any other dependencies, e.g. from `Component.Media.js/css`.
    """
    origin_class_id: str | None = None
    """The class ID of the component that originated this dependency."""

    def _render(self) -> tuple[str, dict[str, str | bool], str]:
        """Return (tag_name, all_attrs, content). Override in subclasses."""
        raise NotImplementedError

    def render(self) -> SafeString:
        """Render as HTML tag."""
        tag_name, all_attrs, content = self._render()
        attrs_str = format_attributes(all_attrs)
        attrs_prefix = " " + attrs_str if attrs_str else ""
        return mark_safe(f"<{tag_name}{attrs_prefix}>{content}</{tag_name}>")  # type: ignore[return-value]

    def __html__(self) -> SafeString:
        """Return rendered HTML so Script/Style can be used in Component.Media.js/css as `SafeString`."""
        return self.render()

    def render_json(self) -> dict[str, str | dict[str, str | bool]]:
        """Render as JSON object with tag, attrs, and content fields."""
        tag_name, all_attrs, content = self._render()
        return {
            "tag": tag_name,
            "attrs": all_attrs,
            "content": content,
        }

    def _check_validity(self) -> None:
        if self.url and self.content:
            raise ValueError(f"{self._err_msg()} cannot have both `src`/`href` and `content`")
        if not self.url and not self.content:
            raise ValueError(f"{self._err_msg()} must have either `src`/`href` or `content`")

        # The script content CANNOT contain its own closing tag
        # e.g. JS code CANNOT contain `</script>`
        tag_name = self.__class__.__name__.lower()
        end_tag_substr = f"</{tag_name}"
        if self.content and end_tag_substr in self.content:
            raise RuntimeError(
                f"{self._err_msg()} contains '{end_tag_substr}>' end tag. This is not allowed.",
            )

    def _err_msg(self) -> str:
        if self.origin_class_id:
            return f"{self.__class__.__name__} for component '{self.origin_class_id}'"
        return self.__class__.__name__

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        return self is other


@dataclass
class Script(Dependency):
    """
    Represents a `<script>` tag with content and attributes.

    Modify this object to change the attributes or content of the rendered `<script>` tag.

    If `Script.url` is set, renders as `<script src="...">`, otherwise renders as `<script>...</script>`.

    **Example:**

    ```python
    from django_components import Script

    script = Script(
        content="console.log('Hello, world!');",
        attrs={"type": "module"},
        wrap=False,
    )
    ```

    becomes

    ```html
    <script type="module">
        console.log('Hello, world!');
    </script>
    ```
    """

    wrap: bool = True
    """
    If True, wrap the JS content in a self-executing function.
    Only applies when the script type is absent or a JS MIME type.

    See https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/script/type

    **Example**

    ```python
    from django_components import Script

    Script(
        content="console.log('Hello, world!');",
        wrap=True,
    )
    ```

    becomes

    ```html
    <script>
        (function() {
            console.log("Hello, world!");
        })();
    </script>
    ```
    """

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "url": self.url,
            "content": self.content,
            "attrs": self.attrs,
            "wrap": self.wrap,
            "origin_class_id": self.origin_class_id,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Script":
        return cls(
            kind=data["kind"],
            content=data["content"],
            url=data["url"],
            attrs=data["attrs"],
            wrap=data["wrap"],
            origin_class_id=data["origin_class_id"],
        )

    def _render(self) -> tuple[str, dict[str, str | bool], str]:
        self._check_validity()
        if self.url:
            all_attrs = {**self.attrs, "src": self.url}
            content = ""
        else:
            all_attrs = self.attrs
            content = self.content or ""
            if content and self.wrap and _script_type_should_wrap(all_attrs):
                content = f"(function() {{\n{content}\n}})();"
        return ("script", all_attrs, content)

    def __hash__(self) -> int:
        # Identify by URL or content, fallback to object ID
        if self.url:
            return hash((type(self).__name__, self.url))
        if self.content is not None:
            return hash((type(self).__name__, self.content))
        return id(self)

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other) or not isinstance(other, Script):
            return False

        # Compare by URL or content, fallback to object equality
        if self.url and other.url:
            return self.url == other.url
        if not self.url and not other.url and self.content is not None and other.content is not None:
            return self.content == other.content
        return id(self) == id(other)


@dataclass
class Style(Dependency):
    """
    Represents a `<style>` tag or `<link rel="stylesheet">` tag for stylesheets.

    Modify this object to change the attributes or content of the rendered `<link>` or `<style>` tag.

    If `Style.url` is set, renders as `<link rel="stylesheet" href="...">`,
    otherwise renders as `<style>...</style>`.

    **Example:**

    ```python
    from django_components import Style

    style = Style(
        url="/static/style.css",
        attrs={"media": "print"},
    )
    ```

    becomes

    ```html
    <link rel="stylesheet" href="/static/style.css" media="print">
    ```
    """

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "url": self.url,
            "content": self.content,
            "attrs": self.attrs,
            "origin_class_id": self.origin_class_id,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Style":
        return cls(
            kind=data["kind"],
            content=data["content"],
            url=data["url"],
            attrs=data["attrs"],
            origin_class_id=data["origin_class_id"],
        )

    def _render(self) -> tuple[str, dict[str, str | bool], str]:
        """Shared rendering logic that for rendering."""
        self._check_validity()

        if self.url:
            all_attrs = {**self.attrs, "rel": "stylesheet", "href": self.url}
            tag_name = "link"
            content = ""  # <link> tags are self-closing
        else:
            all_attrs = self.attrs
            tag_name = "style"
            content = self.content or ""
        return (tag_name, all_attrs, content)

    def render(self) -> SafeString:
        tag_name, all_attrs, content = self._render()
        attrs_str = format_attributes(all_attrs)
        attrs_prefix = " " + attrs_str if attrs_str else ""

        # Render as `<link>` tag if url is present, otherwise as `<style>` tag
        if tag_name == "link":
            html = f"<link{attrs_prefix}>"
        else:
            html = f"<style{attrs_prefix}>{content}</style>"
        return mark_safe(html)  # type: ignore[return-value]

    def __hash__(self) -> int:
        # Identify by URL or content, fallback to object ID
        if self.url:
            return hash((type(self).__name__, self.url))
        if self.content is not None:
            return hash((type(self).__name__, self.content))
        return id(self)

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other) or not isinstance(other, Style):
            return False

        # Compare by URL or content, fallback to object equality
        if self.url and other.url:
            return self.url == other.url
        if not self.url and not other.url and self.content is not None and other.content is not None:
            return self.content == other.content
        return id(self) == id(other)


class ComponentJsVars(NamedTuple):
    comp_cls_id: str
    variables_hash: str
    json_data: str


class ComponentCall(NamedTuple):
    comp_cls_id: str
    comp_id: str
    js_input_hash: str | None


class VariableData(NamedTuple):
    comp_cls_id: str
    script_type: ScriptType
    variables_hash: str | None


#########################################################
# 1. Cache the inlined component JS and CSS scripts (`Component.js` and `Component.css`).
#
#    To support HTML fragments, when a fragment is loaded on a page,
#    we on-demand request the JS and CSS files of the components that are
#    referenced in the fragment.
#
#    Thus, we need to persist the JS and CSS files across requests. These are then accessed
#    via `cached_script_view` endpoint.
#########################################################


# Generate keys like
# `__components:MyButton_a78y37:js:df7c6d10`
# `__components:MyButton_a78y37:css`
def _gen_cache_key(
    comp_cls_id: str,
    script_type: ScriptType,
    variables_hash: str | None,
) -> str:
    if variables_hash:
        return f"__components:{comp_cls_id}:{script_type}:{variables_hash}"
    return f"__components:{comp_cls_id}:{script_type}"


def _is_script_in_cache(
    comp_cls: type["Component"],
    script_type: ScriptType,
    variables_hash: str | None,
) -> bool:
    cache_key = _gen_cache_key(comp_cls.class_id, script_type, variables_hash)
    cache = get_component_media_cache()
    return cache.has_key(cache_key)


def _cache_script(
    comp_cls: type["Component"],
    script: Script | Style,
    script_type: ScriptType,
    variables_hash: str | None,
) -> None:
    """
    Given a component and it's inlined JS or CSS, store the JS/CSS in a cache,
    so it can be retrieved via URL endpoint.
    """
    # E.g. `__components:MyButton:js:df7c6d10`
    if script_type in ("js", "css"):
        cache_key = _gen_cache_key(comp_cls.class_id, script_type, variables_hash)
    else:
        raise ValueError(f"Unexpected script_type '{script_type}'")

    # NOTE: By setting the script in the cache, we will be able to retrieve it
    # via the endpoint, e.g. when we make a request to `/components/cache/MyComp_ab0c2d.js`.
    cache = get_component_media_cache()
    serialized_script = json.dumps(script.to_json())
    cache.set(cache_key, serialized_script)


# Regex pattern to match $onComponent( calls in component JS
# Matches: $onComponent( with optional whitespace before the opening parenthesis
_ONCOMPONENT_PATTERN = re.compile(r"\$onComponent\s*\(")


def _transform_oncomponent_calls(js_content: str, comp_cls_id: str) -> str:
    """
    Replace `$onComponent(` with `DjangoComponents.manager.registerComponent("comp_cls_id", `
    so that $onComponent is just syntactic sugar for `registerComponent()`.
    """
    return _ONCOMPONENT_PATTERN.sub(f'DjangoComponents.manager.registerComponent("{comp_cls_id}", ', js_content)


def cache_component_js(comp_cls: type["Component"], force: bool) -> None:
    """
    Cache the content from `Component.js`. This is the common JS that's shared
    among all instances of the same component. So even if the component is rendered multiple
    times, this JS is loaded only once.
    """
    if not comp_cls.js or not is_nonempty_str(comp_cls.js):
        return

    if not force and _is_script_in_cache(comp_cls, "js", None):
        return

    # Transform `$onComponent(` calls to registerComponent calls before caching
    transformed_js = _transform_oncomponent_calls(comp_cls.js, comp_cls.class_id)

    # NOTE: We store the script as `Script` object so later we can still modify
    # the attributes and content separately.
    script_obj = Script(
        kind="component",
        content=transformed_js,
        attrs={},
        origin_class_id=comp_cls.class_id,
    )
    _cache_script(
        comp_cls=comp_cls,
        script=script_obj,
        script_type="js",
        variables_hash=None,
    )


# NOTE: In CSS, we link the CSS vars to the component via a stylesheet that defines
# the CSS vars under `[data-djc-css-a1b2c3]`. Because of this we define the variables
# separately from the rest of the CSS definition.
#
# We use conceptually similar approach for JS, except in JS we have to manually associate
# the JS variables ("stylesheet") with the target HTML element ("component").
#
# It involves 3 steps:
# 1. Register the common logic (equivalent to registering common CSS).
#    with `DjangoComponents.manager.registerComponent`.
# 2. Register the unique set of JS variables (equivalent to defining CSS vars)
#    with `DjangoComponents.manager.registerComponentData`.
# 3. Actually run a component's JS instance with `DjangoComponents.manager.callComponent`,
#    specifying the components HTML elements with `component_id`, and JS vars with `variables_hash`.
def cache_component_js_vars(comp_cls: type["Component"], js_vars: Mapping) -> str | None:
    if not is_nonempty_str(comp_cls.js):
        return None

    # The hash for the file that holds the JS variables is derived from the variables themselves.
    json_data = json.dumps(js_vars)
    variables_hash = md5(json_data.encode()).hexdigest()[0:6]  # noqa: S324

    # Generate and cache a JS script that contains the JS variables.
    if not _is_script_in_cache(comp_cls, "js", variables_hash):
        js_vars_script = _gen_exec_script(
            output_type="script",
            script_kind="variables",
            script_origin_class_id=comp_cls.class_id,
            css_tags__fetch_in_client=[],
            js_tags__fetch_in_client=[],
            css_urls__mark_loaded_in_client=[],
            js_urls__mark_loaded_in_client=[],
            comp_calls=[],
            comp_js_vars=[
                ComponentJsVars(comp_cls.class_id, variables_hash, json_data),
            ],
        )

        # NOTE: `js_vars_script` should never be `None`, condition just to satisfy the type checker
        if js_vars_script is not None:
            _cache_script(
                comp_cls=comp_cls,
                script=js_vars_script,
                script_type="js",
                variables_hash=variables_hash,
            )

    return variables_hash


def cache_component_css(comp_cls: type["Component"], force: bool) -> None:
    """
    Cache the content from `Component.css`. This is the common CSS that's shared
    among all instances of the same component. So even if the component is rendered multiple
    times, this CSS is loaded only once.
    """
    if not comp_cls.css or not is_nonempty_str(comp_cls.css):
        return

    if not force and _is_script_in_cache(comp_cls, "css", None):
        return

    # NOTE: We store the script as `Style` object so later we can still modify
    # the attributes and content separately.
    style_obj = Style(
        kind="component",
        content=comp_cls.css,
        attrs={},
        origin_class_id=comp_cls.class_id,
    )
    _cache_script(
        comp_cls=comp_cls,
        script=style_obj,
        script_type="css",
        variables_hash=None,
    )


# NOTE: In CSS, we link the CSS vars to the component via a stylesheet that defines
# the CSS vars under the CSS selector `[data-djc-css-a1b2c3]`. We define the stylesheet
# with variables separately from `Component.css`, because different instances may return different
# data from `get_css_data()`, which will live in different stylesheets.
def cache_component_css_vars(comp_cls: type["Component"], css_vars: Mapping) -> str | None:
    if not is_nonempty_str(comp_cls.css):
        return None

    # The hash for the file that holds the CSS variables is derived from the variables themselves.
    json_data = json.dumps(css_vars)
    variables_hash = md5(json_data.encode()).hexdigest()[0:6]  # noqa: S324

    # Generate and cache a CSS stylesheet that contains the CSS variables.
    if not _is_script_in_cache(comp_cls, "css", variables_hash):
        formatted_vars = [f"  --{key}: {serialize_css_var_value(value)};" for key, value in css_vars.items()]

        # ```css
        # [data-djc-css-f3f3eg9] {
        #   --my-var: red;
        # }
        # ```
        input_css = "\n".join(
            [f"/* {comp_cls.class_id} */", f"[data-djc-css-{variables_hash}] {{", *formatted_vars, "}"]
        )

        # NOTE: We store the script as `Style` object so later we can still modify
        # the attributes and content separately.
        style_obj = Style(
            kind="variables",
            content=input_css,
            attrs={},
            origin_class_id=comp_cls.class_id,
        )
        _cache_script(
            comp_cls=comp_cls,
            script=style_obj,
            script_type="css",
            variables_hash=variables_hash,
        )

    return variables_hash


#########################################################
# 2. Modify the HTML to use the same IDs defined in previous
#    step for the inlined CSS and JS scripts, so the scripts
#    can be applied to the correct HTML elements. And embed
#    component + JS/CSS relationships as HTML comments.
#########################################################


def set_component_attrs_for_js_and_css(
    html_content: str | SafeString,
    component_id: str | None,
    css_input_hash: str | None,
    root_attributes: list[str] | None = None,
) -> tuple[str | SafeString, dict[str, list[str]]]:
    # These are the attributes that we want to set on the root element.
    all_root_attributes = [*root_attributes] if root_attributes else []

    # Component ID is used for executing JS script, e.g. `data-djc-id-ca1b2c3`
    #
    # NOTE: We use `data-djc-css-a1b2c3` and `data-djc-id-ca1b2c3` instead of
    # `data-djc-css="a1b2c3"` and `data-djc-id="a1b2c3"`, to allow
    # multiple values to be associated with the same element, which may happen if
    # one component renders another.
    if component_id:
        all_root_attributes.append(f"data-djc-id-{component_id}")

    # Attribute by which we bind the CSS variables to the component's CSS,
    # e.g. `data-djc-css-a1b2c3`
    if css_input_hash:
        all_root_attributes.append(f"data-djc-css-{css_input_hash}")

    is_safestring = isinstance(html_content, SafeString)
    updated_html, child_components = set_html_attributes(
        html_content,
        root_attributes=all_root_attributes,
        all_attributes=[],
        # Setting this means that set_html_attributes will check for HTML elemetnts with this
        # attribute, and return a dictionary of {attribute_value: [attributes_set_on_this_tag]}.
        #
        # So if HTML contains tag <template djc-render-id="123"></template>,
        # and we set on that tag `data-djc-id-123`, then we will get
        # {
        #   "123": ["data-djc-id-123"],
        # }
        #
        # This is a minor optimization. Without this, when we're rendering components in
        # component_post_render(), we'd have to parse each `<template djc-render-id="123"></template>`
        # to find the HTML attribute that were set on it.
        watch_on_attribute="djc-render-id",
    )
    updated_html = mark_safe(updated_html) if is_safestring else updated_html

    return updated_html, child_components


# NOTE: To better understand the next section, consider this:
#
# We define and cache the component's JS and CSS at the same time as
# when we render the HTML. However, the resulting HTML MAY OR MAY NOT
# be used in another component.
#
# IF the component's HTML IS used in another component, and the other
# component want to render the JS or CSS dependencies (e.g. inside <head>),
# then it's only at that point when we want to access the data about
# which JS and CSS scripts is the component's HTML associated with.
#
# This happens AFTER the rendering context, so there's no Context to rely on.
#
# Hence, we store the info about associated JS and CSS right in the HTML itself.
# As an HTML comment `<!-- -->`. Thus, the inner component can be used as many times
# and in different components, and they will all know to fetch also JS and CSS of the
# inner components.
def insert_component_dependencies_comment(
    content: str,
    # NOTE: We pass around the component CLASS, so the dependencies logic is not
    # dependent on ComponentRegistries
    component_cls: type["Component"],
    component_id: str,
    js_input_hash: str | None,
    css_input_hash: str | None,
) -> SafeString:
    """
    Given some textual content, prepend it with a short string that
    will be used by the `render_dependencies()` function to collect all
    declared JS / CSS scripts.
    """
    data = f"{component_cls.class_id},{component_id},{js_input_hash or ''},{css_input_hash or ''}"

    # NOTE: It's important that we put the comment BEFORE the content, so we can
    # use the order of comments to evaluate components' instance JS code in the correct order.
    output = mark_safe(COMPONENT_DEPS_COMMENT.format(data=data) + content)
    return output


#########################################################
# 3. Given a FINAL HTML composed of MANY components,
#    process all the HTML dependency comments (created in
#    previous step), obtaining ALL JS and CSS scripts
#    required by this HTML document. And post-process them,
#    so the scripts are either inlined into the HTML, or
#    fetched when the HTML is loaded in the browser.
#########################################################


TContent = TypeVar("TContent", bound=bytes | str)


CSS_PLACEHOLDER_NAME = "CSS_PLACEHOLDER"
CSS_PLACEHOLDER_NAME_B = CSS_PLACEHOLDER_NAME.encode()
JS_PLACEHOLDER_NAME = "JS_PLACEHOLDER"
JS_PLACEHOLDER_NAME_B = JS_PLACEHOLDER_NAME.encode()

CSS_DEPENDENCY_PLACEHOLDER = f'<link name="{CSS_PLACEHOLDER_NAME}">'
JS_DEPENDENCY_PLACEHOLDER = f'<script name="{JS_PLACEHOLDER_NAME}"></script>'
COMPONENT_DEPS_COMMENT = "<!-- _RENDERED {data} -->"

# E.g. `<!-- _RENDERED table,123,a92ef298,bd002c3 -->`
COMPONENT_COMMENT_REGEX = re.compile(rb"<!--\s+_RENDERED\s+(?P<data>[\w\-,/]+?)\s+-->")
# E.g. `table,123,a92ef298,bd002c3`
# - comp_cls_id - Cache key of the component class that was rendered
# - id - Component render ID
# - js - Cache key for the JS data from `get_js_data()`
# - css - Cache key for the CSS data from `get_css_data()`
SCRIPT_NAME_REGEX = re.compile(
    rb"^(?P<comp_cls_id>[\w\-\./]+?),(?P<id>[\w]+?),(?P<js>[0-9a-f]*?),(?P<css>[0-9a-f]*?)$",
)
# Patterns that allow any characters except `>` before and after the placeholder name
# - Before `name`: empty OR non-empty ending with whitespace (to ensure proper separation)
# - After `name`: empty OR non-empty starting with whitespace (to ensure proper separation)
ANY_ATTRS_BEFORE = r"(?:[^>]*\s)?"
ANY_ATTRS_AFTER = r"(?:\s[^>]*)?"

PLACEHOLDER_REGEX = re.compile(
    r"{css_placeholder}|{js_placeholder}".format(
        # NOTE: The CSS and JS placeholders may have any HTML attributes before and after
        # the `name` attribute, as these attributes are assigned BEFORE we replace the
        # placeholders with actual <script> / <link> tags.
        css_placeholder=f'<link\\s+{ANY_ATTRS_BEFORE}name="{CSS_PLACEHOLDER_NAME}"{ANY_ATTRS_AFTER}/?>',
        js_placeholder=f'<script\\s+{ANY_ATTRS_BEFORE}name="{JS_PLACEHOLDER_NAME}"{ANY_ATTRS_AFTER}></script>',
    ).encode()
)


def render_dependencies(content: TContent, strategy: DependenciesStrategy = "document") -> TContent:
    """
    Given an HTML string (str or bytes) that contains parts that were rendered by components,
    this function searches the HTML for the components used in the rendering,
    and inserts the JS and CSS of the used components into the HTML.

    Returns the edited copy of the HTML.

    See [Rendering JS / CSS](../concepts/advanced/rendering_js_css.md).

    **Args:**

    - `content` (str | bytes): The rendered HTML string that is searched for components, and
        into which we insert the JS and CSS tags. Required.

    - `strategy` - Optional. Configure how to handle JS and CSS dependencies. Default is
        ``"document"``. Read more about
        [Rendering strategies](../concepts/advanced/rendering_js_css.md#dependencies-strategies).

        There are six strategies:

        - [`"document"`](../concepts/advanced/rendering_js_css.md#document) (default for top-level)
            - Smartly inserts JS / CSS into placeholders or into `<head>` and `<body>` tags.
            - Inserts extra script to allow `fragment` types to work.
            - Assumes the HTML will be rendered in a JS-enabled browser.
        - [`"fragment"`](../concepts/advanced/rendering_js_css.md#fragment)
            - A lightweight HTML fragment to be inserted into a document.
            - No JS / CSS included.
        - [`"simple"`](../concepts/advanced/rendering_js_css.md#simple)
            - Smartly insert JS / CSS into placeholders or into `<head>` and `<body>` tags.
            - No extra script loaded.
        - [`"prepend"`](../concepts/advanced/rendering_js_css.md#prepend)
            - Insert JS / CSS before the rendered HTML.
            - No extra script loaded.
        - [`"append"`](../concepts/advanced/rendering_js_css.md#append)
            - Insert JS / CSS after the rendered HTML.
            - No extra script loaded.
        - [`"ignore"`](../concepts/advanced/rendering_js_css.md#ignore) (default when nested)
            - Returns the content unchanged (no JS / CSS inserted).

    **Example:**

    ```python
    def my_view(request):
        template = Template('''
            {% load component_tags %}
            <!doctype html>
            <html>
                <head></head>
                <body>
                    <h1>{{ table_name }}</h1>
                    {% component "table" name=table_name / %}
                </body>
            </html>
        ''')

        html = template.render(
            Context({
                "table_name": request.GET["name"],
            })
        )

        # This inserts components' JS and CSS
        processed_html = render_dependencies(html)

        return HttpResponse(processed_html)
    ```

    """
    if strategy not in DEPS_STRATEGIES:
        raise ValueError(f"Invalid strategy '{strategy}'")
    if strategy == "ignore":
        return content

    is_safestring = isinstance(content, SafeString)

    if isinstance(content, str):
        content_ = content.encode()
    else:
        content_ = cast("bytes", content)

    # TODO - Strategies should be only "document" | "fragment" | "simple".
    #        "prepend" | "append" should be NOT strategies, but instead optional insertion positions.
    internal_strategy: InternalDependenciesStrategy = (
        cast("InternalDependenciesStrategy", strategy) if strategy in ("document", "fragment", "simple") else "simple"
    )

    content_, scripts, styles = _process_dep_declarations(content_, internal_strategy)

    scripts, styles = extensions.on_dependencies(
        OnDependenciesContext(
            scripts=scripts,
            styles=styles,
        )
    )

    js_deps_bytes = "".join([script.render() for script in scripts]).encode("utf-8")
    css_deps_bytes = "".join([style.render() for style in styles]).encode("utf-8")

    # Replace the placeholders with the actual content
    # If strategy in (`document`, 'simple'), we insert the JS and CSS directly into the HTML,
    #                        where the placeholders were.
    # If strategy == `fragment`, we let the client-side manager load the JS and CSS,
    #                        and remove the placeholders.
    did_find_js_placeholder = False
    did_find_css_placeholder = False
    css_replacement = css_deps_bytes if strategy in ("document", "simple") else b""
    js_replacement = js_deps_bytes if strategy in ("document", "simple") else b""

    def on_replace_match(match: "re.Match[bytes]") -> bytes:
        nonlocal did_find_css_placeholder
        nonlocal did_find_js_placeholder

        if CSS_PLACEHOLDER_NAME_B in match[0]:
            replacement = css_replacement
            did_find_css_placeholder = True
        elif JS_PLACEHOLDER_NAME_B in match[0]:
            replacement = js_replacement
            did_find_js_placeholder = True
        else:
            raise RuntimeError(
                "Unexpected error: Regex for component dependencies processing"
                f" matched unknown string '{match[0].decode()}'",
            )
        return replacement

    content_ = PLACEHOLDER_REGEX.sub(on_replace_match, content_)

    # By default ("document") and for "simple" strategy, if user didn't specify any `{% component_dependencies %}`,
    # then try to insert the JS scripts at the end of <body> and CSS sheets at the end
    # of <head>.
    if strategy in ("document", "simple") and (not did_find_js_placeholder or not did_find_css_placeholder):
        maybe_transformed = _insert_js_css_to_default_locations(
            content_.decode(),
            css_content=None if did_find_css_placeholder else css_deps_bytes.decode(),
            js_content=None if did_find_js_placeholder else js_deps_bytes.decode(),
        )

        if maybe_transformed is not None:
            content_ = maybe_transformed.encode()

    # In case of a fragment, we only append the JS (actually JSON) to trigger the call of dependency-manager
    elif strategy == "fragment":
        content_ += js_deps_bytes
    # For prepend / append, we insert the JS and CSS before / after the content
    elif strategy == "prepend":
        content_ = js_deps_bytes + css_deps_bytes + content_
    elif strategy == "append":
        content_ = content_ + js_deps_bytes + css_deps_bytes

    # Return the same type as we were given
    output = content_.decode() if isinstance(content, str) else content_
    output = mark_safe(output) if is_safestring else output
    return cast("TContent", output)


# Renamed so we can access use this function where there's kwarg of the same name
_render_dependencies = render_dependencies


def _core_js() -> Script:
    """
    Returns a `Script` object for the Django Components library's core script.

    This script is required for the Django Components library to work.
    """
    return Script(
        kind="core",
        url=static("django_components/django_components.min.js"),
        content=None,
        attrs={},
        origin_class_id=None,
    )


def _pre_loader_js() -> Script:
    """
    This script checks if our dependency manager script is already loaded on the page,
    and loads the manager if not yet.

    This script is included with every "fragment", so that the "fragments" can be rendered
    even on pages that weren't rendered with the "document" strategy.
    """
    manager_url = static("django_components/django_components.min.js")
    if '"' in manager_url:
        raise ValueError("Manager URL cannot contain quotes")
    content = f"""
        if (!globalThis.DjangoComponents) {{
            const s = document.createElement('script');
            s.src = "{manager_url}";
            document.head.appendChild(s);
        }}
        // Remove this loader script
        if (document.currentScript) document.currentScript.remove();
    """

    return Script(
        kind="core",
        content=content,
        url=None,
        attrs={},
        wrap=True,
        origin_class_id=None,
    )


# Overview of this function:
# 1. We extract all HTML comments like `<!-- _RENDERED table_10bac31,1234-->`.
# 2. We look up the corresponding component classes
# 3. For each component class we get the component's inlined JS and CSS,
#    and the JS and CSS from `Media.js/css`
# 4. We add our client-side JS logic into the mix (`django_components/django_components.min.js`)
#    - For fragments, we would skip this step.
# 5. For all the above JS and CSS, we figure out which JS / CSS needs to be inserted directly
#    into the HTML, and which can be loaded with the client-side manager.
#    - Components' inlined JS is inserted directly into the HTML as `<script> ... <script>`,
#      to avoid having to issues 10s of requests for each component separately.
#    - Components' inlined CSS is inserted directly into the HTML as `<style> ... <style>`,
#      to avoid a [flash of unstyled content](https://en.wikipedia.org/wiki/Flash_of_unstyled_content)
#      that would occur if we had to load the CSS via JS request.
#    - For CSS from `Media.css` we insert that as `<link href="...">` HTML tags, also to avoid
#      the flash of unstyled content
#    - For JS from `Media.js`, we let the client-side manager load that, so that, even if
#      multiple components link to the same JS script in their `Media.js`, the linked JS
#      will be fetched and executed only once.
# 6. And lastly, we generate a JS script that will load / mark as loaded the JS and CSS
#    as categorized in previous step.
def _process_dep_declarations(
    content: bytes, strategy: InternalDependenciesStrategy
) -> tuple[bytes, list[Script], list[Style]]:
    """
    Process a textual content that may include metadata on rendered components.
    The metadata has format like this

    `<!-- _RENDERED component_name,component_id,js_hash,css_hash;... -->`

    E.g.

    `<!-- _RENDERED table_10bac31,123,a92ef298,bd002c3 -->`
    """
    from django_components.component import get_component_by_class_id  # noqa: PLC0415

    if strategy in ("document", "simple"):
        should_inline_scripts = True
    elif strategy == "fragment":
        should_inline_scripts = False
    else:
        raise ValueError(f"Unexpected strategy '{strategy}' passed to _process_dep_declarations")

    # Extract all matched instances of `<!-- _RENDERED ... -->` while also removing them from the text
    content, matches = extract_regex_matches(content, COMPONENT_COMMENT_REGEX)

    # Track which component INSTANCES should have JS-side code executed.
    # This is used to add `$onComponent` callbacks to the dependency manager.
    #
    # This is DIFFERENT from the JS/CSS variables. A call may/may not have variables.
    # And if multiple calls have the same variables, they will have the same JS hash,
    # even if they belong to different Component classes.
    #
    # OTOH, each component instance will have its own `$onComponent` callback, and thus its own
    # `comp_calls` entry, irrespective of whether it has the same JS variables with another or not.
    #
    # With this design, the JS/CSS variables scripts are cached and loaded onto the browser only once.
    # You can define a massive JSON for variables, and it will be loaded from the server only once.
    comp_calls: list[ComponentCall] = []

    # Process individual parts. Each part is like a CSV row of `name,id,js,css`.
    # E.g. something like this:
    # `table_10bac31,1234,a92ef298,a92ef298`
    instance_rows: list[tuple[str, str, str | None, str | None]] = []
    for match in matches:
        raw_data = match.group("data")
        data_match = SCRIPT_NAME_REGEX.match(raw_data)

        if not data_match:
            raise RuntimeError("Malformed dependencies data")

        comp_cls_id: str = data_match.group("comp_cls_id").decode("utf-8")
        comp_id = data_match.group("id").decode("utf-8")
        js_variables_hash: str | None = data_match.group("js").decode("utf-8") or None
        css_variables_hash: str | None = data_match.group("css").decode("utf-8") or None

        instance_rows.append((comp_cls_id, comp_id, js_variables_hash, css_variables_hash))

    ##################################################################
    # Core JS/CSS -- Always include these, regardless of the strategy.
    ##################################################################

    core_scripts: list[Script] = []
    if strategy == "document":
        # For full documents, load manager as a normal external <script src="...">
        core_scripts.append(_core_js())
    elif strategy == "fragment":
        # For fragments, inline a script that conditionally injects the dependency manager
        # if it's not already loaded.
        core_scripts.append(_pre_loader_js())

    core_styles: list[Style] = []

    ##################################################################
    # Component JS/CSS -- Code + variables + Media JS/CSS
    ##################################################################

    all_scripts: list[Script] = []
    all_styles: list[Style] = []

    # All JS/CSS that we will mark as "already loaded" in the dependency manager.
    # This includes JS/CSS from Component.js/css, JS/CSS variables, and JS/CSS from Component.Media.js/css.
    # But only if strategy is "document" | "simple" | "prepend" | "append".
    # Empty for "fragment" because client-side manager is meant to load these dependencies dynamically.
    all_scripts_mark_as_loaded: list[Script] = []
    all_styles_mark_as_loaded: list[Style] = []

    for comp_cls_id, comp_id, js_hash, css_hash in instance_rows:
        instance_scripts, instance_styles, scripts_mark_as_loaded, styles_mark_as_loaded = (
            _get_instance_scripts_and_styles(comp_cls_id, comp_id, js_hash, css_hash, should_inline_scripts)
        )
        comp_cls = get_component_by_class_id(comp_cls_id)

        # NOTE: Users may break their rendering if they remove the existing "component"
        #       and "variables" scripts from their `Component.on_dependencies` hook.
        result = comp_cls.on_dependencies(
            cast("list[Script]", instance_scripts),
            cast("list[Style]", instance_styles),
        )
        if result is not None:
            instance_scripts, instance_styles = result

        all_scripts.extend(instance_scripts)
        all_styles.extend(instance_styles)
        all_scripts_mark_as_loaded.extend(scripts_mark_as_loaded)
        all_styles_mark_as_loaded.extend(styles_mark_as_loaded)

        if is_nonempty_str(comp_cls.js) and "$onComponent" in comp_cls.js:
            # Add component instance to the queue of calls to `$onComponent` callbacks
            comp_calls.append(ComponentCall(comp_cls_id, comp_id, js_hash))

    ##################################################################
    # Categorize
    ##################################################################

    # For each JS/CSS object, decide which ones should be:
    # - Inserted into the HTML as <script> / <style> tags
    # - Loaded with the client-side manager
    # - Marked as already-loaded in the dependency manager
    deps_js__inline: list[Script] = []
    deps_js__fetch_in_client: list[Script] = []
    deps_css__inline: list[Style] = []
    deps_css__fetch_in_client: list[Style] = []
    component_js__inline: list[Script] = []
    component_css__inline: list[Style] = []
    component_js__fetch_in_client: list[Script] = []
    component_css__fetch_in_client: list[Style] = []

    # When we get here, the `script` is already either:
    # - `<script src="...">` if using "fragment" strategy
    # - `<script>...</script>` if using other strategies
    # However, this applies only to Scripts from `Component.js` or variables.
    # The scripts from `Component.Media.js/css` may be either inline or fetched.
    for script in all_scripts:
        if script.kind in ("component", "variables"):
            # JS from `Component.js` or variables
            if should_inline_scripts:
                component_js__inline.append(script)
            else:
                component_js__fetch_in_client.append(script)
        elif script.kind == "extra":
            # Component.Media.js
            if should_inline_scripts:
                deps_js__inline.append(script)
            else:
                deps_js__fetch_in_client.append(script)
        elif script.kind == "core":
            # User's `Component.on_dependencies` hook may introduce new core JS/CSS.
            # in which case we run it after our core JS/CSS
            core_scripts.append(script)
        else:
            raise ValueError(f"Unknown script kind: {script.kind}")

    # When we get here, the `style` is already either:
    # - `<link rel="stylesheet" href="...">` if using "fragment" strategy
    # - `<style>...</style>` if using other strategies
    # However, this applies only to Styles from `Component.css` or variables.
    # The styles from `Component.Media.css` may be either inline or fetched.
    for style in all_styles:
        if style.kind in ("component", "variables"):
            # CSS from `Component.css` or variables
            if should_inline_scripts:
                component_css__inline.append(style)
            else:
                component_css__fetch_in_client.append(style)
        elif style.kind == "extra":
            # Component.Media.css
            if should_inline_scripts:
                deps_css__inline.append(style)
            else:
                deps_css__fetch_in_client.append(style)
        elif style.kind == "core":
            # User's `Component.on_dependencies` hook may introduce new core JS/CSS.
            # in which case we run it after our core JS/CSS
            core_styles.append(style)
        else:
            raise ValueError(f"Unknown style kind: {style.kind}")

    ##################################################################
    # Dedupe
    # If multiple Script/Style objects link to the same JS/CSS (URL or content),
    # we go with the first one that we come across.
    ##################################################################

    # Ensure that the JS/CSS from `Component.Media.js/css` are loaded BEFORE the JS/CSS from `Component.js/css`.
    # NOTE: We do NOT want to fully sort these to preserve the relative order
    #       (components defined earlier in the HTML should be executed earlier).
    all_js__inline = _dedupe_by_url_or_content([*deps_js__inline, *component_js__inline])
    all_js__fetch_in_client = _dedupe_by_url_or_content([*deps_js__fetch_in_client, *component_js__fetch_in_client])
    all_css__inline = _dedupe_by_url_or_content([*deps_css__inline, *component_css__inline])
    all_css__fetch_in_client = _dedupe_by_url_or_content([*deps_css__fetch_in_client, *component_css__fetch_in_client])

    # NOTE: Sorting of these is mainly to keep predictable order in tests.
    all_scripts_mark_as_loaded = sorted(
        _dedupe_by_url_or_content(all_scripts_mark_as_loaded),
        key=lambda x: x.url or "",
    )

    all_styles_mark_as_loaded = sorted(
        _dedupe_by_url_or_content(all_styles_mark_as_loaded),
        key=lambda x: x.url or "",
    )

    ##################################################################
    # Generate exec script -- This tells the client-side manager which JS/CSS to load
    ##################################################################

    # Document - All JS/CSS already inlined, just let the dependency manager know.
    # NOTE: No exec script for the "simple"|"prepend"|"append"|"ignore" mode,
    #       as they are NOT using the dependency manager.
    if strategy == "document":
        exec_script = _gen_exec_script(
            output_type="json",
            script_kind="core",  # Indicate not to mess with this script
            script_origin_class_id=None,
            js_tags__fetch_in_client=[],
            css_tags__fetch_in_client=[],
            js_urls__mark_loaded_in_client=all_scripts_mark_as_loaded,
            css_urls__mark_loaded_in_client=all_styles_mark_as_loaded,
            comp_calls=comp_calls,
            comp_js_vars=[],
        )
    # Fragment - No JS/CSS inlined, tell the dependency manager which JS/CSS to load
    elif strategy == "fragment":
        exec_script = _gen_exec_script(
            output_type="json",
            script_kind="core",  # Indicate not to mess with this script
            script_origin_class_id=None,
            js_tags__fetch_in_client=all_js__fetch_in_client,
            css_tags__fetch_in_client=all_css__fetch_in_client,
            js_urls__mark_loaded_in_client=[],
            css_urls__mark_loaded_in_client=[],
            comp_calls=comp_calls,
            comp_js_vars=[],
        )
    else:
        exec_script = None

    final_scripts = [
        # JS by us
        *core_scripts,
        # This makes calls to the JS dependency manager
        # and loads JS from `Media.js` and `Component.js` if fragment
        *([exec_script] if exec_script else []),
        *all_js__inline,
    ]

    final_styles = [
        # CSS by us
        *core_styles,
        # CSS from `Media.css`, `Component.css` and CSS variables (if not fragment)
        *all_css__inline,
    ]

    return (content, final_scripts, final_styles)


def _get_instance_scripts_and_styles(
    comp_cls_id: str,
    comp_id: str,  # noqa: ARG001
    js_hash: str | None,
    css_hash: str | None,
    should_inline_scripts: bool,
) -> tuple[list[Script], list[Style], list[Script], list[Style]]:
    """
    Get the Script/Style lists for a single component instance
    (Component.js/css + variables + Media.js/css).
    """
    from django_components.component import get_component_by_class_id  # noqa: PLC0415

    comp_cls = get_component_by_class_id(comp_cls_id)
    instance_scripts: list[Script] = []
    instance_styles: list[Style] = []

    # NOTE: When rendering a "document", the initial JS is inserted directly into the HTML
    #       so the scripts are executed at proper order. In such case, we want to prevent
    #       the dependency manager from fetching and executing the code second time.
    #       So we collect which scripts/styles we should "mark as loaded" in the dependency manager.
    # NOTE: We do NOT do this for "simple" | "prepend" | "append", because client-side deps manager
    #       is OFF in those cases.
    #       And we do NOT add this for "fragment" because client-side deps manager is meant to load
    #       these dependencies dynamically.
    scripts_mark_as_loaded: list[Script] = []
    styles_mark_as_loaded: list[Style] = []

    ##############################
    # Component's own JS/CSS (Component.js/css)
    ##############################

    # Component JS
    if is_nonempty_str(comp_cls.js):
        if should_inline_scripts:
            comp_js = cast("Script | None", get_script("js", comp_cls, None))
            if comp_js is not None:
                instance_scripts.append(comp_js)
                comp_js_url = cast("Script", get_script_url("js", comp_cls, None))
                scripts_mark_as_loaded.append(comp_js_url)
        else:
            comp_js_url = cast("Script", get_script_url("js", comp_cls, None))
            instance_scripts.append(comp_js_url)

    # Component CSS
    if is_nonempty_str(comp_cls.css):
        if should_inline_scripts:
            comp_css = cast("Style | None", get_script("css", comp_cls, None))
            if comp_css is not None:
                instance_styles.append(comp_css)
                comp_css_url = cast("Style", get_script_url("css", comp_cls, None))
                styles_mark_as_loaded.append(comp_css_url)
        else:
            comp_css_url = cast("Style", get_script_url("css", comp_cls, None))
            instance_styles.append(comp_css_url)

    ##############################
    # Component JS/CSS variables
    # Skip if no variables are defined or if the component class does not have JS/CSS code.
    ##############################

    # Variables JS
    if js_hash is not None and is_nonempty_str(comp_cls.js) and "$onComponent" in comp_cls.js:
        if should_inline_scripts:
            comp_vars_js = cast("Script | None", get_script("js", comp_cls, js_hash))
            if comp_vars_js is not None:
                instance_scripts.append(comp_vars_js)
                comp_vars_js_url = cast("Script", get_script_url("js", comp_cls, js_hash))
                scripts_mark_as_loaded.append(comp_vars_js_url)
        else:
            comp_vars_js_url = cast("Script", get_script_url("js", comp_cls, js_hash))
            instance_scripts.append(comp_vars_js_url)

    # Variables CSS
    if css_hash is not None and is_nonempty_str(comp_cls.css):
        if should_inline_scripts:
            comp_vars_css = cast("Style | None", get_script("css", comp_cls, css_hash))
            if comp_vars_css is not None:
                instance_styles.append(comp_vars_css)
                comp_vars_css_url = cast("Style", get_script_url("css", comp_cls, css_hash))
                styles_mark_as_loaded.append(comp_vars_css_url)
        else:
            comp_vars_css_url = cast("Style", get_script_url("css", comp_cls, css_hash))
            instance_styles.append(comp_vars_css_url)

    #############################
    # JS/CSS from Component.Media.js/css
    #
    # Legacy code start
    # TODO_V1 - Replace. Instead of using Media class to render scripts/styles to string,
    # and then parsing them into Script/Style, the `Component.(Media` or `Component.Dependencies`)
    # should give us `Script/Style` objects directly.
    # TODO_V1 - Add. Users should be given a hook/method (both on Component and Extension level)
    # to access all Script/Style objects prepared for rendering, allowing the user to modify/create/delete them.
    #############################

    # JS / CSS files from Component.Media.js/css.
    comp_cls = get_component_by_class_id(comp_cls_id)
    media = comp_cls.media

    # Some entries in `Component.Media.js/css` may be SafeString / SafeData objects.
    # That means that it's some objects with `__html__()` method. And calling this method
    # should yield the final string for the `<script>` or `<style>` HTML tag.
    #
    # Howver, in our API we want to expose the JS and CSS as `Script` and `Style` objects.
    # And so, we need to parse the string into a `Script` or `Style` object.
    media_css_tags = cast("list[SafeString]", media.render_css()) if media else []
    media_js_tags = cast("list[SafeString]", media.render_js()) if media else []

    media_css_objects = [
        cast("Style", _parse_dependency_from_string("css", media_css_tag, comp_cls_id))
        for media_css_tag in media_css_tags
    ]
    media_js_objects = [
        cast("Script", _parse_dependency_from_string("js", media_js_tag, comp_cls_id))
        for media_js_tag in media_js_tags
    ]

    instance_scripts.extend(cast("list[Script]", media_js_objects))
    instance_styles.extend(cast("list[Style]", media_css_objects))

    if should_inline_scripts:
        scripts_mark_as_loaded.extend(media_js_objects)
        styles_mark_as_loaded.extend(media_css_objects)

    #############################
    # Legacy code end
    #############################

    return (instance_scripts, instance_styles, scripts_mark_as_loaded, styles_mark_as_loaded)


def _dedupe_by_url_or_content(items: Sequence[TDep]) -> list[TDep]:
    """
    Deduplicate Script/Style list by url or content (first occurrence wins).

    Uses Script/Style __hash__ and __eq__: same url or same content (when no url)
    are considered duplicates.
    """
    return list(dict.fromkeys(items))


# TODO_V1: This function won't be used anymore. Remove it.
def _parse_dependency_from_string(
    script_type: ScriptType,
    tag: str | SafeString,
    component_class_id: str,
) -> Script | Style:
    """
    Parse an HTML tag string from `Component.Media` into `Script`/`Style` object.

    Extracts all attributes from the tag and creates `Script` or `Style` object.
    """
    if script_type not in ("js", "css"):
        raise ValueError(f"Invalid script type: {script_type}")

    # Parse tag name, attributes, and optional content (so we can parse e.g. <script>...</script>)
    tag_name, parsed_attrs, tag_content = _parse_html_tag_attrs(tag)

    # Validate tag name matches expected type
    if script_type == "js":
        if tag_name != "script":
            raise RuntimeError(
                f"One of entries for `Component.Media.{script_type}` media has incorrect tag name. "
                f"Expected '<script>' tag but got '<{tag_name}>'.\n"
                f"Got:\n{tag}",
            )
        attr_name = "src"
    else:  # css
        if tag_name not in ("link", "style"):
            raise RuntimeError(
                f"One of entries for `Component.Media.{script_type}` media has incorrect tag name. "
                f"Expected '<link>' or '<style>' tag but got '<{tag_name}>'.\n"
                f"Got:\n{tag}",
            )
        attr_name = "href"

    if script_type == "js":
        url = parsed_attrs.pop(attr_name, None)
        if url and url is not True:
            # External script with src <script src="...">
            script_obj: Script | Style = Script(
                kind="extra",
                url=url,
                content=None,
                attrs=parsed_attrs,
                origin_class_id=component_class_id,
            )
        else:
            # Inline <script>...</script> (wrap=False so we don't re-wrap when rendering)
            script_obj = Script(
                kind="extra",
                url=None,
                content=tag_content,
                attrs=parsed_attrs,
                origin_class_id=component_class_id,
                wrap=False,
            )
    # css: <link> or <style>
    else:  # noqa: PLR5501
        if tag_name == "link":
            # <link href="...">
            url = parsed_attrs.pop(attr_name, None)
            if not url or url is True:
                raise RuntimeError(
                    f"One of entries for `Component.Media.{script_type}` media is missing a "
                    f"value for attribute '{attr_name}'.\n"
                    f"Got:\n{tag}",
                )
            script_obj = Style(
                kind="extra",
                url=url,
                content=None,
                attrs=parsed_attrs,
                origin_class_id=component_class_id,
            )
        else:
            # <style>...</style> with inline content
            script_obj = Style(
                kind="extra",
                url=None,
                content=tag_content,
                attrs=parsed_attrs,
                origin_class_id=component_class_id,
            )

    return script_obj


class TagAttrParser(html.parser.HTMLParser):
    """Parse a single HTML tag (and optional content) to tag name, attributes, and content."""

    def __init__(self) -> None:
        super().__init__()
        self.tag_name: str | None = None
        self.attrs: dict[str, str | bool] = {}
        self.content_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.tag_name is not None:
            raise ValueError(
                f"HTML string contains multiple tags. Expected a single tag but found multiple: "
                f"'<{self.tag_name}>' and '<{tag}>'"
            )

        self.tag_name = tag
        # Convert list of (name, value) tuples to dict
        # If value is None, it's a boolean attribute
        for name, value in attrs:
            if value is None:
                self.attrs[name] = True
            else:
                self.attrs[name] = value

    def handle_data(self, data: str) -> None:
        """Capture content inside the tag (e.g. for <script>...</script> or <style>...</style>)."""
        self.content_parts.append(data)


def _parse_html_tag_attrs(tag_str: str) -> tuple[str, dict[str, str | bool], str]:
    """
    Parse HTML tag attributes and optional content from a tag string.

    Handles both URL-based tags and tags with inline content, e.g.:
    - <script src="https://..."></script> or <link href="https://...">
    - <script>....</script> or <style>...</style>

    Returns a tuple of (tag_name, attrs, content) where:
    - tag_name: The name of the HTML tag (e.g., "script", "link", "style")
    - attrs: A dict of attributes where:
      - Boolean attributes (no value) have value True
      - Attributes with values have their string values
    - content: The raw text content inside the tag, or "" if none (e.g. for <link>)
    """
    parser = TagAttrParser()
    parser.feed(tag_str.strip())

    if not parser.tag_name:
        raise ValueError(f"Failed to parse HTML tag attributes: no opening tag found in '{tag_str}'")

    content = "".join(parser.content_parts)
    return (parser.tag_name, parser.attrs, content)


def get_script(
    script_type: ScriptType,
    comp_cls: type["Component"],
    variables_hash: str | None,
) -> Script | Style | None:
    """Get `Script` or `Style` object from cache. Returns `None` if not found."""
    cache = get_component_media_cache()
    cache_key = _gen_cache_key(comp_cls.class_id, script_type, variables_hash)
    cached_data = cache.get(cache_key)

    if cached_data is None:
        return None

    # TODO_V1: Keep only new format in v1. Since scripts may be stored in
    # a cache that may be separate from the Django application, we have to
    # expect that old format may be present.
    try:
        data = json.loads(cached_data)
    except (json.JSONDecodeError, TypeError):
        # NOTE: `get_script()` is used only for retrieving 2 kinds of scripts:
        # - Component scripts (`Component.js` or `Component.css`)
        # - Variables scripts (from `get_js_data()` or `get_css_data()`)
        # And if we were given `variables_hash`, we know we were trying to get a variables script.
        kind: DependencyKind = "variables" if variables_hash is not None else "component"

        # Backward compatibility: old format was just a string
        if script_type == "js":
            return Script(kind=kind, content=cached_data, origin_class_id=comp_cls.class_id)
        else:
            return Style(kind=kind, content=cached_data, origin_class_id=comp_cls.class_id)
    else:
        if script_type == "js":
            return Script.from_json(data)
        else:
            return Style.from_json(data)


def get_script_url(
    script_type: ScriptType,
    comp_cls: type["Component"],
    variables_hash: str | None,
) -> Script | Style:
    kind: DependencyKind = "component" if variables_hash is None else "variables"
    url = reverse(
        CACHE_ENDPOINT_NAME,
        kwargs={
            "comp_cls_id": comp_cls.class_id,
            "script_type": script_type,
            **({"variables_hash": variables_hash} if variables_hash is not None else {}),
        },
    )

    if script_type == "css":
        # <link href="... media="all" rel="stylesheet">
        return Style(
            kind=kind,
            url=url,
            content=None,
            origin_class_id=comp_cls.class_id,
            attrs={"media": "all", "rel": "stylesheet"},
        )
    elif script_type == "js":
        # <script src="...">
        return Script(
            kind=kind,
            url=url,
            content=None,
            origin_class_id=comp_cls.class_id,
        )
    else:
        raise ValueError(f"Invalid script type: {script_type}")


def _gen_exec_script(
    output_type: Literal["script", "json"],
    script_kind: DependencyKind,
    script_origin_class_id: str | None,
    js_tags__fetch_in_client: list[Script],
    css_tags__fetch_in_client: list[Style],
    js_urls__mark_loaded_in_client: list[Script],
    css_urls__mark_loaded_in_client: list[Style],
    comp_js_vars: list[ComponentJsVars],
    comp_calls: list[ComponentCall],
) -> Script | None:
    # Return None if all lists are empty
    if not any(
        [
            js_tags__fetch_in_client,
            css_tags__fetch_in_client,
            css_urls__mark_loaded_in_client,
            js_urls__mark_loaded_in_client,
            comp_js_vars,
            comp_calls,
        ]
    ):
        return None

    def to_base64(tag: str) -> str:
        return base64.b64encode(tag.encode()).decode()

    def map_to_base64(lst: Sequence[str]) -> list[str]:
        return [to_base64(tag) for tag in lst]

    # Extract URLs from Script/Style objects for base64 encoding.
    # Inline scripts/styles (no URL) are skipped; only URL-based resources are marked as loaded.
    def extract_urls(script_objects: Sequence[Script | Style]) -> list[str]:
        urls = []
        for obj in script_objects:
            if obj.url:
                urls.append(obj.url)
        return urls

    def render_tags(script_objects: Sequence[Script | Style]) -> list[str]:
        tags: list[str] = []
        for obj in script_objects:
            tags.append(json.dumps(obj.render_json()))
        return tags

    # Generate JSON that will tell the JS dependency manager which JS and CSS to load
    #
    # NOTE: It would be simpler to pass only the URL itself for `loadJs/loadCss`, instead of a whole tag.
    #    But because we allow users to specify the Media class, and thus users can
    #    configure how the `<link>` or `<script>` tags are rendered, we need pass the whole tag.
    #
    # NOTE 2: Convert to Base64 to avoid any issues with `</script>` tags in the content
    exec_script_data = {
        # For the URLs that are to be marked as "already loaded", we format them just as URLs,
        # NOT an entire HTML tag. Because we don't care about the other HTML attributes.
        "cssUrls__markAsLoaded": map_to_base64(extract_urls(css_urls__mark_loaded_in_client)),
        "jsUrls__markAsLoaded": map_to_base64(extract_urls(js_urls__mark_loaded_in_client)),
        # But for the `<script>/<style>/<link> tags that we want to dynamically load in browser
        # we pass JSON objects with tag, attrs, and content fields. The browser will construct
        # the HTML elements from this data.
        "cssTags__toFetch": map_to_base64(render_tags(css_tags__fetch_in_client)),
        "jsTags__toFetch": map_to_base64(render_tags(js_tags__fetch_in_client)),
        # TODO- Convert componentJsVars and componentJsCalls to JSONs?
        # NOTE: Component call data contains only hashes and IDs. But since this info is taken
        # from the rendered HTML, which could have been tampered with, it's better to escape these to base64 too.
        "componentJsVars": [map_to_base64(js_vars) for js_vars in comp_js_vars],
        # NOTE: Component call data contains only hashes and IDs. But since this info is taken
        # from the rendered HTML, which could have been tampered with, it's better to escape these to base64 too.
        "componentJsCalls": [
            [
                to_base64(call.comp_cls_id),
                to_base64(call.comp_id),
                # `None` (converted to `null` in JSON) means that the component has no JS variables
                to_base64(call.js_input_hash) if call.js_input_hash is not None else None,
            ]
            for call in comp_calls
        ],
    }

    # NOTE: This data is embedded into the HTML as JSON. It is the responsibility of
    # the client-side code to detect that this script was inserted, and to load the
    # corresponding assets
    # See https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script#embedding_data_in_html
    exec_script_content = json.dumps(exec_script_data)

    # This is for when the script is embedded into the HTML as JSON `<script>` tag
    # The body is just the JSON data itself, because the client-side manager watches
    # for `<script type="application/json" data-djc>` tags and processes them.
    if output_type == "json":
        # Create Script object with `type="application/json"` and `data-djc` attributes
        exec_script = Script(
            kind=script_kind,
            origin_class_id=script_origin_class_id,
            content=exec_script_content,
            attrs={"type": "application/json", "data-djc": True},
        )
    else:
        # This is for when script is loaded as `.js` file (e.g. when fragment that has variables
        # fetches its JS/CSS files). In this case, the script is a function that calls the
        # `_loadComponentScripts()` function - This is the same API that's called with `<script data-djc>` tags,
        # but we just have to call it manually.
        exec_script = Script(
            kind=script_kind,
            origin_class_id=script_origin_class_id,
            content=f"""
            DjangoComponents.manager._loadComponentScripts({exec_script_content});
            """,
            attrs={"type": "text/javascript"},
            wrap=True,
        )
    return exec_script


head_or_body_end_tag_re = re.compile(r"<\/(?:head|body)\s*>", re.DOTALL)


def _insert_js_css_to_default_locations(
    html_content: str,
    js_content: str | None,
    css_content: str | None,
) -> str | None:
    """
    This function tries to insert the JS and CSS content into the default locations.

    JS is inserted at the end of `<body>`, and CSS is inserted at the end of `<head>`.

    We find these tags by looking for the first `</head>` and last `</body>` tags.
    """
    if css_content is None and js_content is None:
        return None

    did_modify_html = False

    first_end_head_tag_index = None
    last_end_body_tag_index = None

    # First check the content for the first `</head>` and last `</body>` tags
    for match in head_or_body_end_tag_re.finditer(html_content):
        tag_name = match[0][2:6]

        # We target the first `</head>`, thus, after we set it, we skip the rest
        if tag_name == "head":
            if css_content is not None and first_end_head_tag_index is None:
                first_end_head_tag_index = match.start()

        # But for `</body>`, we want the last occurrence, so we insert the content only
        # after the loop.
        elif tag_name == "body":
            if js_content is not None:
                last_end_body_tag_index = match.start()

        else:
            raise ValueError(f"Unexpected tag name '{tag_name}'")

    # Then do two string insertions. First the CSS, because we assume that <head> is before <body>.
    index_offset = 0
    updated_html = html_content
    if css_content is not None and first_end_head_tag_index is not None:
        updated_html = updated_html[:first_end_head_tag_index] + css_content + updated_html[first_end_head_tag_index:]
        index_offset = len(css_content)
        did_modify_html = True

    if js_content is not None and last_end_body_tag_index is not None:
        js_index = last_end_body_tag_index + index_offset
        updated_html = updated_html[:js_index] + js_content + updated_html[js_index:]
        did_modify_html = True

    if did_modify_html:
        return updated_html

    return None  # No changes made


#########################################################
# 4. Endpoints for fetching the JS / CSS scripts from within
#    the browser, as defined from previous steps.
#########################################################


CACHE_ENDPOINT_NAME = "components_cached_script"
_CONTENT_TYPES = {"js": "text/javascript", "css": "text/css"}


def _get_content_types(script_type: ScriptType) -> str:
    if script_type not in _CONTENT_TYPES:
        raise ValueError(f"Unknown script_type '{script_type}'")

    return _CONTENT_TYPES[script_type]


def cached_script_view(
    req: HttpRequest,
    comp_cls_id: str,
    script_type: ScriptType,
    variables_hash: str | None = None,
) -> HttpResponse:
    from django_components.component import get_component_by_class_id  # noqa: PLC0415

    if req.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    try:
        comp_cls = get_component_by_class_id(comp_cls_id)
    except KeyError:
        return HttpResponseNotFound()

    script_obj = get_script(script_type, comp_cls, variables_hash)
    if script_obj is None:
        return HttpResponseNotFound()

    # Return the content (not the full HTML tag) for the HTTP response
    if script_obj.content is None:
        # External script/style - this shouldn't happen for cached scripts, but just in case
        return HttpResponseBadRequest(b"No content found for cached script")

    content_type = _get_content_types(script_type)
    content = script_obj.content.encode()
    return HttpResponse(content=content, content_type=content_type)


urlpatterns = [
    # E.g. `/components/cache/MyTable_a1b2c3.js` or `/components/cache/MyTable_a1b2c3.0ab2c3.js`
    path(
        "cache/<str:comp_cls_id>.<str:variables_hash>.<str:script_type>", cached_script_view, name=CACHE_ENDPOINT_NAME
    ),
    path("cache/<str:comp_cls_id>.<str:script_type>", cached_script_view, name=CACHE_ENDPOINT_NAME),
]


#########################################################
# 5. Template tags
#########################################################


def _component_dependencies(dep_type: Literal["js", "css"]) -> SafeString:
    """Marks location where CSS link and JS script tags should be rendered."""
    if dep_type == "css":
        placeholder = CSS_DEPENDENCY_PLACEHOLDER
    elif dep_type == "js":
        placeholder = JS_DEPENDENCY_PLACEHOLDER
    else:
        raise TemplateSyntaxError(
            f"Unknown dependency type in {{% component_dependencies %}}. Must be one of 'css' or 'js', got {dep_type}",
        )

    return mark_safe(placeholder)


class ComponentCssDependenciesNode(BaseNode):
    """
    Marks location where CSS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted into the `<head>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_css_dependencies %}` tags, CSS links
    are by default inserted into the `<head>` tag of the HTML. (See
    [Default JS / CSS locations](../concepts/advanced/rendering_js_css.md#default-js-css-locations))

    Note that there should be only one `{% component_css_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL CSS links will be duplicately inserted into ALL these places.
    """

    tag = "component_css_dependencies"
    end_tag = None  # inline-only
    allowed_flags = ()

    def render(self, context: Context) -> str:  # noqa: ARG002
        return _component_dependencies("css")


class ComponentJsDependenciesNode(BaseNode):
    """
    Marks location where JS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted at the end of the `<body>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_js_dependencies %}` tags, JS scripts
    are by default inserted at the end of the `<body>` tag of the HTML. (See
    [Default JS / CSS locations](../concepts/advanced/rendering_js_css.md#default-js-css-locations))

    Note that there should be only one `{% component_js_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL JS scripts will be duplicately inserted into ALL these places.
    """

    tag = "component_js_dependencies"
    end_tag = None  # inline-only
    allowed_flags = ()

    def render(self, context: Context) -> str:  # noqa: ARG002
        return _component_dependencies("js")
