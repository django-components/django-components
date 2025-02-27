"""All code related to management of component dependencies (JS and CSS scripts)"""

import base64
import json
import re
import sys
from abc import ABC, abstractmethod
from functools import lru_cache
from hashlib import md5
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from weakref import WeakValueDictionary

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.forms import Media
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.decorators import sync_and_async_middleware
from django.utils.safestring import SafeString, mark_safe

from django_components.util.html import SoupNode
from django_components.util.misc import get_import_path

if TYPE_CHECKING:
    from django_components.component import Component


ScriptType = Literal["css", "js"]
RenderType = Literal["document", "fragment"]


#########################################################
# 1. Cache the inlined component JS and CSS scripts,
#    so they can be referenced and retrieved later via
#    an ID.
#########################################################


class ComponentMediaCacheABC(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[str]: ...  # noqa: #704

    @abstractmethod
    def has(self, key: str) -> bool: ...  # noqa: #704

    @abstractmethod
    def set(self, key: str, value: str) -> None: ...  # noqa: #704


class InMemoryComponentMediaCache(ComponentMediaCacheABC):
    def __init__(self) -> None:
        self._data: Dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key, None)

    def has(self, key: str) -> bool:
        return key in self._data

    def set(self, key: str, value: str) -> None:
        self._data[key] = value


comp_media_cache = InMemoryComponentMediaCache()


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
# E.g. `path.to.my.secret.MyComponent` -> `MyComponent_ab01f32`
#
# The associations are defined as WeakValue map, so deleted components can be garbage
# collected and automatically deleted from the dict.
if sys.version_info < (3, 9):
    comp_hash_mapping: WeakValueDictionary = WeakValueDictionary()
else:
    comp_hash_mapping: WeakValueDictionary[str, Type["Component"]] = WeakValueDictionary()


# Convert Component class to something like `TableComp_a91d03`
@lru_cache(None)
def _hash_comp_cls(comp_cls: Type["Component"]) -> str:
    full_name = get_import_path(comp_cls)
    comp_cls_hash = md5(full_name.encode()).hexdigest()[0:6]
    return comp_cls.__name__ + "_" + comp_cls_hash


def _gen_cache_key(
    comp_cls_hash: str,
    script_type: ScriptType,
) -> str:
    return f"__components:{comp_cls_hash}:{script_type}"


def _is_script_in_cache(
    comp_cls: Type["Component"],
    script_type: ScriptType,
) -> bool:
    comp_cls_hash = _hash_comp_cls(comp_cls)
    cache_key = _gen_cache_key(comp_cls_hash, script_type)
    return comp_media_cache.has(cache_key)


def _cache_script(
    comp_cls: Type["Component"],
    script: str,
    script_type: ScriptType,
) -> None:
    """
    Given a component and it's inlined JS or CSS, store the JS/CSS in a cache,
    so it can be retrieved via URL endpoint.
    """
    comp_cls_hash = _hash_comp_cls(comp_cls)

    # E.g. `__components:MyButton:js:df7c6d10`
    if script_type in ("js", "css"):
        cache_key = _gen_cache_key(comp_cls_hash, script_type)
    else:
        raise ValueError(f"Unexpected script_type '{script_type}'")

    # NOTE: By setting the script in the cache, we will be able to retrieve it
    # via the endpoint, e.g. when we make a request to `/components/cache/MyComp_ab0c2d.js`.
    comp_media_cache.set(cache_key, script.strip())


def cache_inlined_js(comp_cls: Type["Component"], content: str) -> None:
    if not _is_nonempty_str(comp_cls.js):
        return

    # Prepare the script that's common to all instances of the same component
    # E.g. `my_table.js`
    if not _is_script_in_cache(comp_cls, "js"):
        _cache_script(
            comp_cls=comp_cls,
            script=content,
            script_type="js",
        )


def cache_inlined_css(comp_cls: Type["Component"], content: str) -> None:
    if not _is_nonempty_str(comp_cls.js):
        return

    # Prepare the script that's common to all instances of the same component
    if not _is_script_in_cache(comp_cls, "css"):
        # E.g. `my_table.css`
        _cache_script(
            comp_cls=comp_cls,
            script=content,
            script_type="css",
        )


