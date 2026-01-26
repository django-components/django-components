"""
End-to-end tests for CSS variables feature.

These tests verify that CSS variables from `get_css_data()` work correctly
in a real browser environment.
"""

import re
from typing import TYPE_CHECKING

from django_components.testing import djc_test
from tests.e2e.utils import TEST_SERVER_URL, with_playwright
from tests.testutils import setup_test_config

if TYPE_CHECKING:
    from playwright.async_api import Browser

    from django_components import types
    from tests.e2e.utils import BrowserType

setup_test_config()


# NOTE: All views, components, and associated JS and CSS are defined in
# `tests/e2e/testserver/testserver`
@djc_test
class TestE2eCssVariables:
    @with_playwright
    async def test_css_variables_multiple_instances_different_values(
        self,
        browser: "Browser",
        browser_name: "BrowserType",
    ):
        url = TEST_SERVER_URL + "/css-vars/multiple"

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

            const redHash = getCssHash(boxRed);
            const greenHash = getCssHash(boxGreen);
            const blueHash = getCssHash(boxBlue);

            return {
                redBg,
                greenBg,
                blueBg,
                redHash,
                greenHash,
                blueHash,
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
    async def test_css_variables_sized_box(self, browser: "Browser", browser_name: "BrowserType"):
        url = TEST_SERVER_URL + "/css-vars/sized"

        page = await browser.new_page()
        await page.goto(url)

        test_js: types.js = """() => {
            const box = document.querySelector('#sized-box .sized-box');

            if (!box) {
                return {
                    width: null,
                    height: null,
                    bgColor: null,
                    cssHash: null,
                };
            }

            const width = globalThis.getComputedStyle(box).getPropertyValue('width');
            const height = globalThis.getComputedStyle(box).getPropertyValue('height');
            const bgColor = globalThis.getComputedStyle(box).getPropertyValue('background-color');

            // Extract CSS variable hash from data-djc-css-{hash} attribute
            let cssHash = null;
            for (let i = 0; i < box.attributes.length; i++) {
                const attr = box.attributes[i];
                if (attr.name.startsWith('data-djc-css-')) {
                    cssHash = attr.name.replace('data-djc-css-', '');
                    break;
                }
            }

            return {
                width,
                height,
                bgColor,
                cssHash,
            };
        }"""

        data = await page.evaluate(test_js)

        # Verify dimensions are set correctly via CSS variables
        assert data["width"] == "200px"
        assert data["height"] == "150px"

        # Verify background color is set via CSS variable
        # The color #0275d8 is a blue color, should render as rgb(2, 117, 216)
        assert "rgb(2, 117, 216)" in data["bgColor"] or "#0275d8" in data["bgColor"].lower()

        # Verify CSS variable hash is present
        assert data["cssHash"] is not None
        assert re.match(r"^[a-f0-9]{6}$", data["cssHash"]) is not None

        await page.close()
