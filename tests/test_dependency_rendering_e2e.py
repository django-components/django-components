"""
Here we check that all parts of managing JS and CSS dependencies work together
in an actual browser.
"""

import re

from playwright.async_api import Page
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import types
from django_components.testing import djc_test
from tests.testutils import setup_test_config
from tests.e2e.utils import TEST_SERVER_URL, with_playwright

setup_test_config({"autodiscover": False})


# NOTE: All views, components,  and associated JS and CSS are defined in
# `tests/e2e/testserver/testserver`
@djc_test
class TestE2eDependencyRendering:
    @with_playwright
    async def test_single_component_dependencies(self):
        single_comp_url = TEST_SERVER_URL + "/single"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            const bodyHTML = document.body.innerHTML;

            const innerEl = document.querySelector(".inner");
            const innerFontSize = globalThis.getComputedStyle(innerEl).getPropertyValue('font-size');

            const myStyleEl = document.querySelector(".my-style");
            const myStyleBg = globalThis.getComputedStyle(myStyleEl).getPropertyValue('background');

            return {
                bodyHTML,
                componentJsMsg: globalThis.testSimpleComponent,
                scriptJsMsg: globalThis.testMsg,
                innerFontSize,
                myStyleBg,
            };
        }"""

        data = await page.evaluate(test_js)

        # Check that the actual HTML content was loaded
        assert re.compile(
            r'Variable: <strong class="inner" data-djc-id-\w{7}="">foo</strong>'
        ).search(data["bodyHTML"]) is not None
        assertInHTML('<div class="my-style"> 123 </div>', data["bodyHTML"], count=1)
        assertInHTML('<div class="my-style2"> xyz </div>', data["bodyHTML"], count=1)

        # Check components' inlined JS got loaded
        assert data["componentJsMsg"] == "kapowww!"

        # Check JS from Media.js got loaded
        assert data["scriptJsMsg"] == {"hello": "world"}

        # Check components' inlined CSS got loaded
        assert data["innerFontSize"] == "4px"

        # Check CSS from Media.css got loaded
        assert "rgb(0, 0, 255)" in data["myStyleBg"]  # AKA 'background: blue'

        await page.close()

    @with_playwright
    async def test_multiple_component_dependencies(self):
        single_comp_url = TEST_SERVER_URL + "/multi"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            const bodyHTML = document.body.innerHTML;

            // Get the stylings defined via CSS
            const innerEl = document.querySelector(".inner");
            const innerFontSize = globalThis.getComputedStyle(innerEl).getPropertyValue('font-size');

            const outerEl = document.querySelector(".outer");
            const outerFontSize = globalThis.getComputedStyle(outerEl).getPropertyValue('font-size');

            const otherEl = document.querySelector(".other");
            const otherDisplay = globalThis.getComputedStyle(otherEl).getPropertyValue('display');

            const myStyleEl = document.querySelector(".my-style");
            const myStyleBg = globalThis.getComputedStyle(myStyleEl).getPropertyValue('background');

            const myStyle2El = document.querySelector(".my-style2");
            const myStyle2Color = globalThis.getComputedStyle(myStyle2El).getPropertyValue('color');

            return {
                bodyHTML,
                component1JsMsg: globalThis.testSimpleComponent,
                component2JsMsg: globalThis.testSimpleComponentNested,
                component3JsMsg: globalThis.testOtherComponent,
                scriptJs1Msg: globalThis.testMsg,
                scriptJs2Msg: globalThis.testMsg2,
                innerFontSize,
                outerFontSize,
                myStyleBg,
                myStyle2Color,
                otherDisplay,
            };
        }"""

        data = await page.evaluate(test_js)

        # Check that the actual HTML content was loaded
        assert re.compile(
            # <div class="outer" data-djc-id-c10uLMD>
            #     Variable:
            #     <strong class="inner" data-djc-id-cDZEnUC>
            #         variable
            #     </strong>
            #     XYZ:
            #     <strong class="other" data-djc-id-cIYirHK>
            #         variable_inner
            #     </strong>
            # </div>
            # <div class="my-style">123</div>
            # <div class="my-style2">xyz</div>
            r'<div class="outer" data-djc-id-\w{7}="">\s*'
            r"Variable:\s*"
            r'<strong class="inner" data-djc-id-\w{7}="">\s*'
            r"variable\s*"
            r"<\/strong>\s*"
            r"XYZ:\s*"
            r'<strong class="other" data-djc-id-\w{7}="">\s*'
            r"variable_inner\s*"
            r"<\/strong>\s*"
            r"<\/div>\s*"
            r'<div class="my-style">123<\/div>\s*'
            r'<div class="my-style2">xyz<\/div>\s*'
        ).search(data["bodyHTML"]) is not None

        # Check components' inlined JS got loaded
        assert data["component1JsMsg"] == "kapowww!"
        assert data["component2JsMsg"] == "bongo!"
        assert data["component3JsMsg"] == "wowzee!"

        # Check JS from Media.js got loaded
        assert data["scriptJs1Msg"] == {"hello": "world"}
        assert data["scriptJs2Msg"] == {"hello2": "world2"}

        # Check components' inlined CSS got loaded
        assert data["innerFontSize"] == "4px"
        assert data["outerFontSize"] == "40px"
        assert data["otherDisplay"] == "flex"

        # Check CSS from Media.css got loaded
        assert "rgb(0, 0, 255)" in data["myStyleBg"]  # AKA 'background: blue'
        assert data["myStyle2Color"] == "rgb(255, 0, 0)"  # AKA 'color: red'

        await page.close()

    @with_playwright
    async def test_renders_css_nojs_env(self):
        single_comp_url = TEST_SERVER_URL + "/multi"

        page: Page = await self.browser.new_page(java_script_enabled=False)  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            const bodyHTML = document.body.innerHTML;

            // Get the stylings defined via CSS
            const innerEl = document.querySelector(".inner");
            const innerFontSize = globalThis.getComputedStyle(innerEl).getPropertyValue('font-size');

            const outerEl = document.querySelector(".outer");
            const outerFontSize = globalThis.getComputedStyle(outerEl).getPropertyValue('font-size');

            const otherEl = document.querySelector(".other");
            const otherDisplay = globalThis.getComputedStyle(otherEl).getPropertyValue('display');

            const myStyleEl = document.querySelector(".my-style");
            const myStyleBg = globalThis.getComputedStyle(myStyleEl).getPropertyValue('background');

            const myStyle2El = document.querySelector(".my-style2");
            const myStyle2Color = globalThis.getComputedStyle(myStyle2El).getPropertyValue('color');

            return {
                bodyHTML,
                component1JsMsg: globalThis.testSimpleComponent,
                component2JsMsg: globalThis.testSimpleComponentNested,
                component3JsMsg: globalThis.testOtherComponent,
                scriptJs1Msg: globalThis.testMsg,
                scriptJs2Msg: globalThis.testMsg2,
                innerFontSize,
                outerFontSize,
                myStyleBg,
                myStyle2Color,
                otherDisplay,
            };
        }"""

        data = await page.evaluate(test_js)

        # Check that the actual HTML content was loaded
        #
        # <div class="outer" data-djc-id-c10uLMD>
        #     Variable:
        #     <strong class="inner" data-djc-id-cDZEnUC>
        #         variable
        #     </strong>
        #     XYZ:
        #     <strong data-djc-id-cIYirHK class="other">
        #         variable_inner
        #     </strong>
        # </div>
        # <div class="my-style">123</div>
        # <div class="my-style2">xyz</div>
        assert re.compile(
            r'<div class="outer" data-djc-id-\w{7}="">\s*'
            r"Variable:\s*"
            r'<strong class="inner" data-djc-id-\w{7}="">\s*'
            r"variable\s*"
            r"<\/strong>\s*"
            r"XYZ:\s*"
            r'<strong class="other" data-djc-id-\w{7}="">\s*'
            r"variable_inner\s*"
            r"<\/strong>\s*"
            r"<\/div>\s*"
            r'<div class="my-style">123<\/div>\s*'
            r'<div class="my-style2">xyz<\/div>\s*'
        ).search(data["bodyHTML"]) is not None

        # Check components' inlined JS did NOT get loaded
        assert data["component1JsMsg"] is None
        assert data["component2JsMsg"] is None
        assert data["component3JsMsg"] is None

        # Check JS from Media.js did NOT get loaded
        assert data["scriptJs1Msg"] is None
        assert data["scriptJs2Msg"] is None

        # Check components' inlined CSS got loaded
        assert data["innerFontSize"] == "4px"
        assert data["outerFontSize"] == "40px"
        assert data["otherDisplay"] == "flex"

        # Check CSS from Media.css got loaded
        assert "rgb(0, 0, 255)" in data["myStyleBg"]  # AKA 'background: blue'
        assert "rgb(255, 0, 0)" in data["myStyle2Color"]  # AKA 'color: red'

        await page.close()

    @with_playwright
    async def test_js_executed_in_order__js(self):
        single_comp_url = TEST_SERVER_URL + "/js-order/js"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // NOTE: This variable should be defined by `check_script_order` component,
            // and it should contain all other variables defined by the previous components
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        assert data["testSimpleComponent"] == "kapowww!"
        assert data["testSimpleComponentNested"] == "bongo!"
        assert data["testOtherComponent"] == "wowzee!"

        # Check JS from Media.js got loaded
        assert data["testMsg"] == {"hello": "world"}
        assert data["testMsg2"] == {"hello2": "world2"}

        await page.close()

    @with_playwright
    async def test_js_executed_in_order__media(self):
        single_comp_url = TEST_SERVER_URL + "/js-order/media"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // NOTE: This variable should be defined by `check_script_order` component,
            // and it should contain all other variables defined by the previous components
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        # NOTE: The Media JS are loaded BEFORE the components' JS, so they should be empty
        assert data["testSimpleComponent"] is None
        assert data["testSimpleComponentNested"] is None
        assert data["testOtherComponent"] is None

        # Check JS from Media.js
        assert data["testMsg"] == {"hello": "world"}
        assert data["testMsg2"] == {"hello2": "world2"}

        await page.close()

    # In this case the component whose JS is accessing data from other components
    # is used in the template before the other components. So the JS should
    # not be able to access the data from the other components.
    @with_playwright
    async def test_js_executed_in_order__invalid(self):
        single_comp_url = TEST_SERVER_URL + "/js-order/invalid"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // checkVars was defined BEFORE other components, so it should be empty!
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        assert data["testSimpleComponent"] is None
        assert data["testSimpleComponentNested"] is None
        assert data["testOtherComponent"] is None

        # Check JS from Media.js got loaded
        assert data["testMsg"] is None
        assert data["testMsg2"] is None

        await page.close()

    # Fragment where JS and CSS is defined on Component class
    @with_playwright
    async def test_fragment_comp(self):
        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/js?frag=comp")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        assert data_before["targetHtml"] == '<div id="target">OLD</div>'
        assert data_before["fragHtml"] is None

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function(
            "() => document.head.innerHTML.includes('<link href=\"/components/cache/FragComp_')"
        )
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        assert data["targetHtml"] is None
        assert re.compile(
            r'<div class="frag" data-djc-id-\w{7}="">\s*' r"123\s*" r'<span id="frag-text">xxx</span>\s*' r"</div>"
        ).search(data["fragHtml"]) is not None
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    # Fragment where JS and CSS is defined on Media class
    @with_playwright
    async def test_fragment_media(self):
        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/js?frag=media")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        assert data_before["targetHtml"] == '<div id="target">OLD</div>'
        assert data_before["fragHtml"] is None

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function("() => document.head.innerHTML.includes('<link href=\"/static/fragment.css\"')")
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        assert data["targetHtml"] is None
        assert re.compile(
            r'<div class="frag" data-djc-id-\w{7}="">\s*' r"123\s*" r'<span id="frag-text">xxx</span>\s*' r"</div>"
        ).search(data["fragHtml"]) is not None
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    # Fragment loaded by AlpineJS
    @with_playwright
    async def test_fragment_alpine(self):
        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/alpine?frag=comp")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        assert data_before["targetHtml"] == '<div id="target" x-html="htmlVar">OLD</div>'
        assert data_before["fragHtml"] is None

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function(
            "() => document.head.innerHTML.includes('<link href=\"/components/cache/FragComp_')"
        )
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        # NOTE: Unlike the vanilla JS tests, for the Alpine test we don't remove the targetHtml,
        # but only change its contents.
        assert re.compile(
            r'<div class="frag" data-djc-id-\w{7}="">\s*' r"123\s*" r'<span id="frag-text">xxx</span>\s*' r"</div>"
        ).search(data["targetHtml"]) is not None
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    # Fragment loaded by HTMX
    @with_playwright
    async def test_fragment_htmx(self):
        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/htmx?frag=comp")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        assert data_before["targetHtml"] == '<div id="target">OLD</div>'
        assert data_before["fragHtml"] is None

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function(
            "() => document.head.innerHTML.includes('<link href=\"/components/cache/FragComp_')"
        )
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragInnerHtml = fragEl ? fragEl.innerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragInnerHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        assert data["targetHtml"] is None
        # NOTE: We test only the inner HTML, because the element itself may or may not have
        # extra CSS classes added by HTMX, which results in flaky tests.
        assert re.compile(r'123\s*<span id="frag-text">xxx</span>').search(data["fragInnerHtml"]) is not None
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    # Fragment where the page wasn't rendered with the "document" strategy
    @with_playwright
    async def test_fragment_without_document(self):
        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/htmx_raw?frag=comp")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        assert data_before["targetHtml"] == '<div id="target">OLD</div>'
        assert data_before["fragHtml"] is None

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function(
            "() => document.head.innerHTML.includes('<link href=\"/components/cache/FragComp_')"
        )
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        assert data["targetHtml"] is None
        assert re.compile(
            r'<div class="frag" data-djc-id-\w{7}="">\s*' r"123\s*" r'<span id="frag-text">xxx</span>\s*' r"</div>"
        ).search(data["fragHtml"]) is not None
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    @with_playwright
    async def test_alpine__head(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/head"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")

        await page.close()

    @with_playwright
    async def test_alpine__body(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/body"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")

        await page.close()

    @with_playwright
    async def test_alpine__body2(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/body2"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")

        await page.close()

    @with_playwright
    async def test_alpine__invalid(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/invalid"

        page: Page = await self.browser.new_page()  # type: ignore[attr-defined]
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST:")

        await page.close()
