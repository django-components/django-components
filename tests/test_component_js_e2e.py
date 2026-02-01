"""
End-to-end tests for JS variables feature.

These tests verify that JS variables from `get_js_data()` work correctly
in a real browser environment.
"""

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
    Define server-side components and views for E2E tests.

    This function is automatically discovered and called by the testserver
    to register URL patterns, views, and components.
    """

    @register("js_no_vars_component")
    class JsNoVarsComponent(Component):
        template: types.django_html = """
            <div id="js-no-vars-container" class="js-container">
                <div id="js-no-vars-initial" class="initial-state">Initial</div>
                <div id="js-no-vars-oncomponent" class="oncomponent-state">Not loaded</div>
                <button id="js-no-vars-button" class="test-button">Click me</button>
                <div id="js-no-vars-click-result" class="click-result"></div>
            </div>
        """

        css: types.css = """
            .js-container {
                padding: 20px;
                border: 2px solid #6c757d;
                margin: 10px;
            }
            .initial-state {
                color: #007bff;
                font-weight: bold;
            }
            .oncomponent-state {
                color: #666;
                margin-top: 10px;
            }
            .test-button {
                margin-top: 10px;
                padding: 8px 16px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .click-result {
                margin-top: 10px;
                padding: 10px;
                background: #f0f0f0;
                border-radius: 4px;
            }
        """

        js: types.js = """
            // Code outside $onComponent - runs immediately when script loads
            (function() {
                const initialEl = document.querySelector('#js-no-vars-initial');
                if (initialEl) {
                    initialEl.textContent = 'Immediate execution worked!';
                    initialEl.style.color = '#28a745';
                }
            })();

            // Code inside $onComponent - runs when component is initialized
            $onComponent((data, ctx) => {
                const oncomponentEl = document.querySelector('#js-no-vars-oncomponent');
                if (oncomponentEl) {
                    oncomponentEl.textContent = '$onComponent execution worked!';
                    oncomponentEl.style.color = '#28a745';
                }

                // Also set up click handler inside $onComponent
                const button = document.querySelector('#js-no-vars-button');
                const resultEl = document.querySelector('#js-no-vars-click-result');
                if (button && resultEl) {
                    button.addEventListener('click', () => {
                        resultEl.textContent = 'Button click handler worked!';
                        resultEl.style.background = '#d4edda';
                    });
                }
            });
        """

    @register("js_vars_interactive_button")
    class JsVarsInteractiveButton(Component):
        template: types.django_html = """
            <button id="js-button-{{ button_id }}" class="interactive-button" data-button-id="{{ button_id }}">
                Click me
            </button>
            <div id="js-result-{{ button_id }}" class="result"></div>
            <div id="js-immediate-{{ button_id }}" class="immediate-state">Initial</div>
        """

        js: types.js = """
            // Code outside $onComponent - runs immediately when script loads
            // This sets up markers on all buttons with the class 'interactive-button'
            (function() {
                const buttons = document.querySelectorAll('.interactive-button[data-button-id]');
                buttons.forEach(button => {
                    const buttonId = button.getAttribute('data-button-id');
                    const immediateEl = document.querySelector(`#js-immediate-${buttonId}`);
                    if (immediateEl) {
                        immediateEl.textContent = 'Immediate execution worked!';
                        immediateEl.style.color = '#28a745';
                    }
                });
            })();

            // Code inside $onComponent - runs when component is initialized with variables
            $onComponent(({ message, button_id }, ctx) => {
                const button = document.querySelector(`#js-button-${button_id}`);
                const result = document.querySelector(`#js-result-${button_id}`);

                if (button && result) {
                    button.addEventListener('click', () => {
                        result.textContent = message;
                        result.style.color = button_id;
                    });
                }
            });
        """

        class Kwargs:
            button_id: str
            message: str

        def get_template_data(self, args, kwargs: Kwargs, slots, context):
            return {
                "button_id": kwargs.button_id,
            }

        def get_js_data(self, args, kwargs: Kwargs, slots, context):
            return {
                "message": kwargs.message,
                "button_id": kwargs.button_id,
            }

    @register("js_fragment_no_vars")
    class JsFragmentNoVars(Component):
        template: types.django_html = """
            <div id="fragment-no-vars" class="fragment-container">
                <div class="fragment-content">Fragment without variables</div>
                <div id="fragment-status-no-vars" class="status">Not loaded</div>
            </div>
        """

        css: types.css = """
            .fragment-container {
                padding: 20px;
                border: 2px solid #007bff;
                margin: 10px;
            }
            .fragment-content {
                font-weight: bold;
                color: #007bff;
            }
            .status {
                margin-top: 10px;
                color: #666;
            }
        """

        js: types.js = """
            $onComponent((data, ctx) => {
                const statusEl = document.querySelector('#fragment-status-no-vars');
                if (statusEl) {
                    statusEl.textContent = 'JS loaded successfully';
                    statusEl.style.color = '#28a745';
                }
            });
        """

    @register("js_fragment_with_vars")
    class JsFragmentWithVars(Component):
        template: types.django_html = """
            <div id="fragment-with-vars" class="fragment-container">
                <div class="fragment-content">Fragment with variables</div>
                <div id="fragment-status-with-vars" class="status">Not loaded</div>
                <div id="fragment-data" class="data"></div>
            </div>
        """

        css: types.css = """
            .fragment-container {
                padding: 20px;
                border: 2px solid #28a745;
                margin: 10px;
            }
            .fragment-content {
                font-weight: bold;
                color: #28a745;
            }
            .status {
                margin-top: 10px;
                color: #666;
            }
            .data {
                margin-top: 10px;
                padding: 10px;
                background: #f0f0f0;
                border-radius: 4px;
            }
        """

        class Kwargs:
            user_name: str
            count: int

        js: types.js = """
            $onComponent(({ user_name, count }, ctx) => {
                const statusEl = document.querySelector('#fragment-status-with-vars');
                const dataEl = document.querySelector('#fragment-data');

                if (statusEl) {
                    statusEl.textContent = 'JS loaded with variables';
                    statusEl.style.color = '#28a745';
                }

                if (dataEl) {
                    dataEl.textContent = `User: ${user_name}, Count: ${count}`;
                }
            });
        """

        def get_js_data(self, args, kwargs: Kwargs, slots, context):
            return {
                "user_name": kwargs.user_name,
                "count": kwargs.count,
            }

    @register("js_fragment_base")
    class JsFragmentBase(Component):
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
                        fetch(`/js-vars/fragment/fragment?type=${fragmentType}`)
                            .then(response => response.text())
                            .then(html => {
                                const target = document.querySelector('#target');
                                const parser = new DOMParser();
                                const doc = parser.parseFromString(html, 'text/html');

                                // Replace target with fragment content
                                target.innerHTML = doc.body.innerHTML;
                            });
                    });
                }
            });
        """

    def js_fragment_base_view(_request):
        return JsFragmentBase.render_to_response()

    def js_fragment_view(request):
        fragment_type = request.GET.get("type", "")

        # Return compoent with or without JS vars based on `type` query param
        if fragment_type == "no-vars":
            return JsFragmentNoVars.render_to_response(deps_strategy="fragment")
        elif fragment_type == "with-vars":
            return JsFragmentWithVars.render_to_response(
                kwargs={"user_name": "TestUser", "count": 42},
                deps_strategy="fragment",
            )
        else:
            return HttpResponse("Invalid fragment type", status=400)  # type: ignore[arg-type]

    def js_no_vars_component_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head></head>
                <body>
                    {% component 'js_no_vars_component' / %}
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    def js_vars_multiple_instances_view(_request):
        template_str: types.django_html = """
            {% load component_tags %}
            <!DOCTYPE html>
            <html>
                <head></head>
                <body>
                    <div id="button-red">
                        {% component 'js_vars_interactive_button'
                            button_id='red'
                            message='Red button clicked!'
                        / %}
                    </div>
                    <div id="button-green">
                        {% component 'js_vars_interactive_button'
                            button_id='green'
                            message='Green button clicked!'
                        / %}
                    </div>
                    <div id="button-blue">
                        {% component 'js_vars_interactive_button'
                            button_id='blue'
                            message='Blue button clicked!'
                        / %}
                    </div>
                </body>
            </html>
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        return HttpResponse(rendered)  # type: ignore[arg-type]

    return {
        "/js-vars/document/no-vars": js_no_vars_component_view,
        "/js-vars/document/vars": js_vars_multiple_instances_view,
        "/js-vars/fragment/base": js_fragment_base_view,
        "/js-vars/fragment/fragment": js_fragment_view,
    }


@djc_test
class TestJsVariablesE2E:
    @with_playwright
    async def test_document_no_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        url = TEST_SERVER_URL + "/js-vars/document/no-vars"

        page = await browser.new_page()
        await page.goto(url)

        # Wait for JS to load and execute
        await page.wait_for_timeout(500)

        # Verify both immediate execution and $onComponent execution worked
        test_js: types.js = """() => {
            const initialEl = document.querySelector('#js-no-vars-initial');
            const oncomponentEl = document.querySelector('#js-no-vars-oncomponent');
            const button = document.querySelector('#js-no-vars-button');
            const resultEl = document.querySelector('#js-no-vars-click-result');

            // Check initial state (code outside $onComponent)
            const initialText = initialEl ? initialEl.textContent : null;
            const initialColor = initialEl ? window.getComputedStyle(initialEl).color : null;

            // Check oncomponent state (code inside $onComponent)
            const oncomponentText = oncomponentEl ? oncomponentEl.textContent : null;
            const oncomponentColor = oncomponentEl ? window.getComputedStyle(oncomponentEl).color : null;

            // Click button to test click handler (set up inside $onComponent)
            if (button) {
                button.click();
            }

            // Wait a bit for click handler to execute
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve({
                        initialText: initialText,
                        initialColor: initialColor,
                        oncomponentText: oncomponentText,
                        oncomponentColor: oncomponentColor,
                        clickResultText: resultEl ? resultEl.textContent : null,
                        clickResultBg: resultEl ? window.getComputedStyle(resultEl).backgroundColor : null,
                    });
                }, 100);
            });
        }"""

        data = await page.evaluate(test_js)

        # Verify immediate execution (outside $onComponent) worked
        assert data["initialText"] == "Immediate execution worked!"
        assert "rgb(40, 167, 69)" in data["initialColor"] or "#28a745" in data["initialColor"]

        # Verify $onComponent execution worked
        assert data["oncomponentText"] == "$onComponent execution worked!"
        assert "rgb(40, 167, 69)" in data["oncomponentColor"] or "#28a745" in data["oncomponentColor"]

        # Verify click handler (set up inside $onComponent) worked
        assert data["clickResultText"] == "Button click handler worked!"
        assert "rgb(212, 237, 218)" in data["clickResultBg"] or "#d4edda" in data["clickResultBg"]

        await page.close()

    @with_playwright
    async def test_document_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        url = TEST_SERVER_URL + "/js-vars/document/vars"

        page = await browser.new_page()
        await page.goto(url)

        # Wait for JS to load and execute
        await page.wait_for_timeout(500)

        test_js: types.js = """() => {
            const redButton = document.querySelector('#js-button-red');
            const greenButton = document.querySelector('#js-button-green');
            const blueButton = document.querySelector('#js-button-blue');

            const redResult = document.querySelector('#js-result-red');
            const greenResult = document.querySelector('#js-result-green');
            const blueResult = document.querySelector('#js-result-blue');

            // Check immediate execution (outside $onComponent)
            const redImmediate = document.querySelector('#js-immediate-red');
            const greenImmediate = document.querySelector('#js-immediate-green');
            const blueImmediate = document.querySelector('#js-immediate-blue');

            // Click each button to trigger the JS variable usage (inside $onComponent)
            redButton.click();
            greenButton.click();
            blueButton.click();

            // Wait a bit for the click handlers to execute
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve({
                        // Verify $onComponent execution (click handlers with variables)
                        redMessage: redResult ? redResult.textContent : null,
                        greenMessage: greenResult ? greenResult.textContent : null,
                        blueMessage: blueResult ? blueResult.textContent : null,
                        redButtonId: redButton ? redButton.id : null,
                        greenButtonId: greenButton ? greenButton.id : null,
                        blueButtonId: blueButton ? blueButton.id : null,
                        // Verify immediate execution (outside $onComponent)
                        redImmediateText: redImmediate ? redImmediate.textContent : null,
                        redImmediateColor: redImmediate ? window.getComputedStyle(redImmediate).color : null,
                        greenImmediateText: greenImmediate ? greenImmediate.textContent : null,
                        greenImmediateColor: greenImmediate ? window.getComputedStyle(greenImmediate).color : null,
                        blueImmediateText: blueImmediate ? blueImmediate.textContent : null,
                        blueImmediateColor: blueImmediate ? window.getComputedStyle(blueImmediate).color : null,
                    });
                }, 100);
            });
        }"""

        data = await page.evaluate(test_js)

        # Verify $onComponent execution - each button has the correct message set via JS variables
        assert data["redMessage"] == "Red button clicked!"
        assert data["greenMessage"] == "Green button clicked!"
        assert data["blueMessage"] == "Blue button clicked!"

        # Verify button IDs are correct
        assert data["redButtonId"] == "js-button-red"
        assert data["greenButtonId"] == "js-button-green"
        assert data["blueButtonId"] == "js-button-blue"

        # Verify immediate execution (outside $onComponent) worked for all instances
        assert data["redImmediateText"] == "Immediate execution worked!"
        assert "rgb(40, 167, 69)" in data["redImmediateColor"] or "#28a745" in data["redImmediateColor"]
        assert data["greenImmediateText"] == "Immediate execution worked!"
        assert "rgb(40, 167, 69)" in data["greenImmediateColor"] or "#28a745" in data["greenImmediateColor"]
        assert data["blueImmediateText"] == "Immediate execution worked!"
        assert "rgb(40, 167, 69)" in data["blueImmediateColor"] or "#28a745" in data["blueImmediateColor"]

        await page.close()

    @with_playwright
    async def test_fragment_no_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        """Test that a fragment component loads its JS and CSS when inserted into DOM."""
        url = TEST_SERVER_URL + "/js-vars/fragment/base"

        page = await browser.new_page()
        await page.goto(url)

        # Wait for initial page load
        await page.wait_for_timeout(500)

        # Set the fragment type and click the button
        await page.evaluate("""() => {
            const btn = document.querySelector('#load-fragment-btn');
            btn.setAttribute('data-fragment-type', 'no-vars');
        }""")

        await page.click("#load-fragment-btn")

        # Wait for fragment to load
        await page.wait_for_timeout(1000)

        # Verify fragment was inserted and JS executed
        test_js: types.js = """() => {
            const fragment = document.querySelector('#fragment-no-vars');
            const status = document.querySelector('#fragment-status-no-vars');
            const content = document.querySelector('.fragment-content');

            // Check if CSS is applied (border should be set)
            const computedStyle = fragment ? window.getComputedStyle(fragment) : null;
            const borderColor = computedStyle ? computedStyle.borderColor : null;

            return {
                fragmentExists: fragment !== null,
                statusText: status ? status.textContent : null,
                statusColor: status ? window.getComputedStyle(status).color : null,
                contentText: content ? content.textContent : null,
                hasBorder: borderColor && borderColor !== 'rgba(0, 0, 0, 0)',
            };
        }"""

        data = await page.evaluate(test_js)

        # Verify fragment was loaded
        assert data["fragmentExists"] is True
        assert data["contentText"] == "Fragment without variables"
        assert data["statusText"] == "JS loaded successfully"
        # Verify CSS was applied (status should be green)
        assert "rgb(40, 167, 69)" in data["statusColor"] or "#28a745" in data["statusColor"]
        assert data["hasBorder"] is True

        await page.close()

    @with_playwright
    async def test_fragment_with_vars(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        """Test that a fragment component loads with JS variables when inserted into DOM."""
        url = TEST_SERVER_URL + "/js-vars/fragment/base"

        page = await browser.new_page()
        await page.goto(url)

        # Wait for initial page load
        await page.wait_for_timeout(500)

        # Set the fragment type and click the button
        await page.evaluate("""() => {
            const btn = document.querySelector('#load-fragment-btn');
            btn.setAttribute('data-fragment-type', 'with-vars');
        }""")

        await page.click("#load-fragment-btn")

        # Wait for fragment to load
        await page.wait_for_timeout(500)

        # Verify fragment was inserted, JS executed, and variables were passed
        test_js: types.js = """() => {
            const fragment = document.querySelector('#fragment-with-vars');
            const status = document.querySelector('#fragment-status-with-vars');
            const data = document.querySelector('#fragment-data');
            const content = document.querySelector('.fragment-content');

            // Check if CSS is applied
            const computedStyle = fragment ? window.getComputedStyle(fragment) : null;
            const borderColor = computedStyle ? computedStyle.borderColor : null;

            return {
                fragmentExists: fragment !== null,
                statusText: status ? status.textContent : null,
                statusColor: status ? window.getComputedStyle(status).color : null,
                dataText: data ? data.textContent : null,
                contentText: content ? content.textContent : null,
                hasBorder: borderColor && borderColor !== 'rgba(0, 0, 0, 0)',
            };
        }"""

        data = await page.evaluate(test_js)

        # Verify fragment was loaded
        assert data["fragmentExists"] is True
        assert data["contentText"] == "Fragment with variables"
        assert data["statusText"] == "JS loaded with variables"
        # Verify JS variables were passed and used
        assert data["dataText"] == "User: TestUser, Count: 42"
        # Verify CSS was applied (status should be green)
        assert "rgb(40, 167, 69)" in data["statusColor"] or "#28a745" in data["statusColor"]
        assert data["hasBorder"] is True

        await page.close()
