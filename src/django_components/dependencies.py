"""All code related to management of component dependencies (JS and CSS scripts)"""

import base64
import json
import re
from hashlib import md5
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.forms import Media
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.template import Context, TemplateSyntaxError
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.decorators import sync_and_async_middleware
from django.utils.safestring import SafeString, mark_safe
from djc_core_html_parser import set_html_attributes

from django_components.cache import get_component_media_cache
from django_components.node import BaseNode
from django_components.util.misc import is_nonempty_str

if TYPE_CHECKING:
    from django_components.component import Component


ScriptType = Literal["css", "js"]
RenderType = Literal["document", "fragment"]


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
    input_hash: Optional[str],
) -> str:
    if input_hash:
        return f"__components:{comp_cls_id}:{script_type}:{input_hash}"
    else:
        return f"__components:{comp_cls_id}:{script_type}"


def _is_script_in_cache(
    comp_cls: Type["Component"],
    script_type: ScriptType,
    input_hash: Optional[str],
) -> bool:
    cache_key = _gen_cache_key(comp_cls.class_id, script_type, input_hash)
    cache = get_component_media_cache()
    return cache.has_key(cache_key)


def _cache_script(
    comp_cls: Type["Component"],
    script: str,
    script_type: ScriptType,
    input_hash: Optional[str],
) -> None:
    """
    Given a component and it's inlined JS or CSS, store the JS/CSS in a cache,
    so it can be retrieved via URL endpoint.
    """

    # E.g. `__components:MyButton:js:df7c6d10`
    if script_type in ("js", "css"):
        cache_key = _gen_cache_key(comp_cls.class_id, script_type, input_hash)
    else:
        raise ValueError(f"Unexpected script_type '{script_type}'")

    # NOTE: By setting the script in the cache, we will be able to retrieve it
    # via the endpoint, e.g. when we make a request to `/components/cache/MyComp_ab0c2d.js`.
    cache = get_component_media_cache()
    cache.set(cache_key, script.strip())


