"""
End-to-end tests for CSS variables feature.

These tests verify that CSS variables from `get_css_data()` work correctly
in a real browser environment.
"""

import re
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.template import Context, Template

from django_components import Component, register, types
from django_components.testing import djc_test
from tests.e2e.utils import TEST_SERVER_URL, with_playwright
from tests.testutils import setup_test_config

if TYPE_CHECKING:
    from playwright.async_api import Browser

    from tests.e2e.utils import BrowserType

setup_test_config()


def server():
    """
    Define server-side components and views for CSS vars E2E tests.

    This function is automatically discovered and called by the testserver
    to register URL patterns, views, and components.
    """

    @register("css_no_vars_component")
    class CssNoVarsComponent(Component):
        """Component with static CSS only (no get_css_data)."""

        template: types.django_html = """
            <div id="css-no-vars-container" class="css-static-box">
                <div class="css-static-label">No CSS vars</div>
            </div>
        """

        css: types.css = """
            .css-static-box {
                padding: 20px;
                border: 2px solid #6c757d;
                margin: 10px;
                background-color: #e9ecef;
                width: 100px;
                height: 100px;
            }
            .css-static-label {
                color: #495057;
                font-weight: bold;
            }
        """

    @register("css_vars_themed_box")
    class CssVarsThemedBox(Component):
        template: types.django_html = """
            <div class="themed-box">Box</div>
        """

        css: types.css = """
            .themed-box {
                background-color: var(--bg_color);
                width: 100px;
                height: 100px;
            }
        """

        def get_css_data(self, args, kwargs, slots, context):
            return {
                "bg_color": kwargs.get("color", "blue"),
            }

    @register("css_vars_sized_box")
    class CssVarsSizedBox(Component):
        template: types.django_html = """
            <div class="sized-box">Box</div>
        """

        css: types.css = """
            .sized-box {
                width: var(--box_width);
                height: var(--box_height);
                background-color: var(--bg_color);
            }
        """

        def get_css_data(self, args, kwargs, slots, context):
            return {
                "box_width": kwargs.get("width", "100px"),
                "box_height": kwargs.get("height", "100px"),
                "bg_color": kwargs.get("color", "red"),
            }

    @register("css_fragment_no_vars")
    class CssFragmentNoVars(Component):
        """Fragment component with static CSS only."""

        template: types.django_html = """
            <div id="css-fragment-no-vars" class="css-fragment-container">
                <div class="css-fragment-content">Fragment without CSS variables</div>
            </div>
        """

        css: types.css = """
            .css-fragment-container {
                padding: 20px;
                border: 2px solid #007bff;
                margin: 10px;
                background-color: #e7f1ff;
            }
            .css-fragment-content {
                font-weight: bold;
                color: #007bff;
            }
        """

    @register("css_fragment_with_vars")
    class CssFragmentWithVars(Component):
        """Fragment component with get_css_data (CSS variables)."""

        template: types.django_html = """
            <div id="css-fragment-with-vars" class="css-fragment-themed">
                <div class="css-fragment-themed-label">Fragment with CSS variables</div>
            </div>
        """

        css: types.css = """
            .css-fragment-themed {
                padding: 20px;
                border: 2px solid var(--border_color);
                margin: 10px;
                background-color: var(--bg_color);
            }
            .css-fragment-themed-label {
                font-weight: bold;
                color: var(--text_color);
            }
        """

        def get_css_data(self, args, kwargs, slots, context):
            return {
                "border_color": kwargs.get("border_color", "#28a745"),
                "bg_color": kwargs.get("bg_color", "#d4edda"),
                "text_color": kwargs.get("text_color", "#155724"),
            }

    @register("css_fragment_base")
    class CssFragmentBase(Component):
        """Base HTML page with button to load a CSS fragment (no-vars or with-vars)."""

        template: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    <div id="target">Initial content</div>
                    <button id="load-fragment-btn" data-fragment-type="">Load Fragment</button>
                    {% component_js_dependencies %}
                </body>
            </html>
        """

        js: types.js = """
            $onComponent((data, ctx) => {
                const btn = document.querySelector('#load-fragment-btn');
                if (btn) {
                    btn.addEventListener('click', function() {
                        const fragmentType = this.getAttribute('data-fragment-type') || 'no-vars';
                        fetch(`/css-vars/fragment/fragment?type=${fragmentType}`)
                            .then(response => response.text())
                            .then(html => {
                                const target = document.querySelector('#target');
                                const parser = new DOMParser();
                                const doc = parser.parseFromString(html, 'text/html');
                                target.innerHTML = doc.body.innerHTML;
                            });
                    });
                }
            });
        """

    def css_document_no_vars_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'css_no_vars_component' / %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def css_document_vars_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    <div id="box-red">
                        {% component 'css_vars_themed_box' color='red' / %}
                    </div>
                    <div id="box-green">
                        {% component 'css_vars_themed_box' color='green' / %}
                    </div>
                    <div id="box-blue">
                        {% component 'css_vars_themed_box' color='blue' / %}
                    </div>
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def css_document_sized_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    <div id="sized-box">
                        {% component 'css_vars_sized_box' width='200px' height='150px' color='#0275d8' / %}
                    </div>
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def css_fragment_base_view(_request):
        return CssFragmentBase.render_to_response()

    def css_fragment_view(request):
        fragment_type = request.GET.get("type", "")
        if fragment_type == "no-vars":
            return CssFragmentNoVars.render_to_response(deps_strategy="fragment")
        elif fragment_type == "with-vars":
            return CssFragmentWithVars.render_to_response(
                kwargs={
                    "border_color": "#28a745",
                    "bg_color": "#d4edda",
                    "text_color": "#155724",
                },
                deps_strategy="fragment",
            )
        else:
            return HttpResponse("Invalid fragment type", status=400)  # type: ignore[arg-type]

    return {
        "/css-vars/document/no-vars": css_document_no_vars_view,
        "/css-vars/document/vars": css_document_vars_view,
        "/css-vars/document/sized": css_document_sized_view,
        "/css-vars/fragment/base": css_fragment_base_view,
        "/css-vars/fragment/fragment": css_fragment_view,
    }


@djc_test
class TestE2eCssVariables:
    @with_playwright
    async def test_document_no_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        """Full document: component without CSS variables (static CSS only)."""
        url = TEST_SERVER_URL + "/css-vars/document/no-vars"

        page = await browser.new_page()
        await page.goto(url)

        test_js: types.js = """() => {
            const box = document.querySelector('#css-no-vars-container.css-static-box');
            if (!box) return { bg: null, width: null, hash: null };
            const style = globalThis.getComputedStyle(box);
            let hash = null;
            for (let i = 0; i < box.attributes.length; i++) {
                const attr = box.attributes[i];
                if (attr.name.startsWith('data-djc-css-')) {
                    hash = attr.name.replace('data-djc-css-', '');
                    break;
                }
            }
            return {
                bg: style.getPropertyValue('background-color'),
                width: style.getPropertyValue('width'),
                hash,
            };
        }"""

        data = await page.evaluate(test_js)

        # Static styles from component CSS
        assert "rgb(233, 236, 239)" in data["bg"] or "#e9ecef" in data["bg"].lower()
        assert data["width"] == "100px"
        # No CSS variables => may have no hash or a shared/default hash
        await page.close()

    @with_playwright
    async def test_document_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        """Full document: multiple instances with different CSS variable values."""
        url = TEST_SERVER_URL + "/css-vars/document/vars"

        page = await browser.new_page()
        await page.goto(url)

        test_js: types.js = """() => {
            const boxRed = document.querySelector('#box-red .themed-box');
            const boxGreen = document.querySelector('#box-green .themed-box');
            const boxBlue = document.querySelector('#box-blue .themed-box');

            const redBg = boxRed ? globalThis.getComputedStyle(boxRed).getPropertyValue('background-color') : null;
            const greenBg = boxGreen ? globalThis.getComputedStyle(boxGreen).getPropertyValue('background-color') : null;
            const blueBg = boxBlue ? globalThis.getComputedStyle(boxBlue).getPropertyValue('background-color') : null;

            // Extract CSS variable hash from data-djc-css-{hash} attribute
            // The attribute format is data-djc-css-{hash}, so we need to find the attribute
            const getCssHash = (el) => {
                if (!el) return null;
                for (let i = 0; i < el.attributes.length; i++) {
                    const attr = el.attributes[i];
                    if (attr.name.startsWith('data-djc-css-')) {
                        return attr.name.replace('data-djc-css-', '');
                    }
                }
                return null;
            };

            return {
                redBg,
                greenBg,
                blueBg,
                redHash: getCssHash(boxRed),
                greenHash: getCssHash(boxGreen),
                blueHash: getCssHash(boxBlue),
            };
        }"""  # noqa: E501

        data = await page.evaluate(test_js)

        # Verify that each box has the correct background color
        # CSS colors are returned as RGB values
        assert "rgb(255, 0, 0)" in data["redBg"] or "red" in data["redBg"].lower()
        assert "rgb(0, 128, 0)" in data["greenBg"] or "green" in data["greenBg"].lower()
        assert "rgb(0, 0, 255)" in data["blueBg"] or "blue" in data["blueBg"].lower()

        # Verify that each instance has a different CSS variable hash
        # (since they have different variable values)
        assert data["redHash"] is not None
        assert data["greenHash"] is not None
        assert data["blueHash"] is not None
        assert data["redHash"] != data["greenHash"]
        assert data["greenHash"] != data["blueHash"]
        assert data["redHash"] != data["blueHash"]

        await page.close()

    @with_playwright
    async def test_document_sized(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        """Full document: single component with CSS variables (width, height, color)."""
        url = TEST_SERVER_URL + "/css-vars/document/sized"

        page = await browser.new_page()
        await page.goto(url)

        test_js: types.js = """() => {
            const box = document.querySelector('#sized-box .sized-box');
            if (!box) {
                return { width: null, height: null, bgColor: null, cssHash: null };
            }
            const style = globalThis.getComputedStyle(box);
            let cssHash = null;
            for (let i = 0; i < box.attributes.length; i++) {
                const attr = box.attributes[i];
                if (attr.name.startsWith('data-djc-css-')) {
                    cssHash = attr.name.replace('data-djc-css-', '');
                    break;
                }
            }
            return {
                width: style.getPropertyValue('width'),
                height: style.getPropertyValue('height'),
                bgColor: style.getPropertyValue('background-color'),
                cssHash,
            };
        }"""

        data = await page.evaluate(test_js)

        # Verify dimensions are set correctly via CSS variables
        assert data["width"] == "200px"
        assert data["height"] == "150px"
        assert "rgb(2, 117, 216)" in data["bgColor"] or "#0275d8" in data["bgColor"].lower()
        assert data["cssHash"] is not None
        assert re.match(r"^[a-f0-9]{6}$", data["cssHash"]) is not None

        await page.close()

    @with_playwright
    async def test_fragment_no_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        """Fragment: component without CSS variables loaded into existing page."""
        url = TEST_SERVER_URL + "/css-vars/fragment/base"

        page = await browser.new_page()
        await page.goto(url)

        await page.wait_for_timeout(500)

        await page.evaluate("""() => {
            const btn = document.querySelector('#load-fragment-btn');
            btn.setAttribute('data-fragment-type', 'no-vars');
        }""")
        await page.click("#load-fragment-btn")
        await page.wait_for_timeout(500)

        test_js: types.js = """() => {
            const fragment = document.querySelector('#css-fragment-no-vars');
            const content = document.querySelector('.css-fragment-content');
            const style = fragment ? globalThis.getComputedStyle(fragment) : null;
            const bg = style ? style.getPropertyValue('background-color') : null;
            const border = style ? style.borderColor : null;
            return {
                fragmentExists: fragment !== null,
                contentText: content ? content.textContent : null,
                bg,
                hasBorder: border && border !== 'rgba(0, 0, 0, 0)',
            };
        }"""

        data = await page.evaluate(test_js)

        assert data["fragmentExists"] is True
        assert data["contentText"] == "Fragment without CSS variables"
        assert "rgb(231, 241, 255)" in data["bg"] or "#e7f1ff" in data["bg"].lower()
        assert data["hasBorder"] is True

        await page.close()

    @with_playwright
    async def test_fragment_with_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        """Fragment: component with CSS variables loaded into existing page."""
        url = TEST_SERVER_URL + "/css-vars/fragment/base"

        page = await browser.new_page()
        await page.goto(url)

        await page.wait_for_timeout(500)

        await page.evaluate("""() => {
            const btn = document.querySelector('#load-fragment-btn');
            btn.setAttribute('data-fragment-type', 'with-vars');
        }""")
        await page.click("#load-fragment-btn")
        await page.wait_for_timeout(500)

        test_js: types.js = """() => {
            const fragment = document.querySelector('#css-fragment-with-vars');
            const content = document.querySelector('.css-fragment-themed-label');
            const style = fragment ? globalThis.getComputedStyle(fragment) : null;
            const bg = style ? style.getPropertyValue('background-color') : null;
            const border = style ? style.borderColor : null;
            let cssHash = null;
            if (fragment) {
                for (let i = 0; i < fragment.attributes.length; i++) {
                    const attr = fragment.attributes[i];
                    if (attr.name.startsWith('data-djc-css-')) {
                        cssHash = attr.name.replace('data-djc-css-', '');
                        break;
                    }
                }
            }
            return {
                fragmentExists: fragment !== null,
                contentText: content ? content.textContent : null,
                bg,
                border,
                cssHash,
                hasBorder: border && border !== 'rgba(0, 0, 0, 0)',
            };
        }"""

        data = await page.evaluate(test_js)

        assert data["fragmentExists"] is True
        assert data["contentText"] == "Fragment with CSS variables"
        # #d4edda -> rgb(212, 237, 218)
        assert "rgb(212, 237, 218)" in data["bg"] or "#d4edda" in data["bg"].lower()
        assert data["hasBorder"] is True
        assert data["cssHash"] is not None

        await page.close()
