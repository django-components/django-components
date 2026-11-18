"""
Injected page markup must not change how the client-side manager loads.

These tests render real pages in Python and show them to a real browser. Playwright answers every
request, so they use no port: `http://app.test` is the app, and `http://other.test` stands for
the attacker's site. A file from that site changes `document.title`, which is harmless and easy to see.

The tests use Playwright's sync API because `djc_test` applies its settings and its cleanup around
the call to the test function, and an async test function does its work after that call returns.
"""

import base64
import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pytest
from django.template import Context, Template
from django.test import Client
from playwright.sync_api import sync_playwright

import django_components
from django_components import Component, ComponentExtension, OnDependenciesContext, register, types
from django_components.testing import djc_test
from tests.e2e.utils import BROWSER_NAMES
from tests.testutils import setup_test_config

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest
    from playwright.sync_api import Browser, Page, Route

setup_test_config()

pytestmark = pytest.mark.e2e

APP = "http://app.test"
OTHER = "http://other.test"
NONCE = "pagenonce123"

# With `'strict-dynamic'`, the scripts that the manager adds run with no further check.
STRICT_DYNAMIC = f"script-src 'nonce-{NONCE}' 'strict-dynamic'"
PLAIN_NONCE = f"script-src 'nonce-{NONCE}'"

BASE_TAG = f'<base href="{OTHER}/">'
REFUSED_MESSAGE = "[DjangoComponents] Ignored a <script data-djc> block"
RUNTIME_PATH = "/static/django_components/django_components.min.js"
RUNTIME_FILE = Path(django_components.__file__).parent / "static/django_components/django_components.min.js"


# Another test file may have set `ROOT_URLCONF` first, and these tests need the cache URLs.
DJANGO_SETTINGS = {"STATIC_URL": "/static/", "ROOT_URLCONF": "django_components.urls"}


class NonceExtension(ComponentExtension):
    """Adds a nonce the way an app does, through the hook. The JSON block needs none for CSP."""

    name = "test_nonce"
    nonce: ClassVar[str | None] = NONCE

    def on_dependencies(self, ctx: OnDependenciesContext):
        if NonceExtension.nonce is not None:
            for script in ctx.scripts:
                if "data-djc" not in script.attrs:
                    script.attrs["nonce"] = NonceExtension.nonce
        return ctx.scripts, ctx.styles


@pytest.fixture(scope="module", params=BROWSER_NAMES, ids=BROWSER_NAMES)
def sync_browser(request: "FixtureRequest") -> Iterator["Browser"]:
    with sync_playwright() as playwright:
        browser = getattr(playwright, request.param).launch()
        yield browser
        browser.close()


def register_widget() -> type[Component]:
    @register("widget")
    class Widget(Component):
        template: types.django_html = """
            <div class="widget">widget</div>
        """
        js: types.js = """
            $onComponent((data) => {
                window.widgetCalls = window.widgetCalls || [];
                window.widgetCalls.push(data);
            });
        """
        css: types.css = """
            .widget { color: red; }
        """

    return Widget


def register_lazy_widget() -> type[Component]:
    """A component that the document does not use, so the manager has to fetch its files for a fragment."""

    @register("lazy_widget")
    class LazyWidget(Component):
        template: types.django_html = """
            <div class="lazy-widget">lazy widget</div>
        """
        js: types.js = """
            $onComponent((data) => {
                window.widgetCalls = window.widgetCalls || [];
                window.widgetCalls.push(data);
            });
        """
        css: types.css = """
            .lazy-widget { color: red; }
        """

    return LazyWidget


def render_page(injected: str = "", tail: str = "", head: str = "", nonce: str | None = NONCE) -> str:
    NonceExtension.nonce = nonce
    template = Template(
        """
        <!doctype html>
        <html>
            <head><title>clean</title>{{ head|safe }}</head>
            <body>
                {{ injected|safe }}
                {% component "widget" / %}
                {% component_js_dependencies %}
                {{ tail|safe }}
            </body>
        </html>
        """,
    )
    return template.render(Context({"injected": injected, "head": head, "tail": tail}))


def render_fragment(component: type[Component], nonce: str | None = NONCE) -> str:
    NonceExtension.nonce = nonce
    return str(component.render(deps_strategy="fragment"))


def render_shell(*body: str) -> str:
    """A page with no component, so it has no runtime until a fragment's loader adds it."""
    return f"<!doctype html><html><head><title>clean</title></head><body>{''.join(body)}</body></html>"