def cache_component_js(comp_cls: Type["Component"]) -> None:
    """
    Cache the content from `Component.js`. This is the common JS that's shared
    among all instances of the same component. So even if the component is rendered multiple
    times, this JS is loaded only once.
    """
    if not comp_cls.js or not is_nonempty_str(comp_cls.js) or _is_script_in_cache(comp_cls, "js", None):
        return None

    _cache_script(
        comp_cls=comp_cls,
        script=comp_cls.js,
        script_type="js",
        input_hash=None,
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
#    with `Components.manager.registerComponent`.
# 2. Register the unique set of JS variables (equivalent to defining CSS vars)
#    with `Components.manager.registerComponentData`.
# 3. Actually run a component's JS instance with `Components.manager.callComponent`,
#    specifying the components HTML elements with `component_id`, and JS vars with `input_hash`.
def cache_component_js_vars(comp_cls: Type["Component"], js_vars: Dict) -> Optional[str]:
    if not is_nonempty_str(comp_cls.js):
        return None

    # The hash for the file that holds the JS variables is derived from the variables themselves.
    json_data = json.dumps(js_vars)
    input_hash = md5(json_data.encode()).hexdigest()[0:6]

    # Generate and cache a JS script that contains the JS variables.
    if not _is_script_in_cache(comp_cls, "js", input_hash):
        _cache_script(
            comp_cls=comp_cls,
            script="",  # TODO - enable JS and CSS vars
            script_type="js",
            input_hash=input_hash,
        )

    return input_hash


def wrap_component_js(comp_cls: Type["Component"], content: str) -> str:
    if "</script" in content:
        raise RuntimeError(
            f"Content of `Component.js` for component '{comp_cls.__name__}' contains '</script>' end tag. "
            "This is not allowed, as it would break the HTML."
        )
    return f"<script>{content}</script>"


def cache_component_css(comp_cls: Type["Component"]) -> None:
    """
    Cache the content from `Component.css`. This is the common CSS that's shared
    among all instances of the same component. So even if the component is rendered multiple
    times, this CSS is loaded only once.
    """
    if not comp_cls.css or not is_nonempty_str(comp_cls.css) or _is_script_in_cache(comp_cls, "css", None):
        return None

    _cache_script(
        comp_cls=comp_cls,
        script=comp_cls.css,
        script_type="css",
        input_hash=None,
    )


# NOTE: In CSS, we link the CSS vars to the component via a stylesheet that defines
# the CSS vars under the CSS selector `[data-djc-css-a1b2c3]`. We define the stylesheet
# with variables separately from `Component.css`, because different instances may return different
# data from `get_css_data()`, which will live in different stylesheets.
def cache_component_css_vars(comp_cls: Type["Component"], css_vars: Dict) -> Optional[str]:
    if not is_nonempty_str(comp_cls.css):
        return None

    # The hash for the file that holds the CSS variables is derived from the variables themselves.
    json_data = json.dumps(css_vars)
    input_hash = md5(json_data.encode()).hexdigest()[0:6]

    # Generate and cache a CSS stylesheet that contains the CSS variables.
    if not _is_script_in_cache(comp_cls, "css", input_hash):
        _cache_script(
            comp_cls=comp_cls,
            script="",  # TODO - enable JS and CSS vars
            script_type="css",
            input_hash=input_hash,
        )

    return input_hash


def wrap_component_css(comp_cls: Type["Component"], content: str) -> str:
    if "</style" in content:
        raise RuntimeError(
            f"Content of `Component.css` for component '{comp_cls.__name__}' contains '</style>' end tag. "
            "This is not allowed, as it would break the HTML."
        )
    return f"<style>{content}</style>"


#########################################################
# 2. Modify the HTML to use the same IDs defined in previous
#    step for the inlined CSS and JS scripts, so the scripts
#    can be applied to the correct HTML elements. And embed
#    component + JS/CSS relationships as HTML comments.
#########################################################


def set_component_attrs_for_js_and_css(
    html_content: Union[str, SafeString],
    component_id: Optional[str],
    css_input_hash: Optional[str],
    css_scope_id: Optional[str],
    root_attributes: Optional[List[str]] = None,
) -> Tuple[Union[str, SafeString], Dict[str, List[str]]]:
    # These are the attributes that we want to set on the root element.
    all_root_attributes = [*root_attributes] if root_attributes else []

    # Component ID is used for executing JS script, e.g. `data-djc-id-a1b2c3`
    #
    # NOTE: We use `data-djc-css-a1b2c3` and `data-djc-id-a1b2c3` instead of
    # `data-djc-css="a1b2c3"` and `data-djc-id="a1b2c3"`, to allow
    # multiple values to be associated with the same element, which may happen if
    # one component renders another.
    if component_id:
        all_root_attributes.append(f"data-djc-id-{component_id}")

    # Attribute by which we bind the CSS variables to the component's CSS,
    # e.g. `data-djc-css-a1b2c3`
    if css_input_hash:
        all_root_attributes.append(f"data-djc-css-{css_input_hash}")

    # These attributes are set on all tags
    all_attributes = []

    # We apply the CSS scoping attribute to both root and non-root tags.
    #
    # This is the HTML part of Vue-like CSS scoping.
    # That is, for each HTML element that the component renders, we add a `data-djc-scope-a1b2c3` attribute.
    # And we stop when we come across a nested components.
    if css_scope_id:
        all_attributes.append(f"data-djc-scope-{css_scope_id}")

    is_safestring = isinstance(html_content, SafeString)
    updated_html, child_components = set_html_attributes(
        html_content,
        root_attributes=all_root_attributes,
        all_attributes=all_attributes,
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
    component_cls: Type["Component"],
    component_id: str,
    js_input_hash: Optional[str],
    css_input_hash: Optional[str],
) -> SafeString:
    """
    Given some textual content, prepend it with a short string that
    will be used by the ComponentDependencyMiddleware to collect all
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


TContent = TypeVar("TContent", bound=Union[bytes, str])


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
    rb"^(?P<comp_cls_id>[\w\-\./]+?),(?P<id>[\w]+?),(?P<js>[0-9a-f]*?),(?P<css>[0-9a-f]*?)$"
)
# E.g. `data-djc-id-a1b2c3`
MAYBE_COMP_ID = r'(?: data-djc-id-\w{6}="")?'
# E.g. `data-djc-css-99914b`
MAYBE_COMP_CSS_ID = r'(?: data-djc-css-\w{6}="")?'

PLACEHOLDER_REGEX = re.compile(
    r"{css_placeholder}|{js_placeholder}".format(
        css_placeholder=f'<link name="{CSS_PLACEHOLDER_NAME}"{MAYBE_COMP_CSS_ID}{MAYBE_COMP_ID}/?>',
        js_placeholder=f'<script name="{JS_PLACEHOLDER_NAME}"{MAYBE_COMP_CSS_ID}{MAYBE_COMP_ID}></script>',
    ).encode()
)


def render_dependencies(content: TContent, type: RenderType = "document") -> TContent:
    """
    Given a string that contains parts that were rendered by components,
    this function inserts all used JS and CSS.

    By default, the string is parsed as an HTML and:
    - CSS is inserted at the end of `<head>` (if present)
    - JS is inserted at the end of `<body>` (if present)

    If you used `{% component_js_dependencies %}` or `{% component_css_dependencies %}`,
    then the JS and CSS will be inserted only at these locations.

    Example:
    ```python
    def my_view(request):
        template = Template('''
            {% load components %}
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
    if type not in ("document", "fragment"):
        raise ValueError(f"Invalid type '{type}'")

    is_safestring = isinstance(content, SafeString)

    if isinstance(content, str):
        content_ = content.encode()
    else:
        content_ = cast(bytes, content)

    content_, js_dependencies, css_dependencies = _process_dep_declarations(content_, type)

    # Replace the placeholders with the actual content
    # If type == `document`, we insert the JS and CSS directly into the HTML,
    #                        where the placeholders were.
    # If type == `fragment`, we let the client-side manager load the JS and CSS,
    #                        and remove the placeholders.
    did_find_js_placeholder = False
    did_find_css_placeholder = False
    css_replacement = css_dependencies if type == "document" else b""
    js_replacement = js_dependencies if type == "document" else b""

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
                f" matched unknown string '{match[0].decode()}'"
            )
        return replacement

    content_ = PLACEHOLDER_REGEX.sub(on_replace_match, content_)

    # By default, if user didn't specify any `{% component_dependencies %}`,
    # then try to insert the JS scripts at the end of <body> and CSS sheets at the end
    # of <head>
    if type == "document" and (not did_find_js_placeholder or not did_find_css_placeholder):
        maybe_transformed = _insert_js_css_to_default_locations(
            content_.decode(),
            css_content=None if did_find_css_placeholder else css_dependencies.decode(),
            js_content=None if did_find_js_placeholder else js_dependencies.decode(),
        )

        if maybe_transformed is not None:
            content_ = maybe_transformed.encode()

    # In case of a fragment, we only append the JS (actually JSON) to trigger the call of dependency-manager
    if type == "fragment":
        content_ += js_dependencies

    # Return the same type as we were given
    output = content_.decode() if isinstance(content, str) else content_
    output = mark_safe(output) if is_safestring else output
    return cast(TContent, output)


# Renamed so we can access use this function where there's kwarg of the same name
_render_dependencies = render_dependencies


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
def _process_dep_declarations(content: bytes, type: RenderType) -> Tuple[bytes, bytes, bytes]:
    """
    Process a textual content that may include metadata on rendered components.
    The metadata has format like this

    `<!-- _RENDERED component_name,component_id,js_hash,css_hash;... -->`

    E.g.

    `<!-- _RENDERED table_10bac31,123,a92ef298,bd002c3 -->`
    """
    # Extract all matched instances of `<!-- _RENDERED ... -->` while also removing them from the text
    all_parts: List[bytes] = list()

    def on_replace_match(match: "re.Match[bytes]") -> bytes:
        all_parts.append(match.group("data"))
        return b""

    content = COMPONENT_COMMENT_REGEX.sub(on_replace_match, content)

    # NOTE: Python's set does NOT preserve order
    seen_comp_hashes: Set[str] = set()
    comp_hashes: List[str] = []
    # Used for passing Python vars to JS/CSS
    inputs_data: List[Tuple[str, ScriptType, Optional[str]]] = []
    comp_data: List[Tuple[str, ScriptType, Optional[str]]] = []

    # Process individual parts. Each part is like a CSV row of `name,id,js,css`.
    # E.g. something like this:
    # `table_10bac31,1234,a92ef298,a92ef298`
    for part in all_parts:
        part_match = SCRIPT_NAME_REGEX.match(part)

        if not part_match:
            raise RuntimeError("Malformed dependencies data")

        comp_cls_id: str = part_match.group("comp_cls_id").decode("utf-8")
        js_input_hash: Optional[str] = part_match.group("js").decode("utf-8") or None
        css_input_hash: Optional[str] = part_match.group("css").decode("utf-8") or None

        if comp_cls_id in seen_comp_hashes:
            continue

        comp_hashes.append(comp_cls_id)
        seen_comp_hashes.add(comp_cls_id)

        # Schedule to load the `<script>` / `<link>` tags for the JS / CSS from `Component.js/css`.
        comp_data.append((comp_cls_id, "js", None))
        comp_data.append((comp_cls_id, "css", None))

        # Schedule to load the `<script>` / `<link>` tags for the JS / CSS variables.
        # Skip if no variables are defined.
        if js_input_hash is not None:
            inputs_data.append((comp_cls_id, "js", js_input_hash))
        if css_input_hash is not None:
            inputs_data.append((comp_cls_id, "css", css_input_hash))

    (
        to_load_input_js_urls,
        to_load_input_css_urls,
        inlined_input_js_tags,
        inlined_input_css_tags,
        loaded_input_js_urls,
        loaded_input_css_urls,
    ) = _prepare_tags_and_urls(inputs_data, type)

    (
        to_load_component_js_urls,
        to_load_component_css_urls,
        inlined_component_js_tags,
        inlined_component_css_tags,
        loaded_component_js_urls,
        loaded_component_css_urls,
    ) = _prepare_tags_and_urls(comp_data, type)

    def get_component_media(comp_cls_id: str) -> Media:
        from django_components.component import get_component_by_class_id

        comp_cls = get_component_by_class_id(comp_cls_id)
        # NOTE: We instantiate the component classes so the `Media` are processed into `media`
        comp = comp_cls()
        return comp.media

    all_medias = [
        # JS / CSS files from Component.Media.js/css.
        *[get_component_media(comp_cls_id) for comp_cls_id in comp_hashes],
        # All the inlined scripts that we plan to fetch / load
        Media(
            js=[*to_load_component_js_urls, *to_load_input_js_urls],
            css={"all": [*to_load_component_css_urls, *to_load_input_css_urls]},
        ),
    ]

    # Once we have ALL JS and CSS URLs that we want to fetch, we can convert them to
    # <script> and <link> tags. Note that this is done by the user-provided Media classes.
    # fmt: off
    to_load_css_tags = [
        tag
        for media in all_medias if media is not None
        for tag in media.render_css()
    ]
    to_load_js_tags = [
        tag
        for media in all_medias if media is not None
        for tag in media.render_js()
    ]
    # fmt: on

    # Postprocess all <script> and <link> tags to 1) dedupe, and 2) extract URLs.
    # For the deduplication, if multiple components link to the same JS/CSS, but they
    # render the <script> or <link> tag differently, we go with the first tag that we come across.
    to_load_css_tags, to_load_css_urls = _postprocess_media_tags("css", to_load_css_tags)
    to_load_js_tags, to_load_js_urls = _postprocess_media_tags("js", to_load_js_tags)

    loaded_css_urls = sorted(
        [
            *loaded_component_css_urls,
            *loaded_input_css_urls,
            # NOTE: When rendering a document, the initial CSS is inserted directly into the HTML
            # to avoid a flash of unstyled content. In the dependency manager, we only mark those
            # scripts as loaded.
            *(to_load_css_urls if type == "document" else []),
        ]
    )
    loaded_js_urls = sorted(
        [
            *loaded_component_js_urls,
            *loaded_input_js_urls,
            # NOTE: When rendering a document, the initial JS is inserted directly into the HTML
            # so the scripts are executed at proper order. In the dependency manager, we only mark those
            # scripts as loaded.
            *(to_load_js_urls if type == "document" else []),
        ]
    )

    exec_script = _gen_exec_script(
        to_load_js_tags=to_load_js_tags if type == "fragment" else [],
        to_load_css_tags=to_load_css_tags if type == "fragment" else [],
        loaded_js_urls=loaded_js_urls,
        loaded_css_urls=loaded_css_urls,
    )

    # Core scripts without which the rest wouldn't work
    core_script_tags = Media(
        # NOTE: When rendering a document, the initial JS is inserted directly into the HTML
        js=[static("django_components/django_components.min.js")] if type == "document" else [],
    ).render_js()

    final_script_tags = "".join(
        [
            # JS by us
            *[tag for tag in core_script_tags],
            # Make calls to the JS dependency manager
            # Loads JS from `Media.js` and `Component.js` if fragment
            *([exec_script] if exec_script else []),
            # JS from `Media.js`
            # NOTE: When rendering a document, the initial JS is inserted directly into the HTML
            # so the scripts are executed at proper order. In the dependency manager, we only mark those
            # scripts as loaded.
            *(to_load_js_tags if type == "document" else []),
            # JS variables
            *[tag for tag in inlined_input_js_tags],
            # JS from `Component.js` (if not fragment)
            *[tag for tag in inlined_component_js_tags],
        ]
    )

    final_css_tags = "".join(
        [
            # CSS by us
            # <NONE>
            # CSS from `Component.css` (if not fragment)
            *[tag for tag in inlined_component_css_tags],
            # CSS variables
            *[tag for tag in inlined_input_css_tags],
            # CSS from `Media.css` (plus from `Component.css` if fragment)
            # NOTE: Similarly to JS, the initial CSS is loaded outside of the dependency
            #       manager, and only marked as loaded, to avoid a flash of unstyled content.
            *[tag for tag in to_load_css_tags],
        ]
    )

    return (content, final_script_tags.encode("utf-8"), final_css_tags.encode("utf-8"))


href_pattern = re.compile(r'href="([^"]+)"')
src_pattern = re.compile(r'src="([^"]+)"')


# Detect duplicates by URLs, extract URLs, and sort by URLs
def _postprocess_media_tags(
    script_type: ScriptType,
    tags: List[str],
) -> Tuple[List[str], List[str]]:
    urls: List[str] = []
    tags_by_url: Dict[str, str] = {}

    for tag in tags:
        # Extract the URL from <script src="..."> or <link href="...">
        if script_type == "js":
            attr = "src"
            attr_pattern = src_pattern
        else:
            attr = "href"
            attr_pattern = href_pattern

        maybe_url_match = attr_pattern.search(tag.strip())
        maybe_url = maybe_url_match.group(1) if maybe_url_match else None

        if not is_nonempty_str(maybe_url):
            raise RuntimeError(
                f"One of entries for `Component.Media.{script_type}` media is missing a "
                f"value for attribute '{attr}'. If there is content inlined inside the `<{attr}>` tags, "
                f"you must move the content to a `.{script_type}` file and reference it via '{attr}'.\nGot:\n{tag}"
            )

        url = cast(str, maybe_url)

        # Skip duplicates
        if url in tags_by_url:
            continue

        tags_by_url[url] = tag
        urls.append(url)

    # Ensure consistent order
    tags = [tags_by_url[url] for url in urls]

    return tags, urls


def _prepare_tags_and_urls(
    data: List[Tuple[str, ScriptType, Optional[str]]],
    type: RenderType,
) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
    from django_components.component import get_component_by_class_id

    to_load_js_urls: List[str] = []
    to_load_css_urls: List[str] = []
    inlined_js_tags: List[str] = []
    inlined_css_tags: List[str] = []
    loaded_js_urls: List[str] = []
    loaded_css_urls: List[str] = []

    # When `type="document"`, we insert the actual <script> and <style> tags into the HTML.
    # But even in that case we still need to call `Components.manager.markScriptLoaded`,
    # so the client knows NOT to fetch them again.
    # So in that case we populate both `inlined` and `loaded` lists
    for comp_cls_id, script_type, input_hash in data:
        # NOTE: When CSS is scoped, then EVERY component instance will have different
        # copy of the style, because each copy will have component's ID embedded.
        # So, in that case we inline the style into the HTML (See `_link_dependencies_with_component_html`),
        # which means that we are NOT going to load / inline it again.
        comp_cls = get_component_by_class_id(comp_cls_id)

        if type == "document":
            # NOTE: Skip fetching of inlined JS/CSS if it's not defined or empty for given component
            #
            # NOTE: If `input_hash` is `None`, then we get the component's JS/CSS
            #       (e.g. `/components/cache/table.js`).
            #       And if `input_hash` is given, we get the component's JS/CSS variables
            #       (e.g. `/components/cache/table.0ab2c3.js`).
            if script_type == "js" and is_nonempty_str(comp_cls.js):
                inlined_js_tags.append(get_script_tag("js", comp_cls, input_hash))
                loaded_js_urls.append(get_script_url("js", comp_cls, input_hash))

            if script_type == "css" and is_nonempty_str(comp_cls.css):
                inlined_css_tags.append(get_script_tag("css", comp_cls, input_hash))
                loaded_css_urls.append(get_script_url("css", comp_cls, input_hash))

        # When NOT a document (AKA is a fragment), then scripts are NOT inserted into
        # the HTML, and instead we fetch and load them all via our JS dependency manager.
        else:
            if script_type == "js" and is_nonempty_str(comp_cls.js):
                to_load_js_urls.append(get_script_url("js", comp_cls, input_hash))

            if script_type == "css" and is_nonempty_str(comp_cls.css):
                to_load_css_urls.append(get_script_url("css", comp_cls, input_hash))

    return (
        to_load_js_urls,
        to_load_css_urls,
        inlined_js_tags,
        inlined_css_tags,
        loaded_js_urls,
        loaded_css_urls,
    )


def get_script_content(
    script_type: ScriptType,
    comp_cls: Type["Component"],
    input_hash: Optional[str],
) -> Optional[str]:
    cache = get_component_media_cache()
    cache_key = _gen_cache_key(comp_cls.class_id, script_type, input_hash)
    script = cache.get(cache_key)

    return script


def get_script_tag(
    script_type: ScriptType,
    comp_cls: Type["Component"],
    input_hash: Optional[str],
) -> str:
    content = get_script_content(script_type, comp_cls, input_hash)
    if content is None:
        raise RuntimeError(
            f"Could not find {script_type.upper()} for component '{comp_cls.__name__}' (id: {comp_cls.class_id})"
        )

    if script_type == "js":
        content = wrap_component_js(comp_cls, content)
    elif script_type == "css":
        content = wrap_component_css(comp_cls, content)
    else:
        raise ValueError(f"Unexpected script_type '{script_type}'")

    return content


def get_script_url(
    script_type: ScriptType,
    comp_cls: Type["Component"],
    input_hash: Optional[str],
) -> str:
    return reverse(
        CACHE_ENDPOINT_NAME,
        kwargs={
            "comp_cls_id": comp_cls.class_id,
            "script_type": script_type,
            **({"input_hash": input_hash} if input_hash is not None else {}),
        },
    )


def _gen_exec_script(
    to_load_js_tags: List[str],
    to_load_css_tags: List[str],
    loaded_js_urls: List[str],
    loaded_css_urls: List[str],
) -> Optional[str]:
    # Return None if all lists are empty
    if not any([to_load_js_tags, to_load_css_tags, loaded_css_urls, loaded_js_urls]):
        return None

    def map_to_base64(lst: Sequence[str]) -> List[str]:
        return [base64.b64encode(tag.encode()).decode() for tag in lst]

    # Generate JSON that will tell the JS dependency manager which JS and CSS to load
    #
    # NOTE: It would be simpler to pass only the URL itself for `loadJs/loadCss`, instead of a whole tag.
    #    But because we allow users to specify the Media class, and thus users can
    #    configure how the `<link>` or `<script>` tags are rendered, we need pass the whole tag.
    #
    # NOTE 2: Convert to Base64 to avoid any issues with `</script>` tags in the content
    exec_script_data = {
        "loadedCssUrls": map_to_base64(loaded_css_urls),
        "loadedJsUrls": map_to_base64(loaded_js_urls),
        "toLoadCssTags": map_to_base64(to_load_css_tags),
        "toLoadJsTags": map_to_base64(to_load_js_tags),
    }

    # NOTE: This data is embedded into the HTML as JSON. It is the responsibility of
    # the client-side code to detect that this script was inserted, and to load the
    # corresponding assets
    # See https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script#embedding_data_in_html
    exec_script = json.dumps(exec_script_data)
    exec_script = f'<script type="application/json" data-djc>{exec_script}</script>'
    return exec_script


head_or_body_end_tag_re = re.compile(r"<\/(?:head|body)\s*>", re.DOTALL)


def _insert_js_css_to_default_locations(
    html_content: str,
    js_content: Optional[str],
    css_content: Optional[str],
) -> Optional[str]:
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
    else:
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
    input_hash: Optional[str] = None,
) -> HttpResponse:
    from django_components.component import get_component_by_class_id

    if req.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    try:
        comp_cls = get_component_by_class_id(comp_cls_id)
    except KeyError:
        return HttpResponseNotFound()

    script = get_script_content(script_type, comp_cls, input_hash)
    if script is None:
        return HttpResponseNotFound()

    content_type = _get_content_types(script_type)
    return HttpResponse(content=script, content_type=content_type)


urlpatterns = [
    # E.g. `/components/cache/MyTable_a1b2c3.js` or `/components/cache/MyTable_a1b2c3.0ab2c3.js`
    path("cache/<str:comp_cls_id>.<str:input_hash>.<str:script_type>", cached_script_view, name=CACHE_ENDPOINT_NAME),
    path("cache/<str:comp_cls_id>.<str:script_type>", cached_script_view, name=CACHE_ENDPOINT_NAME),
]


#########################################################
# 5. Middleware that automatically applies the dependency-
#    aggregating logic on all HTML responses.
#########################################################


@sync_and_async_middleware
class ComponentDependencyMiddleware:
    """
    Middleware that inserts CSS/JS dependencies for all rendered
    components at points marked with template tags.
    """

    def __init__(self, get_response: "Callable[[HttpRequest], HttpResponse]") -> None:
        self._get_response = get_response

        # NOTE: Required to work with async
        if iscoroutinefunction(self._get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        if iscoroutinefunction(self):
            return self.__acall__(request)

        response = self._get_response(request)
        response = self._process_response(response)
        return response

    # NOTE: Required to work with async
    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        response = await self._get_response(request)
        response = self._process_response(response)
        return response

    def _process_response(self, response: HttpResponse) -> HttpResponse:
        if not isinstance(response, StreamingHttpResponse) and response.get("Content-Type", "").startswith(
            "text/html"
        ):
            response.content = render_dependencies(response.content, type="document")

        return response


#########################################################
# 6. Template tags
#########################################################


def _component_dependencies(type: Literal["js", "css"]) -> SafeString:
    """Marks location where CSS link and JS script tags should be rendered."""
    if type == "css":
        placeholder = CSS_DEPENDENCY_PLACEHOLDER
    elif type == "js":
        placeholder = JS_DEPENDENCY_PLACEHOLDER
    else:
        raise TemplateSyntaxError(
            f"Unknown dependency type in {{% component_dependencies %}}. Must be one of 'css' or 'js', got {type}"
        )

    return mark_safe(placeholder)


class ComponentCssDependenciesNode(BaseNode):
    """
    Marks location where CSS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted into the `<head>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_css_dependencies %}` tags, CSS links
    are by default inserted into the `<head>` tag of the HTML. (See
    [JS and CSS output locations](../../concepts/advanced/rendering_js_css/#js-and-css-output-locations))

    Note that there should be only one `{% component_css_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL CSS links will be duplicately inserted into ALL these places.
    """

    tag = "component_css_dependencies"
    end_tag = None  # inline-only
    allowed_flags = []

    def render(self, context: Context) -> str:
        return _component_dependencies("css")


class ComponentJsDependenciesNode(BaseNode):
    """
    Marks location where JS link tags should be rendered after the whole HTML has been generated.

    Generally, this should be inserted at the end of the `<body>` tag of the HTML.

    If the generated HTML does NOT contain any `{% component_js_dependencies %}` tags, JS scripts
    are by default inserted at the end of the `<body>` tag of the HTML. (See
    [JS and CSS output locations](../../concepts/advanced/rendering_js_css/#js-and-css-output-locations))

    Note that there should be only one `{% component_js_dependencies %}` for the whole HTML document.
    If you insert this tag multiple times, ALL JS scripts will be duplicately inserted into ALL these places.
    """

    tag = "component_js_dependencies"
    end_tag = None  # inline-only
    allowed_flags = []

    def render(self, context: Context) -> str:
        return _component_dependencies("js")
