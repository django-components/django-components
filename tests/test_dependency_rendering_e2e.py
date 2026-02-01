"""
Here we check that all parts of managing JS and CSS dependencies work together
in an actual browser.
"""

import re
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual, assertInHTML

from django_components import Component, register, types
from django_components.testing import djc_test
from tests.e2e.utils import TEST_SERVER_URL, with_playwright
from tests.testutils import setup_test_config

if TYPE_CHECKING:
    from playwright.async_api import Browser

    from tests.e2e.utils import BrowserType

setup_test_config()


def server():
    """Define server-side components and views for E2E tests"""

    # Components (order: inner first so outer can use it)
    @register("inner")
    class InnerComponent(Component):
        template: types.django_html = """
            Variable: <strong class="inner">{{ variable }}</strong>
        """
        css: types.css = """
            .inner {
                font-size: 4px;
            }
        """
        js: types.js = """
            globalThis.testInnerComponent = 'kapowww!'
        """

        class Defaults:
            variable2 = "default"

        def get_template_data(self, args, kwargs, slots, context):
            return {
                "variable": kwargs["variable"],
                "variable2": kwargs["variable2"],
            }

        class Media:
            css = "style.css"
            js = "script.js"

    @register("outer")
    class OuterComponent(Component):
        template: types.django_html = """
            {% load component_tags %}
            <div class="outer">
                {% component "inner" variable=variable / %}
                {% slot "default" default / %}
            </div>
        """
        css: types.css = """
            .outer {
                font-size: 40px;
            }
        """
        js: types.js = """
            globalThis.testOuterComponent = 'bongo!'
        """

        def get_template_data(self, args, kwargs, slots, context):
            return {"variable": kwargs["variable"]}

        class Media:
            css = ["style.css", "style2.css"]
            js = "script2.js"

    @register("other")
    class OtherComponent(Component):
        template: types.django_html = """
            XYZ: <strong class="other">{{ variable }}</strong>
        """
        css: types.css = """
            .other {
                display: flex;
            }
        """
        js: types.js = """
            globalThis.testOtherComponent = 'wowzee!'
        """

        def get_template_data(self, args, kwargs, slots, context):
            return {"variable": kwargs["variable"]}

        class Media:
            css = "style.css"
            js = "script.js"

    @register("check_script_order_in_js")
    class CheckScriptOrderInJs(Component):
        template = "<check_script_order>"
        js: types.js = """
            globalThis.checkVars = {
                testInnerComponent,
                testOuterComponent,
                testOtherComponent,
                testMsg,
                testMsg2,
            };
        """

    @register("check_script_order_in_media")
    class CheckScriptOrderInMedia(Component):
        template = "<check_script_order>"

        class Media:
            js = "check_script_order.js"

    @register("frag_comp")
    class FragComp(Component):
        template: types.django_html = """
            <div class="frag">
                123
                <span id="frag-text"></span>
            </div>
        """
        js = """
            document.querySelector('#frag-text').textContent = 'xxx';
        """
        css = """
            .frag {
                background: blue;
            }
        """

    @register("frag_media")
    class FragMedia(Component):
        template = """
            <div class="frag">
                123
                <span id="frag-text"></span>
            </div>
        """

        class Media:
            js = "fragment.js"
            css = "fragment.css"

    @register("alpine_test_in_media")
    class AlpineCompInMedia(Component):
        template: types.django_html = """
            <div x-data="alpine_test">
                ALPINE_TEST:
                <div x-text="somevalue"></div>
            </div>
        """

        class Media:
            js = "alpine_test.js"

    @register("alpine_test_in_js")
    class AlpineCompInJs(Component):
        template: types.django_html = """
            <div x-data="alpine_test">
                ALPINE_TEST:
                <div x-text="somevalue"></div>
            </div>
        """
        js: types.js = """
            document.addEventListener('alpine:init', () => {
                Alpine.data('alpine_test', () => ({
                    somevalue: 123,
                }))
            });
        """

    # Views
    def single_component_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'inner' variable='foo' / %}
                    <div class="my-style">123</div>
                    <div class="my-style2">xyz</div>
                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def multiple_components_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'outer' variable='variable' %}
                        {% component 'other' variable='variable_inner' / %}
                    {% endcomponent %}
                    <div class="my-style">123</div>
                    <div class="my-style2">xyz</div>
                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def alpine_in_head_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                    <script defer src="https://unpkg.com/alpinejs"></script>
                </head>
                <body>
                    {% component 'alpine_test_in_media' / %}
                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def alpine_in_body_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'alpine_test_in_media' / %}
                    {% component_js_dependencies %}
                    <script src="https://unpkg.com/alpinejs"></script>
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def alpine_in_body_view_2(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'alpine_test_in_js' / %}
                    {% component_js_dependencies %}
                    <script src="https://unpkg.com/alpinejs"></script>
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def alpine_in_body_vars_not_available_before_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'alpine_test_in_js' / %}
                    {# Alpine loaded BEFORE components JS #}
                    <script src="https://unpkg.com/alpinejs"></script>
                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def check_js_order_in_js_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'outer' variable='variable' %}
                        {% component 'other' variable='variable_inner' / %}
                    {% endcomponent %}
                    {# check_script_order_in_media is AFTER the other components #}
                    {% component 'check_script_order_in_js' / %}
                    abc
                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def check_js_order_in_media_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'outer' variable='variable' %}
                        {% component 'other' variable='variable_inner' / %}
                    {% endcomponent %}
                    {# check_script_order_in_media is AFTER the other components #}
                    {% component 'check_script_order_in_media' / %}
                    abc
                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def check_js_order_vars_not_available_before_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {# check_script_order_in_media is BEFORE the other components #}
                    {% component 'check_script_order_in_media' / %}
                    {% component 'outer' variable='variable' %}
                        {% component 'other' variable='variable_inner' / %}
                    {% endcomponent %}
                    abc
                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def fragment_base_js_view(request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                </head>
                <body>
                    {% component 'inner' variable='foo' / %}

                    <div id="target">OLD</div>

                    <button id="loader">
                      Click me!
                    </button>
                    <script>
                        const frag = "{{ frag }}";
                        document.querySelector('#loader').addEventListener('click', function () {
                            fetch(`/fragment/frag?frag=${frag}`)
                                .then(response => response.text())
                                .then(html => {
                                    console.log({ fragment: html })
                                    const target = document.querySelector('#target');
                                    const a = new DOMParser().parseFromString(html, "text/html");
                                    target.replaceWith(...a.body.childNodes);
                                    for (const script of a.querySelectorAll('script')) {
                                        const newScript = document.createElement('script');
                                        newScript.textContent = script.textContent;
                                        newScript.async = false;
                                        document.body.appendChild(newScript);
                                    }
                                });
                        });
                    </script>

                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        frag = request.GET["frag"]
        rendered = template.render(Context({"frag": frag}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def fragment_base_alpine_view(request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                    <script defer src="https://unpkg.com/alpinejs"></script>
                </head>
                <body x-data="{
                    htmlVar: 'OLD',
                    loadFragment: function () {
                        const frag = '{{ frag }}';
                        fetch(`/fragment/frag?frag=${frag}`)
                            .then(response => response.text())
                            .then(html => {
                                console.log({ fragment: html });
                                this.htmlVar = html;
                            });
                    }
                }">
                    {% component 'inner' variable='foo' / %}

                    <div id="target" x-html="htmlVar">OLD</div>

                    <button id="loader" @click="loadFragment">
                      Click me!
                    </button>

                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        frag = request.GET["frag"]
        rendered = template.render(Context({"frag": frag}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def fragment_base_htmx_view(request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
                </head>
                <body>
                    {% component 'inner' variable='foo' / %}

                    <div id="target">OLD</div>

                    <button id="loader" hx-get="/fragment/frag?frag={{ frag }}" hx-swap="outerHTML" hx-target="#target">
                      Click me!
                    </button>

                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        frag = request.GET["frag"]
        rendered = template.render(Context({"frag": frag}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def fragment_base_htmx_view__raw(request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head>
                    {% component_css_dependencies %}
                    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
                </head>
                <body>
                    {% component 'inner' variable='foo' / %}

                    <div id="target">OLD</div>

                    <button id="loader" hx-get="/fragment/frag?frag={{ frag }}" hx-swap="outerHTML" hx-target="#target">
                      Click me!
                    </button>

                    {% component_js_dependencies %}
                </body>
            </html>
        """
        template = Template(template_str)
        frag = request.GET["frag"]
        rendered = template.render(
            Context({"frag": frag, "DJC_DEPS_STRATEGY": "ignore"}),
        )
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def fragment_view(request):
        fragment_type = request.GET["frag"]
        if fragment_type == "comp":
            return FragComp.render_to_response(deps_strategy="fragment")
        if fragment_type == "media":
            return FragMedia.render_to_response(deps_strategy="fragment")
        raise ValueError("Invalid fragment type")

    return {
        "/single/": single_component_view,
        "/multi/": multiple_components_view,
        "/alpine/head": alpine_in_head_view,
        "/alpine/body": alpine_in_body_view,
        "/alpine/body2": alpine_in_body_view_2,
        "/alpine/invalid": alpine_in_body_vars_not_available_before_view,
        "/js-order/js": check_js_order_in_js_view,
        "/js-order/media": check_js_order_in_media_view,
        "/js-order/invalid": check_js_order_vars_not_available_before_view,
        "/fragment/base/alpine": fragment_base_alpine_view,
        "/fragment/base/htmx": fragment_base_htmx_view,
        "/fragment/base/htmx_raw": fragment_base_htmx_view__raw,
        "/fragment/base/js": fragment_base_js_view,
        "/fragment/frag": fragment_view,
    }


@djc_test
class TestE2eDependencyRendering:
    @with_playwright
    async def test_single_component_dependencies(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/single"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            const bodyHTML = document.body.innerHTML;

            const innerEl = document.querySelector(".inner");
            const innerFontSize = globalThis.getComputedStyle(innerEl).getPropertyValue('font-size');

            const myStyleEl = document.querySelector(".my-style");
            const myStyleBg = globalThis.getComputedStyle(myStyleEl).getPropertyValue('background');

            return {
                bodyHTML,
                componentJsMsg: globalThis.testInnerComponent,
                scriptJsMsg: globalThis.testMsg,
                innerFontSize,
                myStyleBg,
            };
        }"""

        data = await page.evaluate(test_js)

        # Check that the actual HTML content was loaded
        assert (
            re.compile(r'Variable: <strong class="inner" data-djc-id-\w{7}="">foo</strong>').search(data["bodyHTML"])
            is not None
        )
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
    async def test_multiple_component_dependencies(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/multi"

        page = await browser.new_page()
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
                component1JsMsg: globalThis.testInnerComponent,
                component2JsMsg: globalThis.testOuterComponent,
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
        assert (
            re.compile(
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
                r'<div class="my-style2">xyz<\/div>\s*',
            ).search(data["bodyHTML"])
            is not None
        )

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
    async def test_renders_css_nojs_env(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/multi"

        page = await browser.new_page(java_script_enabled=False)
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
                component1JsMsg: globalThis.testInnerComponent,
                component2JsMsg: globalThis.testOuterComponent,
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
        assert (
            re.compile(
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
            ).search(data["bodyHTML"])
            is not None
        )

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
    async def test_js_executed_in_order__js(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/js-order/js"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // NOTE: This variable should be defined by `check_script_order` component,
            // and it should contain all other variables defined by the previous components
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        assert data["testInnerComponent"] == "kapowww!"
        assert data["testOuterComponent"] == "bongo!"
        assert data["testOtherComponent"] == "wowzee!"

        # Check JS from Media.js got loaded
        assert data["testMsg"] == {"hello": "world"}
        assert data["testMsg2"] == {"hello2": "world2"}

        await page.close()

    @with_playwright
    async def test_js_executed_in_order__media(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/js-order/media"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // NOTE: This variable should be defined by `check_script_order` component,
            // and it should contain all other variables defined by the previous components
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        # NOTE: The Media JS are loaded BEFORE the components' JS, so they should be empty
        assert data["testInnerComponent"] is None
        assert data["testOuterComponent"] is None
        assert data["testOtherComponent"] is None

        # Check JS from Media.js
        assert data["testMsg"] == {"hello": "world"}
        assert data["testMsg2"] == {"hello2": "world2"}

        await page.close()

    # In this case the component whose JS is accessing data from other components
    # is used in the template before the other components. So the JS should
    # not be able to access the data from the other components.
    @with_playwright
    async def test_js_executed_in_order__invalid(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/js-order/invalid"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // checkVars was defined BEFORE other components, so it should be empty!
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        assert data["testInnerComponent"] is None
        assert data["testOuterComponent"] is None
        assert data["testOtherComponent"] is None

        # Check JS from Media.js got loaded
        assert data["testMsg"] is None
        assert data["testMsg2"] is None

        await page.close()

    # Fragment where JS and CSS is defined on Component class
    @with_playwright
    async def test_fragment_comp(self, browser: "Browser", browser_name: "BrowserType"):
        page = await browser.new_page()
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
            """
            () => document.head.innerHTML.includes(
              '<link media="all" rel="stylesheet" href="/components/cache/FragComp_'
            )
            """,
        )
        # Wait for stylesheet to load (CI can be slow; link in DOM ≠ fetch complete)
        await page.wait_for_function(
            """
            () => {
                const link = document.querySelector('link[href*="FragComp_"]');
                return link && link.sheet !== null;
            }
            """,
        )
        # Wait for stylesheet to be applied (Firefox can apply later than link load)
        await page.wait_for_function(
            """
            () => {
                const fragEl = document.querySelector(".frag");
                if (!fragEl) return false;
                const bg = globalThis.getComputedStyle(fragEl).getPropertyValue('background');
                return bg.includes('rgb(0, 0, 255)');
            }
            """,
        )

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
        assert (
            re.compile(
                r'<div class="frag" data-djc-id-\w{7}="">\s*'
                r"123\s*"
                r'<span id="frag-text">xxx</span>\s*'
                r"</div>",
            ).search(data["fragHtml"])
            is not None
        )
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    # Fragment where JS and CSS is defined on Media class
    @with_playwright
    async def test_fragment_media(self, browser: "Browser", browser_name: "BrowserType"):
        page = await browser.new_page()
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
        await page.wait_for_function(
            """
            () => document.head.innerHTML.includes(
              '<link media="all" rel="stylesheet" href="/static/fragment.css"'
            )
            """,
        )
        # Wait for stylesheet to load (CI can be slow; link in DOM ≠ fetch complete)
        await page.wait_for_function(
            """
            () => {
                const link = document.querySelector('link[href*="fragment.css"]');
                return link && link.sheet !== null;
            }
            """,
        )
        # Wait for stylesheet to be applied (Firefox can apply later than link load)
        await page.wait_for_function(
            """
            () => {
                const fragEl = document.querySelector(".frag");
                if (!fragEl) return false;
                const bg = globalThis.getComputedStyle(fragEl).getPropertyValue('background');
                return bg.includes('rgb(0, 0, 255)');
            }
            """,
        )

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
        assert (
            re.compile(
                r'<div class="frag" data-djc-id-\w{7}="">\s*'
                r"123\s*"
                r'<span id="frag-text">xxx</span>\s*'
                r"</div>",
            ).search(data["fragHtml"])
            is not None
        )
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    # Fragment loaded by AlpineJS
    @with_playwright
    async def test_fragment_alpine(self, browser: "Browser", browser_name: "BrowserType"):
        page = await browser.new_page()
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
            """
            () => document.head.innerHTML.includes(
              '<link media="all" rel="stylesheet" href="/components/cache/FragComp_'
            )
            """,
        )
        # Wait for stylesheet to load (CI can be slow; link in DOM ≠ fetch complete)
        await page.wait_for_function(
            """
            () => {
                const link = document.querySelector('link[href*="FragComp_"]');
                return link && link.sheet !== null;
            }
            """,
        )
        # Wait for stylesheet to be applied (Firefox can apply later than link load)
        await page.wait_for_function(
            """
            () => {
                const fragEl = document.querySelector(".frag");
                if (!fragEl) return false;
                const bg = globalThis.getComputedStyle(fragEl).getPropertyValue('background');
                return bg.includes('rgb(0, 0, 255)');
            }
            """,
        )

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
        assert (
            re.compile(
                r'<div class="frag" data-djc-id-\w{7}="">\s*'
                r"123\s*"
                r'<span id="frag-text">xxx</span>\s*'
                r"</div>",
            ).search(data["targetHtml"])
            is not None
        )
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()

    # Fragment loaded by HTMX
    @with_playwright
    async def test_fragment_htmx(self, browser: "Browser", browser_name: "BrowserType"):
        page = await browser.new_page()
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
            """
            () => document.head.innerHTML.includes(
              '<link media="all" rel="stylesheet" href="/components/cache/FragComp_'
            )
            """,
        )
        # Wait for stylesheet to load (CI can be slow; link in DOM ≠ fetch complete)
        await page.wait_for_function(
            """
            () => {
                const link = document.querySelector('link[href*="FragComp_"]');
                return link && link.sheet !== null;
            }
            """,
        )
        # Wait for stylesheet to be applied (Firefox can apply later than link load)
        await page.wait_for_function(
            """
            () => {
                const fragEl = document.querySelector(".frag");
                if (!fragEl) return false;
                const bg = globalThis.getComputedStyle(fragEl).getPropertyValue('background');
                return bg.includes('rgb(0, 0, 255)');
            }
            """,
        )

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
    async def test_fragment_without_document(self, browser: "Browser", browser_name: "BrowserType"):
        page = await browser.new_page()
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
            """
            () => document.head.innerHTML.includes(
              '<link media="all" rel="stylesheet" href="/components/cache/FragComp_'
            )
            """,
        )
        # Wait for stylesheet to load (CI can be slow; link in DOM ≠ fetch complete)
        await page.wait_for_function(
            """
            () => {
                const link = document.querySelector('link[href*="FragComp_"]');
                return link && link.sheet !== null;
            }
            """,
        )
        # Wait for stylesheet to be applied (Firefox can apply later than link load)
        await page.wait_for_function(
            """
            () => {
                const fragEl = document.querySelector(".frag");
                if (!fragEl) return false;
                const bg = globalThis.getComputedStyle(fragEl).getPropertyValue('background');
                return bg.includes('rgb(0, 0, 255)');
            }
            """,
        )

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
        assert (
            re.compile(
                r'<div class="frag" data-djc-id-\w{7}="">\s*'
                r"123\s*"
                r'<span id="frag-text">xxx</span>\s*'
                r"</div>",
            ).search(data["fragHtml"])
            is not None
        )
        assert "rgb(0, 0, 255)" in data["fragBg"]  # AKA 'background: blue'

        await page.close()


@djc_test
class TestE2eAlpineCompat:
    @with_playwright
    async def test_alpine__head(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/alpine/head"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")  # type: ignore[union-attr]

        await page.close()

    @with_playwright
    async def test_alpine__body(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/alpine/body"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")  # type: ignore[union-attr]

        await page.close()

    @with_playwright
    async def test_alpine__body2(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/alpine/body2"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")  # type: ignore[union-attr]

        await page.close()

    @with_playwright
    async def test_alpine__invalid(self, browser: "Browser", browser_name: "BrowserType"):
        single_comp_url = TEST_SERVER_URL + "/alpine/invalid"

        page = await browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        assertHTMLEqual(component_text.strip(), "ALPINE_TEST:")  # type: ignore[union-attr]

        await page.close()
