from djc_core_html_parser import set_html_attributes
from pytest_django.asserts import assertHTMLEqual

from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


# This same set of tests is also found in djc_html_parser, to ensure that
# this implementation can be replaced with the djc_html_parser's Rust-based implementation
@djc_test
class TestHTMLParser:
    def test_basic_transformation(self):
        html = "<div><p>Hello</p></div>"
        result, _ = set_html_attributes(html, root_attributes=["data-root"], all_attributes=["data-all"])

        assertHTMLEqual(
            result,
            """
            <div data-root data-all>
                <p data-all>Hello</p>
            </div>
            """,
        )

    def test_multiple_roots(self):
        html = "<div>First</div><span>Second</span>"
        result, _ = set_html_attributes(html, root_attributes=["data-root"], all_attributes=["data-all"])

        assertHTMLEqual(
            result,
            """
            <div data-root data-all>First</div>
            <span data-root data-all>Second</span>
            """,
        )

    def test_complex_html(self):
        html = """
            <div class="container" id="main">
                <header class="flex">
                    <h1 title="Main Title">Hello & Welcome</h1>
                    <nav data-existing="true">
                        <a href="/home">Home</a>
                        <a href="/about" class="active">About</a>
                    </nav>
                </header>
                <main>
                    <article data-existing="true">
                        <h2>Article 1</h2>
                        <p>Some text with <strong>bold</strong> and <em>emphasis</em></p>
                        <img src="test.jpg" alt="Test Image"/>
                    </article>
                </main>
            </div>
            <footer id="footer">
                <p>&copy; 2024</p>
            </footer>
        """

        result, _ = set_html_attributes(html, ["data-root"], ["data-all", "data-v-123"])

        expected = """
            <div class="container" id="main" data-root data-all data-v-123>
                <header class="flex" data-all data-v-123>
                    <h1 title="Main Title" data-all data-v-123>Hello & Welcome</h1>
                    <nav data-existing="true" data-all data-v-123>
                        <a href="/home" data-all data-v-123>Home</a>
                        <a href="/about" class="active" data-all data-v-123>About</a>
                    </nav>
                </header>
                <main data-all data-v-123>
                    <article data-existing="true" data-all data-v-123>
                        <h2 data-all data-v-123>Article 1</h2>
                        <p data-all data-v-123>Some text with <strong data-all data-v-123>bold</strong> and <em data-all data-v-123>emphasis</em></p>
                        <img src="test.jpg" alt="Test Image" data-all data-v-123/>
                    </article>
                </main>
            </div>
            <footer id="footer" data-root data-all data-v-123>
                <p data-all data-v-123>&copy; 2024</p>
            </footer>
        """  # noqa: E501
        assertHTMLEqual(result, expected)

    def test_void_elements(self):
        test_cases = [
            ('<meta charset="utf-8">', '<meta charset="utf-8" data-root data-v-123>'),
            ('<meta charset="utf-8"/>', '<meta charset="utf-8" data-root data-v-123/>'),
            ("<div><br><hr></div>", "<div data-root data-v-123><br data-v-123><hr data-v-123></div>"),
            ('<img src="test.jpg" alt="Test">', '<img src="test.jpg" alt="Test" data-root data-v-123>'),
        ]

        for input_html, expected in test_cases:
            result, _ = set_html_attributes(input_html, ["data-root"], ["data-v-123"])
            assertHTMLEqual(result, expected)

    def test_html_head_with_meta(self):
        html = """
            <head>
                <meta charset="utf-8">
                <title>Test Page</title>
                <link rel="stylesheet" href="style.css">
                <meta name="description" content="Test">
            </head>"""

        result, _ = set_html_attributes(html, ["data-root"], ["data-v-123"])

        assertHTMLEqual(
            result,
            """
            <head data-root data-v-123>
                <meta charset="utf-8" data-v-123>
                <title data-v-123>Test Page</title>
                <link rel="stylesheet" href="style.css" data-v-123>
                <meta name="description" content="Test" data-v-123>
            </head>
            """,
        )

    def test_watch_attribute(self):
        html = """
            <div data-id="123">
                <p>Regular element</p>
                <span data-id="456">Nested element</span>
                <img data-id="789" src="test.jpg"/>
            </div>"""

        result, captured = set_html_attributes(html, ["data-root"], ["data-v-123"], watch_on_attribute="data-id")

        assertHTMLEqual(
            result,
            """
            <div data-id="123" data-root data-v-123>
                <p data-v-123>Regular element</p>
                <span data-id="456" data-v-123>Nested element</span>
                <img data-id="789" src="test.jpg" data-v-123/>
            </div>
            """,
        )

        # Verify attribute capturing
        assert len(captured) == 3

        # Root element should have both root and all attributes
        assert captured["123"] == ["data-root", "data-v-123"]

        # Non-root elements should only have all attributes
        assert captured["456"] == ["data-v-123"]
        assert captured["789"] == ["data-v-123"]

    def test_whitespace_preservation(self):
        html = """<div>
            <p>  Hello  World  </p>
            <span> Text with spaces </span>
        </div>"""

        result, _ = set_html_attributes(html, ["data-root"], ["data-all"])
        expected = """<div data-root="" data-all="">
            <p data-all="">  Hello  World  </p>
            <span data-all=""> Text with spaces </span>
        </div>"""

        assert result == expected
