import re
from typing import List

import pytest
from playwright.async_api import Browser, Error, Page

from django_components import types
from django_components.testing import djc_test
from tests.testutils import setup_test_config
from tests.e2e.utils import TEST_SERVER_URL, with_playwright

setup_test_config(
    components={"autodiscover": False},
    extra_settings={
        "ROOT_URLCONF": "tests.test_dependency_manager",
    },
)

urlpatterns: List = []


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
        """
    )

    # Ensure the body is clear
    await page.evaluate(
        """
        () => {
            document.body.innerHTML = '';
            document.head.innerHTML = '';
        }
        """
    )

    return page


@djc_test(
    django_settings={
        "STATIC_URL": "static/",
    }
)
class TestDependencyManager:
    @with_playwright
    async def test_script_loads(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        # Check the exposed API
        keys = sorted(await page.evaluate("Object.keys(Components)"))
        assert keys == ["createComponentsManager", "manager", "unescapeJs"]

        keys = await page.evaluate("Object.keys(Components.manager)")
        assert keys == [
            "callComponent",
            "registerComponent",
            "registerComponentData",
            "loadJs",
            "loadCss",
            "markScriptLoaded",
        ]

        await page.close()


# Tests for `manager.loadJs()` / `manager.loadCss()` / `manager.markAsLoaded()`
@djc_test(
    django_settings={
        "STATIC_URL": "static/",
    }
)
class TestLoadScript:
    @with_playwright
    async def test_load_js_scripts(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const headBeforeFirstLoad = document.head.innerHTML;

            // Adds a script the first time
            manager.loadJs("<script src='/one/two'></script>");
            const bodyAfterFirstLoad = document.body.innerHTML;

            // Does not add it the second time
            manager.loadJs("<script src='/one/two'></script>");
            const bodyAfterSecondLoad = document.body.innerHTML;

            // Adds different script
            manager.loadJs("<script src='/four/three'></script>");
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
    async def test_load_css_scripts(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const bodyBeforeFirstLoad = document.body.innerHTML;

            // Adds a script the first time
            manager.loadCss("<link href='/one/two'>");
            const headAfterFirstLoad = document.head.innerHTML;

            // Does not add it the second time
            manager.loadCss("<link herf='/one/two'>");
            const headAfterSecondLoad = document.head.innerHTML;

            // Adds different script
            manager.loadCss("<link href='/four/three'>");
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
    async def test_does_not_load_script_if_marked_as_loaded(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            // Adds a script the first time
            manager.markScriptLoaded('css', '/one/two');
            manager.markScriptLoaded('js', '/one/three');

            manager.loadCss("<link href='/one/two'>");
            const headAfterFirstLoad = document.head.innerHTML;

            manager.loadJs("<script src='/one/three'></script>");
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
    }
)
class TestCallComponent:
    @with_playwright
    async def test_calls_component_successfully(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-12345> abc </div>');

            let captured = null;
            manager.registerComponent(compName, (data, ctx) => {
                captured = { ctx, data };
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = manager.callComponent(compName, compId, inputHash);

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
                "els": ['<div data-djc-id-12345=""> abc </div>'],
                "id": "12345",
                "name": "my_comp",
            },
        }

        await page.close()

    @with_playwright
    async def test_calls_component_successfully_async(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-12345> abc </div>');

            manager.registerComponent(compName, (data, ctx) => {
                return Promise.resolve(123);
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should be Promise
            const result = manager.callComponent(compName, compId, inputHash);
            const isPromise = `${result}` === '[object Promise]';

            // Wrap the whole response in Promise, so we can add extra fields
            return Promise.resolve(result).then((res) => ({
              result: res,
              isPromise,
            }));
        }"""

        data = await page.evaluate(test_js)

        assert data["result"] == 123
        assert data["isPromise"] is True

        await page.close()

    @with_playwright
    async def test_error_in_component_call_do_not_propagate_sync(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-12345> abc </div>');

            manager.registerComponent(compName, (data, ctx) => {
                throw Error('Oops!');
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = manager.callComponent(compName, compId, inputHash);

            return result;
        }"""

        data = await page.evaluate(test_js)

        assert data is None

        await page.close()

    @with_playwright
    async def test_error_in_component_call_do_not_propagate_async(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-12345> abc </div>');

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
    async def test_raises_if_component_element_not_in_dom(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            manager.registerComponent(compName, (data, ctx) => {
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should raise Error
            manager.callComponent(compName, compId, inputHash);
        }"""

        with pytest.raises(
            Error,
            match=re.escape("Error: [Components] 'my_comp': No elements with component ID '12345' found"),
        ):
            await page.evaluate(test_js)

        await page.close()

    @with_playwright
    async def test_raises_if_input_hash_not_registered(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-12345> abc </div>');

            manager.registerComponent(compName, (data, ctx) => {
                return Promise.resolve(123);
            });

            // Should raise Error
            manager.callComponent(compName, compId, inputHash);
        }"""

        with pytest.raises(
            Error,
            match=re.escape("Error: [Components] 'my_comp': Cannot find input for hash 'input-abc'"),
        ):
            await page.evaluate(test_js)

        await page.close()

    @with_playwright
    async def test_raises_if_component_not_registered(self):
        page = await _create_page_with_dep_manager(self.browser)  # type: ignore[attr-defined]

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            document.body.insertAdjacentHTML('beforeend', '<div data-djc-id-12345> abc </div>');

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should raise Error
            manager.callComponent(compName, compId, inputHash);
        }"""

        with pytest.raises(
            Error,
            match=re.escape("Error: [Components] 'my_comp': No component registered for that name"),
        ):
            await page.evaluate(test_js)

        await page.close()
