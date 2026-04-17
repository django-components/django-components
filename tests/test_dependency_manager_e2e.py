import re
from typing import TYPE_CHECKING

import pytest
from playwright.async_api import Browser, Error, Page

from django_components.testing import djc_test
from tests.e2e.utils import TEST_SERVER_URL, with_playwright
from tests.testutils import setup_test_config

if TYPE_CHECKING:
    from django_components import types
    from tests.e2e.utils import BrowserType

setup_test_config(
    extra_settings={
        "ROOT_URLCONF": "tests.test_dependency_manager",
    },
)

urlpatterns: list = []


async def _create_page_with_dep_manager(browser: Browser) -> Page:
    page = await browser.new_page()

    # Load the JS library by opening a page with the script, and then running the script code
    # E.g. `http://localhost:54017/static/django_components/django_components.min.js`
    script_url = TEST_SERVER_URL + "/static/django_components/django_components.min.js"
    await page.goto(script_url)

    # The page's body is the script code. We load it by executing the code
    await page.evaluate(
        """
        () => {
            eval(document.body.textContent);
        }
        """,
    )

    # Ensure the body is clear
    await page.evaluate(
        """
        () => {
            document.body.innerHTML = '';
            document.head.innerHTML = '';
        }
        """,
    )

    return page


@djc_test(
    django_settings={
        "STATIC_URL": "static/",
    },
)
class TestDependencyManager:
    @with_playwright
    async def test_script_loads(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        # Check the exposed API
        keys = sorted(await page.evaluate("Object.keys(DjangoComponents)"))
        assert keys == ["createComponentsManager", "manager", "unescapeJs"]

        keys = await page.evaluate("Object.keys(DjangoComponents.manager)")
        assert keys == [
            "callComponent",
            "registerComponent",
            "registerComponentData",
            "loadJs",
            "loadCss",
            "markScriptLoaded",
            "waitForScriptsToLoad",
            "_loadComponentScripts",
        ]

        await page.close()

    # TODO_v1: Delete this test in v1
    @with_playwright
    async def test_backwards_compatibility_components_alias(self, browser: "Browser", browser_name: "BrowserType"):
        if browser_name == "firefox":
            pytest.skip("Firefox does not support the `Components` global")

        page = await _create_page_with_dep_manager(browser)

        # Verify that Components is still available as an alias
        components_exists = await page.evaluate("typeof Components !== 'undefined'")
        assert components_exists is True

        # Verify that Components and DjangoComponents are the same object
        are_same = await page.evaluate("Components === DjangoComponents")
        assert are_same is True

        await page.close()


# Tests for `manager.loadJs()` / `manager.loadCss()` / `manager.markAsLoaded()`
@djc_test(
    django_settings={
        "STATIC_URL": "static/",
    },
)
class TestLoadScript:
    @with_playwright
    async def test_load_js_scripts(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = DjangoComponents.createComponentsManager();

            const headBeforeFirstLoad = document.head.innerHTML;

            // Adds a script the first time
            manager.loadJs({'tag': 'script', 'attrs': {'src': '/one/two'}, 'content': ''});
            const bodyAfterFirstLoad = document.body.innerHTML;

            // Does not add it the second time
            manager.loadJs({'tag': 'script', 'attrs': {'src': '/one/two'}, 'content': ''});
            const bodyAfterSecondLoad = document.body.innerHTML;

            // Adds different script
            manager.loadJs({'tag': 'script', 'attrs': {'src': '/four/three'}, 'content': ''});
            const bodyAfterThirdLoad = document.body.innerHTML;

            const headAfterThirdLoad = document.head.innerHTML;

            return {
                bodyAfterFirstLoad,
                bodyAfterSecondLoad,
                bodyAfterThirdLoad,
                headBeforeFirstLoad,
                headAfterThirdLoad,
            };
        }"""

        data = await page.evaluate(test_js)

        assert data["bodyAfterFirstLoad"] == '<script src="/one/two"></script>'
        assert data["bodyAfterSecondLoad"] == '<script src="/one/two"></script>'
        assert data["bodyAfterThirdLoad"] == '<script src="/one/two"></script><script src="/four/three"></script>'

        assert data["headBeforeFirstLoad"] == data["headAfterThirdLoad"]
        assert data["headBeforeFirstLoad"] == ""

        await page.close()

    @with_playwright
    async def test_load_css_scripts(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = DjangoComponents.createComponentsManager();

            const bodyBeforeFirstLoad = document.body.innerHTML;

            // Adds a script the first time
            manager.loadCss({'tag': 'link', 'attrs': {'href': '/one/two'}, 'content': ''});
            const headAfterFirstLoad = document.head.innerHTML;

            // Does not add it the second time
            manager.loadCss({'tag': 'link', 'attrs': {'href': '/one/two'}, 'content': ''});
            const headAfterSecondLoad = document.head.innerHTML;

            // Adds different script
            manager.loadCss({'tag': 'link', 'attrs': {'href': '/four/three'}, 'content': ''});
            const headAfterThirdLoad = document.head.innerHTML;

            const bodyAfterThirdLoad = document.body.innerHTML;

            return {
                headAfterFirstLoad,
                headAfterSecondLoad,
                headAfterThirdLoad,
                bodyBeforeFirstLoad,
                bodyAfterThirdLoad,
            };
        }"""

        data = await page.evaluate(test_js)

        assert data["headAfterFirstLoad"] == '<link href="/one/two">'
        assert data["headAfterSecondLoad"] == '<link href="/one/two">'
        assert data["headAfterThirdLoad"] == '<link href="/one/two"><link href="/four/three">'

        assert data["bodyBeforeFirstLoad"] == data["bodyAfterThirdLoad"]
        assert data["bodyBeforeFirstLoad"] == ""

        await page.close()

    @with_playwright
    async def test_does_not_load_script_if_marked_as_loaded(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = DjangoComponents.createComponentsManager();

            // Adds a script the first time
            manager.markScriptLoaded('css', '/one/two');
            manager.markScriptLoaded('js', '/one/three');

            manager.loadCss({'tag': 'link', 'attrs': {'href': '/one/two'}, 'content': ''});
            const headAfterFirstLoad = document.head.innerHTML;

            manager.loadJs({'tag': 'script', 'attrs': {'src': '/one/three'}, 'content': ''});
            const bodyAfterSecondLoad = document.body.innerHTML;

            return {
                headAfterFirstLoad,
                bodyAfterSecondLoad,
            };
        }"""

        data = await page.evaluate(test_js)

        assert data["headAfterFirstLoad"] == ""
        assert data["bodyAfterSecondLoad"] == ""

        await page.close()


# Tests for `manager.registerComponent()` / `registerComponentData()` / `callComponent()`
@djc_test(
    django_settings={
        "STATIC_URL": "static/",
    },
)
class TestCallComponent:
    @with_playwright
    async def test_calls_component_successfully(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        test_js: types.js = """async () => {
            const manager = DjangoComponents.createComponentsManager();

            const compName = 'my_comp';
            const compId = 'c12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-c12345> abc </div>');

            let captured = null;
            manager.registerComponent(compName, (data, ctx) => {
                captured = { ctx, data };
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = await manager.callComponent(compName, compId, inputHash);

            // Serialize the HTML elements
            captured.ctx.els = captured.ctx.els.map((el) => el.outerHTML);

            return {
              result,
              captured,
            };
        }"""

        data = await page.evaluate(test_js)

        assert data["result"] == 123
        assert data["captured"] == {
            "data": {
                "hello": "world",
            },
            "ctx": {
                "els": ['<div data-djc-id-c12345=""> abc </div>'],
                "id": "c12345",
                "name": "my_comp",
            },
        }

        await page.close()

    @with_playwright
    async def test_calls_component_successfully_async(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        test_js: types.js = """() => {
            const manager = DjangoComponents.createComponentsManager();

            const compName = 'my_comp';
            const compId = 'c12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-c12345> abc </div>');

            manager.registerComponent(compName, ({ hello }, ctx) => {
                return Promise.resolve(hello + "_component_callback");
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should be Promise
            const result = manager.callComponent(compName, compId, inputHash);
            const isPromise = `${result}` === '[object Promise]';

            // Wrap the whole response in Promise, so we can add extra fields
            return result.then((res) => ({
              result: res,
              isPromise,
            }));
        }"""

        data = await page.evaluate(test_js)

        assert data["result"] == "world_component_callback"
        assert data["isPromise"] is True

        await page.close()

    @with_playwright
    async def test_error_in_component_call_do_not_propagate_sync(
        self, browser: "Browser", browser_name: "BrowserType"
    ):
        page = await _create_page_with_dep_manager(browser)

        test_js: types.js = """() => {
            const manager = DjangoComponents.createComponentsManager();

            const compName = 'my_comp';
            const compId = 'c12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-c12345> abc </div>');

            manager.registerComponent(compName, (data, ctx) => {
                throw Error('Oops!');
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = manager.callComponent(compName, compId, inputHash);
            return Promise.allSettled([result]);
        }"""

        data = await page.evaluate(test_js)

        assert len(data) == 1
        assert data[0]["status"] == "rejected"
        assert isinstance(data[0]["reason"], Error)
        assert data[0]["reason"].message == "Oops!"

        await page.close()

    @with_playwright
    async def test_error_in_component_call_do_not_propagate_async(
        self, browser: "Browser", browser_name: "BrowserType"
    ):
        page = await _create_page_with_dep_manager(browser)

        test_js: types.js = """() => {
            const manager = DjangoComponents.createComponentsManager();

            const compName = 'my_comp';
            const compId = 'c12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-c12345> abc </div>');

            manager.registerComponent(compName, async (data, ctx) => {
                throw Error('Oops!');
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = manager.callComponent(compName, compId, inputHash);
            return Promise.allSettled([result]);
        }"""

        data = await page.evaluate(test_js)

        assert len(data) == 1
        assert data[0]["status"] == "rejected"
        assert isinstance(data[0]["reason"], Error)
        assert data[0]["reason"].message == "Oops!"

        await page.close()

    @with_playwright
    async def test_raises_if_component_element_not_in_dom(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        test_js: types.js = """async () => {
            const manager = DjangoComponents.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            manager.registerComponent(compName, ({ hello }, ctx) => {
                return Promise.resolve(hello + "_component_callback");
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should raise Error
            await manager.callComponent(compName, compId, inputHash);
        }"""

        with pytest.raises(
            Error,
            match=re.escape("[DjangoComponents] 'my_comp': No elements with component ID '12345' found"),
        ):
            await page.evaluate(test_js)

        await page.close()

    @with_playwright
    async def test_callcomponent_waits_for_component_data(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        test_js: types.js = """async () => {
            const manager = DjangoComponents.createComponentsManager();

            const compName = 'my_comp';
            const compId = 'c12345';
            const inputHash = 'input-abc';

            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-c12345> abc </div>');

            manager.registerComponent(compName, ({ hello }, ctx) => {
                return Promise.resolve(hello + "_component_callback");
            });

            // `callComponent()` should be blocked until we register component data.
            let isFinished = false;
            const resultPromise = manager.callComponent(compName, compId, inputHash);
            resultPromise.then(() => {
                isFinished = true;
            });

            // After a short while the component call should be still blocked
            await new Promise((r) => setTimeout(r, 20));
            if (isFinished) {
                throw new Error("callComponent should be still blocked");
            }

            // Only after we register component data, the call should be unblocked
            await manager.registerComponentData(compName, inputHash, () => ({ hello: 'world' }));
            if (!isFinished) {
                throw new Error("callComponent should be unblocked");
            }

            return resultPromise;
        }"""

        data = await page.evaluate(test_js)
        assert data == "world_component_callback"

        await page.close()

    @with_playwright
    async def test_callcomponent_waits_for_component(self, browser: "Browser", browser_name: "BrowserType"):
        page = await _create_page_with_dep_manager(browser)

        test_js: types.js = """async () => {
            const manager = DjangoComponents.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-12345> abc </div>');


            manager.registerComponentData(compName, inputHash, () => ({ hello: 'world' }));

            // `callComponent()` should be blocked until we register component data.
            let isFinished = false;
            const resultPromise = manager.callComponent(compName, compId, inputHash);
            resultPromise.then(() => {
                isFinished = true;
            });

            // After a short while the component call should be still blocked
            await new Promise((r) => setTimeout(r, 20));
            if (isFinished) {
                throw new Error("callComponent should be still blocked");
            }

            // Only after we register component data, the call should be unblocked
            await manager.registerComponent(compName, ({ hello }, ctx) => {
                return Promise.resolve(hello + "_component_callback");
            });
            if (!isFinished) {
                throw new Error("callComponent should be unblocked");
            }

            return resultPromise;
        }"""

        data = await page.evaluate(test_js)
        assert data == "world_component_callback"

        await page.close()