#########################################################
# 2. Modify the HTML to use the same IDs defined in previous
#    step for the inlined CSS and JS scripts, so the scripts
#    can be applied to the correct HTML elements. And embed
#    component + JS/CSS relationships as HTML comments.
#########################################################


class Dependencies(NamedTuple):
    # NOTE: We pass around the component CLASS, so the dependencies logic is not
    # dependent on ComponentRegistries
    component_cls: Type["Component"]
    component_id: str


def _insert_component_comment(
    content: str,
    deps: Dependencies,
) -> str:
    """
    Given some textual content, prepend it with a short string that
    will be used by the ComponentDependencyMiddleware to collect all
    declared JS / CSS scripts.
    """
    # Add components to the cache
    comp_cls_hash = _hash_comp_cls(deps.component_cls)
    comp_hash_mapping[comp_cls_hash] = deps.component_cls

    data = f"{comp_cls_hash},{deps.component_id}"

    # NOTE: It's important that we put the comment BEFORE the content, so we can
    # use the order of comments to evaluate components' instance JS code in the correct order.
    output = mark_safe(COMPONENT_DEPS_COMMENT.format(data=data)) + content
    return output


# Anything and everything that needs to be done with a Component's HTML
# script in order to support running JS and CSS per-instance.
def postprocess_component_html(
    component_cls: Type["Component"],
    component_id: str,
    html_content: str,
    type: RenderType,
    render_dependencies: bool,
) -> str:
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

    # Mark the generated HTML so that we will know which JS and CSS
    # scripts are associated with it.
    output = _insert_component_comment(
        html_content,
        Dependencies(
            component_cls=component_cls,
            component_id=component_id,
        ),
    )

    if render_dependencies:
        output = _render_dependencies(output, type)
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


CSS_DEPENDENCY_PLACEHOLDER = '<link name="CSS_PLACEHOLDER">'
JS_DEPENDENCY_PLACEHOLDER = '<script name="JS_PLACEHOLDER"></script>'

CSS_PLACEHOLDER_BYTES = bytes(CSS_DEPENDENCY_PLACEHOLDER, encoding="utf-8")
JS_PLACEHOLDER_BYTES = bytes(JS_DEPENDENCY_PLACEHOLDER, encoding="utf-8")

