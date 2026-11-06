"""
Injected page markup must not change how the client-side manager loads.

These tests render real pages in Python and show them to a real browser. Playwright answers every
request, so they use no port: `http://app.test` is the app, and `http://other.test` stands for
the attacker's site. A file from that site changes `document.title`, which is harmless and easy to see.

The tests use Playwright's sync API because `djc_test` applies its settings and its cleanup around
the call to the test function, and an async test function does its work after that call returns.
"""

import base64
import json
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
        for _ in range(250):
            if any(REFUSED_MESSAGE in text for text in self.console):
                return
            self.page.wait_for_timeout(20)
        raise AssertionError(f"No refusal in the console: {self.console}")

    def settle(self) -> None:
        """Give scripts that should NOT run the time they would need."""
        self.page.wait_for_timeout(300)


def visit(browser: "Browser", html: str, csp: str | None, fragment: str = "") -> Visit:
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
            route.fulfill(
                status=200,
                content_type="text/css" if path.endswith(".css") else "text/javascript",
                headers={"Access-Control-Allow-Origin": "*"},
                body="html { outline: 3px solid lime; }" if path.endswith(".css") else f"document.title = '{path}';",
            )
            return

        path = url.removeprefix(APP)
        if path == "/":
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