def fetch_fragment_script(nonce: str | None = NONCE) -> str:
    """The script that inserts a fragment, as `fetch()` and `innerHTML` do. Others go the same way."""
    nonce_attr = f' nonce="{nonce}"' if nonce else ""
    return f"""
        <div id="slot"></div>
        <script{nonce_attr}>
            fetch("{APP}/fragment").then((res) => res.text()).then((html) => {{
                document.getElementById("slot").innerHTML = html;
                window.fragmentInserted = true;
            }});
        </script>
    """


def _b64(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    return base64.b64encode(text.encode()).decode()


def forged_block(**overrides: object) -> str:
    data = {
        "cssUrls__markAsLoaded": [],
        "jsUrls__markAsLoaded": [],
        "cssTags__toFetch": [],
        "jsTags__toFetch": [],
        "componentJsVars": [],
        "componentJsCalls": [],
        **overrides,
    }
    return f'<script type="application/json" data-djc>{json.dumps(data)}</script>'


def forged_script_block() -> str:
    tag = {"tag": "script", "attrs": {"src": f"{OTHER}/forged.js"}, "content": ""}
    return forged_block(jsTags__toFetch=[_b64(tag)])


def forged_call_block(widget: type[Component]) -> str:
    """Call the page's own component with data that the attacker chose."""
    class_id = widget.class_id
    return "<div data-djc-id-cforged></div>" + forged_block(
        componentJsVars=[[_b64(class_id), _b64("aaaaaa"), _b64('{"forged": true}')]],
        componentJsCalls=[[_b64(class_id), _b64("cforged"), _b64("aaaaaa")]],
    )


@dataclass
class Visit:
    page: "Page"
    other_site_requests: list[str]
    console: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    # Paths asked of the app from `files`, the extra files that a test serves
    file_requests: list[str] = field(default_factory=list)
    # Every path asked of the app
    app_requests: list[str] = field(default_factory=list)

    def title(self) -> str:
        return self.page.title()

    def outline(self) -> str:
        """A stylesheet from the other site sets this."""
        return self.page.evaluate("getComputedStyle(document.documentElement).outlineStyle")

    def widget_calls(self) -> list[dict]:
        return self.page.evaluate("window.widgetCalls || []")

    def wait_for_widget(self, count: int = 1) -> None:
        # `page.wait_for_function()` runs `eval()` in the page, and these pages forbid that.
        for _ in range(250):
            if len(self.widget_calls()) >= count:
                return
            self.page.wait_for_timeout(20)
        raise AssertionError(f"Expected {count} widget call(s), got {self.widget_calls()}: {self.console}")

    def wait_for_refusal(self) -> None:
        self.wait_for_console(REFUSED_MESSAGE)

    def wait_for_console(self, message: str) -> None:
        for _ in range(250):
            if any(message in text for text in self.console):
                return
            self.page.wait_for_timeout(20)
        raise AssertionError(f"No {message!r} in the console: {self.console}")

    def settle(self) -> None:
        """Give scripts that should NOT run the time they would need."""
        self.page.wait_for_timeout(300)


def visit(
    browser: "Browser",
    html: str,
    csp: str | None,
    fragment: str = "",
    files: dict[str, str] | None = None,
) -> Visit:
    """
    Open `html` at `http://app.test/` with the policy `csp`.

    `files` maps more paths on the app to the JS that they serve, such as a file that a visitor
    uploaded, or the app's own script that inserts a fragment.
    """
    context = browser.new_context()
    page = context.new_page()
    result = Visit(page=page, other_site_requests=[])
    page.on("console", lambda message: result.console.append(message.text))
    page.on("pageerror", lambda error: result.page_errors.append(str(error)))
    client = Client()

    def answer(route: "Route") -> None:
        url = route.request.url
        if url.startswith(OTHER):
            path = url.removeprefix(OTHER)
            result.other_site_requests.append(path)
            if path.startswith(f"/copy{RUNTIME_PATH}"):
                # The attacker's site can serve a copy of the runtime
                route.fulfill(
                    status=200,
                    content_type="text/javascript",
                    headers={"Access-Control-Allow-Origin": "*"},
                    body=RUNTIME_FILE.read_bytes(),
                )
                return
            route.fulfill(
                status=200,
                content_type="text/css" if path.endswith(".css") else "text/javascript",
                headers={"Access-Control-Allow-Origin": "*"},
                body="html { outline: 3px solid lime; }" if path.endswith(".css") else f"document.title = '{path}';",
            )
            return

        path = url.removeprefix(APP)
        result.app_requests.append(path)
        if files and path.split("?")[0] in files:
            result.file_requests.append(path)
            route.fulfill(status=200, content_type="text/javascript", body=files[path.split("?")[0]])
        elif path == "/":
            headers = {"Content-Security-Policy": csp} if csp else {}
            route.fulfill(status=200, content_type="text/html", headers=headers, body=html)
        elif path == "/fragment":
            route.fulfill(status=200, content_type="text/html", body=fragment)
        elif path.startswith("/static/django_components/"):
            route.fulfill(status=200, content_type="text/javascript", body=RUNTIME_FILE.read_bytes())
        elif path.startswith("/components/"):
            response = client.get(path)
            route.fulfill(status=response.status_code, content_type=response["Content-Type"], body=response.content)
        else:
            route.fulfill(status=404)

    page.route("**/*", answer)
    page.goto(f"{APP}/")
    return result


@djc_test(django_settings=DJANGO_SETTINGS, components_settings={"extensions": [NonceExtension]})
class TestInjectedBaseTag:
    def test_page_runs_without_injection(self, sync_browser):
        # The hash has to match the shipped file, or every page would break.
        register_widget()

        result = visit(sync_browser, render_page(), PLAIN_NONCE)

        result.wait_for_widget()
        assert result.title() == "clean"
        result.page.context.close()

    def test_runtime_from_other_site_does_not_run(self, sync_browser):
        register_widget()

        result = visit(sync_browser, render_page(BASE_TAG), PLAIN_NONCE)
        result.settle()

        # The browser did go to the other site, and then refused what it got.
        assert [path.split("?")[0] for path in result.other_site_requests] == [RUNTIME_PATH]
        assert result.title() == "clean"
        result.page.context.close()

    def test_loader_refuses_runtime_from_other_site(self, sync_browser):
        widget = register_widget()

        result = visit(sync_browser, render_shell(BASE_TAG, render_fragment(widget)), STRICT_DYNAMIC)
        result.settle()

        assert [path.split("?")[0] for path in result.other_site_requests] == [RUNTIME_PATH]
        assert result.title() == "clean"
        result.page.context.close()

    def test_fragment_files_load_without_injection(self, sync_browser):
        register_widget()
        widget = register_lazy_widget()
        page = render_page(tail=fetch_fragment_script())

        result = visit(sync_browser, page, STRICT_DYNAMIC, fragment=render_fragment(widget))

        # One call for the document's widget, and one for the fragment's, whose file has to pass the hash
        result.wait_for_widget(count=2)
        result.page.context.close()

    def test_fragment_files_from_other_site_do_not_run(self, sync_browser):
        # The tag comes after the runtime, so the runtime loads and then asks for the fragment's files.
        register_widget()
        widget = register_lazy_widget()
        page = render_page(tail=BASE_TAG + fetch_fragment_script())
        component_url = f"/components/cache/{widget.class_id}"

        result = visit(sync_browser, page, STRICT_DYNAMIC, fragment=render_fragment(widget))
        result.wait_for_widget()
        result.settle()

        assert sorted(result.other_site_requests) == [f"{component_url}.css", f"{component_url}.js"]
        assert result.title() == "clean"
        assert result.outline() == "none"
        # The fragment's call never runs, because its file did not
        assert len(result.widget_calls()) == 1
        result.page.context.close()


@djc_test(django_settings=DJANGO_SETTINGS, components_settings={"extensions": [NonceExtension]})
class TestForgedDataBlock:
    @pytest.mark.parametrize("position", ["before_runtime", "after_runtime"])
    def test_forged_block_loads_nothing(self, sync_browser, position: str):
        register_widget()
        forged = forged_script_block()
        page = render_page(forged) if position == "before_runtime" else render_page(tail=forged)

        result = visit(sync_browser, page, STRICT_DYNAMIC)
        result.wait_for_refusal()
        result.wait_for_widget()
        result.settle()

        assert result.other_site_requests == []
        assert result.title() == "clean"
        result.page.context.close()

    def test_forged_call_does_not_run(self, sync_browser):
        # This needs no 'strict-dynamic': the code that runs is the page's own.
        widget = register_widget()

        result = visit(sync_browser, render_page(forged_call_block(widget)), PLAIN_NONCE)
        result.wait_for_refusal()
        result.wait_for_widget()
        result.settle()

        assert result.widget_calls() == [{}]
        result.page.context.close()

    def test_forged_stylesheet_does_not_load(self, sync_browser):
        register_widget()
        tag = {"tag": "link", "attrs": {"rel": "stylesheet", "href": f"{OTHER}/forged.css"}, "content": ""}
        page = render_page(forged_block(cssTags__toFetch=[_b64(tag)]))

        result = visit(sync_browser, page, PLAIN_NONCE)
        result.wait_for_refusal()
        result.settle()

        assert result.other_site_requests == []
        result.page.context.close()

    def test_named_element_does_not_hide_the_nonce(self, sync_browser):
        # `<form name="currentScript">` replaces `document.currentScript`, and it has no nonce
        register_widget()
        page = render_page('<form name="currentScript"></form>' + forged_script_block())

        result = visit(sync_browser, page, STRICT_DYNAMIC)
        result.wait_for_refusal()
        result.settle()

        assert result.other_site_requests == []
        assert result.title() == "clean"
        result.page.context.close()

    @pytest.mark.parametrize(
        "left_open",
        [
            '<script type="application/json" data-djc ',
            # The browser drops a duplicate attribute, so no `<` is left in the tag to give it away
            '<script type="application/json" data-djc type=',
            '<script type="application/json" data-djc data-x=1 data-x="',
        ],
        ids=["plain", "duplicate", "duplicate_quoted"],
    )
    def test_tag_left_open_does_not_take_the_nonce(self, sync_browser, left_open: str):
        # A page's own JSON tag comes after the injected text, with text that the attacker chose.
        # The nonce on that tag lands on the injected tag.
        register_widget()
        tag = {"tag": "script", "attrs": {"src": f"{OTHER}/forged.js"}, "content": ""}
        data = forged_block(jsTags__toFetch=[_b64(tag)]).removeprefix('<script type="application/json" data-djc>')
        page = render_page(tail=f'{left_open}<script nonce="{NONCE}" type="application/json">{data}')

        result = visit(sync_browser, page, STRICT_DYNAMIC)
        result.wait_for_refusal()
        result.settle()

        assert result.other_site_requests == []
        result.page.context.close()

    def test_unreadable_block_does_not_stop_the_runtime(self, sync_browser):
        register_widget()
        page = render_page('<script type="application/json" data-djc>not json</script>', nonce=None)

        result = visit(sync_browser, page, None)

        result.wait_for_widget()
        # An error tracker listens for uncaught errors, so the error must still be one
        result.page.wait_for_timeout(50)
        assert result.page_errors
        result.page.context.close()

    def test_runtime_from_the_loader_checks_blocks(self, sync_browser):
        # The loader has to hand its nonce to the runtime's tag, or the runtime has nothing to compare.
        widget = register_widget()
        page = render_shell(render_fragment(widget), forged_script_block())

        result = visit(sync_browser, page, STRICT_DYNAMIC)
        result.wait_for_refusal()
        result.wait_for_widget()
        result.settle()

        assert result.other_site_requests == []
        result.page.context.close()

    def test_loader_passes_the_nonce_past_a_named_element(self, sync_browser):
        widget = register_widget()
        page = render_shell('<form name="currentScript"></form>', render_fragment(widget), forged_script_block())

        result = visit(sync_browser, page, STRICT_DYNAMIC)
        result.wait_for_refusal()
        result.settle()

        assert result.other_site_requests == []
        result.page.context.close()

    def test_named_element_does_not_stop_the_loader(self, sync_browser):
        # `<div id="DjangoComponents">` makes `globalThis.DjangoComponents` truthy
        widget = register_widget()
        page = render_shell('<div id="DjangoComponents"></div>', render_fragment(widget))

        result = visit(sync_browser, page, STRICT_DYNAMIC)

        result.wait_for_widget()
        result.page.context.close()


@djc_test(django_settings=DJANGO_SETTINGS, components_settings={"extensions": [NonceExtension]})
class TestGenuineFragments:
    def test_fragment_with_the_page_nonce_starts(self, sync_browser):
        register_widget()
        widget = register_lazy_widget()
        page = render_page(tail=fetch_fragment_script())

        result = visit(sync_browser, page, STRICT_DYNAMIC, fragment=render_fragment(widget))

        result.wait_for_widget(count=2)
        result.page.context.close()

    def test_fragment_with_another_nonce_is_refused(self, sync_browser):
        register_widget()
        widget = register_lazy_widget()
        page = render_page(tail=fetch_fragment_script())
        fragment = render_fragment(widget, nonce="anothernonce")

        result = visit(sync_browser, page, STRICT_DYNAMIC, fragment=fragment)
        result.wait_for_refusal()
        result.settle()

        assert len(result.widget_calls()) == 1
        result.page.context.close()

    def test_fragment_starts_on_a_page_without_a_nonce(self, sync_browser):
        # With no nonce on the runtime there is nothing to compare, so apps without CSP see no change.
        register_widget()
        widget = register_lazy_widget()
        page = render_page(tail=fetch_fragment_script(nonce=None), nonce=None)

        result = visit(sync_browser, page, None, fragment=render_fragment(widget, nonce=None))

        result.wait_for_widget(count=2)
        result.page.context.close()


SKIPPED_MESSAGE = "[DjangoComponents] Did not load the script"
# A file that a visitor uploaded, or any other file on the app's origin that the app did not
# mean to run. The runtime's own folder and `/components/cache/` are where the app's files are.
UPLOADED = "/uploads/evil.js"
UPLOADED_JS = "document.title = 'uploaded';"
# The app's own script that inserts a fragment, for a policy that refuses inline scripts.
APP_SCRIPT = f"""
    fetch("{APP}/fragment").then((res) => res.text()).then((html) => {{
        document.getElementById("slot").innerHTML = html;
    }});
"""
APP_SCRIPT_TAG = '<div id="slot"></div><script src="/app.js"></script>'
MEDIA_JS = "window.mediaLoaded = (window.mediaLoaded || 0) + 1;"


def hash_policy(html: str, *sources: str) -> str:
    """
    A policy that allows the page's scripts by their hashes, as an app without nonces writes it.

    It lists the runtime's `integrity` and the hash of each inline script, so the page runs as
    the app meant, and nothing else does.
    """
    hashes = re.findall(r'<script[^>]*src="[^"]*django_components\.min\.js[^"]*"[^>]*integrity="([^"]+)"', html)
    for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", html, re.DOTALL):
        if "src=" in attrs or "application/json" in attrs:
            continue
        hashes.append("sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode())
    return "script-src " + " ".join([*(f"'{value}'" for value in hashes), *sources])


def register_media_widget(*media_js: str) -> type[Component]:
    """A component for a fragment, whose `Media.js` names `media_js`."""

    @register("media_widget")
    class MediaWidget(Component):
        template: types.django_html = """
            <div class="media-widget">media widget</div>
        """
        js: types.js = """
            $onComponent((data) => {
                window.widgetCalls = window.widgetCalls || [];
                window.widgetCalls.push({ media: window.mediaLoaded || 0 });
            });
        """

        class Media:
            js = media_js

    return MediaWidget


def forged_src_block(*srcs: str, attrs: dict[str, str] | None = None) -> str:
    tags = [{"tag": "script", "attrs": {"src": src, **(attrs or {})}, "content": ""} for src in srcs]
    return forged_block(jsTags__toFetch=[_b64(tag) for tag in tags])


@djc_test(django_settings=DJANGO_SETTINGS, components_settings={"extensions": [NonceExtension]})
class TestPageWithoutNonce:
    """
    When the runtime's tag has no nonce, injected markup can write a block that the runtime obeys.

    Such a block may load only the app's own files: `/components/cache/` and `STATIC_URL`.
    """

    def test_forged_block_loads_no_script_from_another_site(self, sync_browser):
        # With hashes and 'strict-dynamic', the scripts that the runtime adds run from any site
        register_widget()
        page = render_page(forged_script_block(), nonce=None)

        result = visit(sync_browser, page, hash_policy(page, "'strict-dynamic'"))
        result.wait_for_widget()
        result.settle()

        assert result.other_site_requests == []
        assert result.title() == "clean"
        assert any(SKIPPED_MESSAGE in text for text in result.console)
        result.page.context.close()

    def test_inserted_block_loads_no_other_file_from_the_app(self, sync_browser):
        # Markup that page code inserts cannot run its own `<script>`, but the runtime would
        register_widget()
        page = render_page(tail=APP_SCRIPT_TAG, nonce=None)
        files = {"/app.js": APP_SCRIPT, UPLOADED: UPLOADED_JS}

        csp = hash_policy(page, "'self'")

        result = visit(sync_browser, page, csp, fragment=forged_src_block(UPLOADED), files=files)
        result.wait_for_widget()
        result.wait_for_console(SKIPPED_MESSAGE)
        result.settle()

        assert result.file_requests == ["/app.js"]
        assert result.title() == "clean"
        result.page.context.close()

    @pytest.mark.parametrize(
        "src",
        [
            "/static/../uploads/evil.js",
            "/static/%2e%2e/uploads/evil.js",
            "/static/..%2fuploads/evil.js",
            "/static/..%5Cuploads/evil.js",
            "//other.test/static/evil.js",
            f"{OTHER}/components/cache/evil.js",
            f"{OTHER}/static/evil.js",
            "http://user:pass@app.test/static/evil.js",
            "/components/cache/evil.js/../../uploads/evil.js",
            "data:text/javascript,document.title='data'",
        ],
    )
    def test_forged_block_cannot_leave_the_app_files(self, sync_browser, src: str):
        register_widget()
        page = render_page(forged_src_block(src), nonce=None)

        result = visit(sync_browser, page, hash_policy(page, "'strict-dynamic'"), files={UPLOADED: UPLOADED_JS})
        result.wait_for_widget()
        result.settle()

        assert result.other_site_requests == []
        assert not [path for path in result.app_requests if "evil" in path]
        assert result.title() == "clean"
        result.page.context.close()

    def test_forged_block_cannot_name_src_twice(self, sync_browser):
        # The tag keeps the last `src` it gets, whatever its case. The runtime also sets `src` to
        # the URL it checked, so this holds even if the check read the first one.
        register_widget()
        page = render_page(forged_src_block("/static/ok.js", attrs={"SRC": f"{OTHER}/forged.js"}), nonce=None)

        result = visit(sync_browser, page, hash_policy(page, "'strict-dynamic'"))
        result.wait_for_widget()
        result.settle()

        assert result.other_site_requests == []
        assert result.title() == "clean"
        result.page.context.close()

    def test_runtime_copy_from_another_site_loads_nothing_from_there(self, sync_browser):
        # A policy with the runtime's hash runs a copy of it from any site, and the copy reads
        # its own address. So an address on another site with `integrity` gives no folder.
        register_widget()
        integrity = re.search(r'integrity="([^"]+)"', render_page(nonce=None))
        assert integrity is not None
        copy_url = f"{OTHER}/copy{RUNTIME_PATH}"
        copy = f'<script src="{copy_url}" integrity="{integrity.group(1)}" crossorigin="anonymous"></script>'
        page = render_page(copy + forged_src_block(f"{OTHER}/copy/static/forged.js", UPLOADED), nonce=None)

        result = visit(sync_browser, page, hash_policy(page, "'strict-dynamic'"), files={UPLOADED: UPLOADED_JS})
        result.wait_for_widget()
        result.settle()

        assert result.other_site_requests == [f"/copy{RUNTIME_PATH}"]
        assert result.file_requests == []
        assert result.title() == "clean"
        result.page.context.close()

    @pytest.mark.parametrize(
        "copy_path",
        [
            # A visitor uploaded a copy of the runtime next to the payload
            "/uploads/django_components.min.js",
            # A server that decodes `%2F` and then follows `..` serves the real file from here
            "/uploads/django_components/..%2f..%2fstatic%2fdjango_components%2fdjango_components.min.js",
        ],
        ids=["uploaded", "encoded_slash"],
    )
    def test_runtime_copy_on_the_app_gives_no_folder_of_its_own(self, sync_browser, copy_path: str):
        # A policy with the runtime's hash runs such a copy, and the copy reads its own address
        register_widget()
        integrity = re.search(r'integrity="([^"]+)"', render_page(nonce=None))
        assert integrity is not None
        copy = f'<script src="{copy_path}" integrity="{integrity.group(1)}" crossorigin="anonymous"></script>'
        page = render_page(copy + forged_src_block(UPLOADED), nonce=None)
        files = {copy_path: RUNTIME_FILE.read_text(), UPLOADED: UPLOADED_JS}

        result = visit(sync_browser, page, hash_policy(page, "'strict-dynamic'"), files=files)
        result.wait_for_widget()
        result.settle()

        # The copy ran, so it asked for nothing, and the page's own runtime refused the block too
        assert [path.split("?")[0] for path in result.file_requests] == [copy_path]
        assert result.title() == "clean"
        result.page.context.close()

    @djc_test(django_settings={**DJANGO_SETTINGS, "STATIC_URL": "/"})
    def test_static_url_at_the_root_is_not_a_folder(self, sync_browser):
        # The root of the site would let through every path on it, such as uploaded files
        register_widget()
        widget = register_media_widget("media.js")
        page = render_page(tail=fetch_fragment_script(nonce=None), nonce=None)
        files = {"/django_components/django_components.min.js": RUNTIME_FILE.read_text(), "/media.js": MEDIA_JS}

        result = visit(sync_browser, page, None, fragment=render_fragment(widget, nonce=None), files=files)
        result.wait_for_widget(count=2)
        result.settle()

        assert "/media.js" not in result.file_requests
        assert result.widget_calls()[1] == {"media": 0}
        result.page.context.close()

    def test_forged_js_variables_do_not_reach_a_component(self, sync_browser):
        # The server never puts JS variables in a block, so on this page such a block is forged
        widget = register_widget()
        page = render_page(forged_call_block(widget), nonce=None)

        result = visit(sync_browser, page, hash_policy(page, "'strict-dynamic'"))
        result.wait_for_widget()
        result.settle()

        assert result.widget_calls() == [{}]
        result.page.context.close()

    @pytest.mark.parametrize("policy", ["none", "hashes"])
    def test_fragment_loads_its_files_from_static_and_cache(self, sync_browser, policy: str):
        register_widget()
        widget = register_media_widget("media.js")
        page = render_page(tail=fetch_fragment_script(nonce=None), nonce=None)
        csp = hash_policy(page, "'strict-dynamic'") if policy == "hashes" else None

        result = visit(
            sync_browser,
            page,
            csp,
            fragment=render_fragment(widget, nonce=None),
            files={"/static/media.js": MEDIA_JS},
        )
        result.wait_for_widget(count=2)

        assert result.widget_calls()[1] == {"media": 1}
        assert result.file_requests == ["/static/media.js"]
        result.page.context.close()

    def test_fragment_skips_a_script_from_another_site(self, sync_browser):
        # This is the one change for apps without a policy. The fragment's components still run.
        register_widget()
        widget = register_media_widget(f"{OTHER}/lib.js")
        page = render_page(tail=fetch_fragment_script(nonce=None), nonce=None)

        result = visit(sync_browser, page, None, fragment=render_fragment(widget, nonce=None))
        result.wait_for_widget(count=2)
        result.settle()

        assert result.other_site_requests == []
        assert any(SKIPPED_MESSAGE in text and f"{OTHER}/lib.js" in text for text in result.console)
        result.page.context.close()

    def test_script_from_another_site_already_on_the_page_is_not_needed(self, sync_browser):
        # The documented way to keep a CDN script: a component on the page lists it, so the
        # runtime knows that the page has it, and the fragment does not ask for it again.
        register_widget()
        widget = register_media_widget(f"{OTHER}/lib.js")
        template = Template(
            """
            <!doctype html>
            <html>
                <head><title>clean</title></head>
                <body>
                    {% component "media_widget" / %}
                    {% component_js_dependencies %}
                    {{ tail|safe }}
                </body>
            </html>
            """,
        )
        NonceExtension.nonce = None
        page = template.render(Context({"tail": fetch_fragment_script(nonce=None)}))

        result = visit(sync_browser, page, None, fragment=render_fragment(widget, nonce=None))
        result.wait_for_widget(count=2)
        result.settle()

        assert result.other_site_requests == ["/lib.js"]
        assert not any(SKIPPED_MESSAGE in text for text in result.console)
        result.page.context.close()

    def test_base_tag_does_not_move_checked_files(self, sync_browser):
        # The runtime loads the full URL it checked, so a `<base>` tag added later changes nothing
        register_widget()
        widget = register_lazy_widget()
        page = render_page(tail=BASE_TAG + fetch_fragment_script(nonce=None), nonce=None)

        result = visit(sync_browser, page, None, fragment=render_fragment(widget, nonce=None))
        result.wait_for_widget(count=2)

        assert not [path for path in result.other_site_requests if path.endswith(".js")]
        result.page.context.close()