COMPONENT_DEPS_COMMENT = "<!-- _RENDERED {data} -->"
# E.g. `<!-- _RENDERED table,123 -->`
COMPONENT_COMMENT_REGEX = re.compile(rb"<!-- _RENDERED (?P<data>[\w\-,/]+?) -->")
# E.g. `table,123`
SCRIPT_NAME_REGEX = re.compile(rb"^(?P<comp_cls_hash>[\w\-\./]+?),(?P<id>[\w]+?)$")
PLACEHOLDER_REGEX = re.compile(
    r"{css_placeholder}|{js_placeholder}".format(
        css_placeholder=CSS_DEPENDENCY_PLACEHOLDER,
        js_placeholder=JS_DEPENDENCY_PLACEHOLDER,
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

        if match[0] == CSS_PLACEHOLDER_BYTES:
            replacement = css_replacement
            did_find_css_placeholder = True
        elif match[0] == JS_PLACEHOLDER_BYTES:
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

    `<!-- _RENDERED component_name,component_id -->`

    E.g.

    `<!-- _RENDERED table_10bac31,123 -->`
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

    # Process individual parts. Each part is like a CSV row of `name,id`.
    # E.g. something like this:
    # `table_10bac31,1234`
    for part in all_parts:
        part_match = SCRIPT_NAME_REGEX.match(part)

        if not part_match:
            raise RuntimeError("Malformed dependencies data")

        comp_cls_hash = part_match.group("comp_cls_hash").decode("utf-8")
        if comp_cls_hash in seen_comp_hashes:
            continue

        comp_hashes.append(comp_cls_hash)
        seen_comp_hashes.add(comp_cls_hash)

    (
        to_load_component_js_urls,
        to_load_component_css_urls,
        inlined_component_js_tags,
        inlined_component_css_tags,
        loaded_component_js_urls,
        loaded_component_css_urls,
    ) = _prepare_tags_and_urls(comp_hashes, type)

    def get_component_media(comp_cls_hash: str) -> Media:
        comp_cls = comp_hash_mapping[comp_cls_hash]
        # NOTE: We instantiate the component classes so the `Media` are processed into `media`
        comp = comp_cls()
        return comp.media

    all_medias = [
        # JS / CSS files from Component.Media.js/css.
        *[get_component_media(comp_cls_hash) for comp_cls_hash in comp_hashes],
        # All the inlined scripts that we plan to fetch / load
        Media(
            js=to_load_component_js_urls,
            css={"all": to_load_component_css_urls},
        ),
    ]

    # Once we have ALL JS and CSS URLs that we want to fetch, we can convert them to
    # <script> and <link> tags. Note that this is done by the user-provided Media classes.
    to_load_css_tags = [tag for media in all_medias for tag in media.render_css()]
    to_load_js_tags = [tag for media in all_medias for tag in media.render_js()]

    # Postprocess all <script> and <link> tags to 1) dedupe, and 2) extract URLs.
    # For the deduplication, if multiple components link to the same JS/CSS, but they
    # render the <script> or <link> tag differently, we go with the first tag that we come across.
    to_load_css_tags, to_load_css_urls = _postprocess_media_tags("css", to_load_css_tags)
    to_load_js_tags, to_load_js_urls = _postprocess_media_tags("js", to_load_js_tags)

    loaded_css_urls = sorted(
        [
            *loaded_component_css_urls,
            # NOTE: When rendering a document, the initial CSS is inserted directly into the HTML
            # to avoid a flash of unstyled content. In the dependency manager, we only mark those
            # scripts as loaded.
            *(to_load_css_urls if type == "document" else []),
        ]
    )
    loaded_js_urls = sorted(
        [
            *loaded_component_js_urls,
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
            # CSS from `Media.css` (plus from `Component.css` if fragment)
            # NOTE: Similarly to JS, the initial CSS is loaded outside of the dependency
            #       manager, and only marked as loaded, to avoid a flash of unstyled content.
            *[tag for tag in to_load_css_tags],
        ]
    )

    return (content, final_script_tags.encode("utf-8"), final_css_tags.encode("utf-8"))


def _is_nonempty_str(txt: Optional[str]) -> bool:
    return txt is not None and bool(txt.strip())


# Detect duplicates by URLs, extract URLs, and sort by URLs
def _postprocess_media_tags(
    script_type: ScriptType,
    tags: List[str],
) -> Tuple[List[str], List[str]]:
    urls: List[str] = []
    tags_by_url: Dict[str, str] = {}

    for tag in tags:
        node = SoupNode.from_fragment(tag.strip())[0]
        # <script src="..."> vs <link href="...">
        attr = "src" if script_type == "js" else "href"
        maybe_url = node.get_attr(attr, None)

        if not _is_nonempty_str(maybe_url):
            raise RuntimeError(
                f"One of entries for `Component.Media.{script_type}` media is missing a "
                f"value for attribute '{attr}'. If there is content inlined inside the `<{node.name()}>` tags, "
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
    data: Iterable[str],
    type: RenderType,
) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
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
    for comp_cls_hash in data:
        # NOTE: When CSS is scoped, then EVERY component instance will have different
        # copy of the style, because each copy will have component's ID embedded.
        # So, in that case we inline the style into the HTML (See `_link_dependencies_with_component_html`),
        # which means that we are NOT going to load / inline it again.
        comp_cls = comp_hash_mapping[comp_cls_hash]

        if type == "document":
            # NOTE: Skip fetching of inlined JS/CSS if it's not defined or empty for given component
            if _is_nonempty_str(comp_cls.js):
                inlined_js_tags.append(_get_script_tag("js", comp_cls))
                loaded_js_urls.append(get_script_url("js", comp_cls))

            if _is_nonempty_str(comp_cls.css):
                inlined_css_tags.append(_get_script_tag("css", comp_cls))
                loaded_css_urls.append(get_script_url("css", comp_cls))

        # When NOT a document (AKA is a fragment), then scripts are NOT inserted into
        # the HTML, and instead we fetch and load them all via our JS dependency manager.
        else:
            if _is_nonempty_str(comp_cls.js):
                to_load_js_urls.append(get_script_url("js", comp_cls))

            if _is_nonempty_str(comp_cls.css):
                to_load_css_urls.append(get_script_url("css", comp_cls))

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
) -> SafeString:
    comp_cls_hash = _hash_comp_cls(comp_cls)
    cache_key = _gen_cache_key(comp_cls_hash, script_type)
    script = comp_media_cache.get(cache_key)

    return script


def _get_script_tag(
    script_type: ScriptType,
    comp_cls: Type["Component"],
) -> SafeString:
    script = get_script_content(script_type, comp_cls)

    if script_type == "js":
        if "</script" in script:
            raise RuntimeError(
                f"Content of `Component.js` for component '{comp_cls.__name__}' contains '</script>' end tag. "
                "This is not allowed, as it would break the HTML."
            )
        return f"<script>{script}</script>"

    elif script_type == "css":
        if "</style" in script:
            raise RuntimeError(
                f"Content of `Component.css` for component '{comp_cls.__name__}' contains '</style>' end tag. "
                "This is not allowed, as it would break the HTML."
            )

        return f"<style>{script}</style>"

    return script


def get_script_url(
    script_type: ScriptType,
    comp_cls: Type["Component"],
) -> str:
    comp_cls_hash = _hash_comp_cls(comp_cls)

    return reverse(
        CACHE_ENDPOINT_NAME,
        kwargs={
            "comp_cls_hash": comp_cls_hash,
            "script_type": script_type,
        },
    )


def _gen_exec_script(
    to_load_js_tags: List[str],
    to_load_css_tags: List[str],
    loaded_js_urls: List[str],
    loaded_css_urls: List[str],
) -> Optional[str]:
    if not to_load_js_tags and not to_load_css_tags and not loaded_css_urls and not loaded_js_urls:
        return None

    def map_to_base64(lst: List[str]) -> List[str]:
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


def _insert_js_css_to_default_locations(
    html_content: str,
    js_content: Optional[str],
    css_content: Optional[str],
) -> Optional[str]:
    """
    This function tries to insert the JS and CSS content into the default locations.

    JS is inserted at the end of `<body>`, and CSS is inserted at the end of `<head>`.
    """
    elems = SoupNode.from_fragment(html_content)

    if not elems:
        return None

    did_modify_html = False

    if css_content is not None:
        for elem in elems:
            if not elem.is_element():
                continue
            head = elem.find_tag("head")
            if head:
                css_elems = SoupNode.from_fragment(css_content)
                head.append_children(css_elems)
                did_modify_html = True

    if js_content is not None:
        for elem in elems:
            if not elem.is_element():
                continue
            body = elem.find_tag("body")
            if body:
                js_elems = SoupNode.from_fragment(js_content)
                body.append_children(js_elems)
                did_modify_html = True

    if did_modify_html:
        transformed = SoupNode.to_html_multiroot(elems)
        return transformed
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
    comp_cls_hash: str,
    script_type: ScriptType,
) -> HttpResponse:
    if req.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    # Otherwise check if the file is among the dynamically generated files in the cache
    cache_key = _gen_cache_key(comp_cls_hash, script_type)
    script = comp_media_cache.get(cache_key)

    if script is None:
        return HttpResponseNotFound()

    content_type = _get_content_types(script_type)
    return HttpResponse(content=script, content_type=content_type)


urlpatterns = [
    # E.g. `/components/cache/table.js`
    path("cache/<str:comp_cls_hash>.<str:script_type>", cached_script_view, name=CACHE_ENDPOINT_NAME),
]


#########################################################
# 5. Middleware that automatically applies the dependency-
#    aggregating logic on all HTML responses.
#########################################################

def decide_render_type_htmx(request: HttpRequest) -> Literal["fragment", "document"]:
    assert hasattr(request, "htmx"), "The htmx middleware is not installed"
    if request.htmx:
        return "fragment"
    return "document"

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
        response = self._process_response(request, response)
        return response

    # NOTE: Required to work with async
    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        response = await self._get_response(request)
        response = self._process_response(request, response)
        return response

    def _process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if not isinstance(response, StreamingHttpResponse) and response.get("Content-Type", "").startswith(
            "text/html"
        ):
            render_type = decide_render_type_htmx(request)
            response.content = render_dependencies(response.content, type=render_type)

        return response