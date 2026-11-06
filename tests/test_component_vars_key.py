"""Each distinct value from `get_js_data()` and `get_css_data()` must get its own stored entry."""

import base64
import enum
import hashlib
import json
import logging
import re

import pytest
from django.test import Client

from django_components import Component, render_dependencies, types
from django_components.cache import get_component_vars_cache
from django_components.dependencies import (
    Style,
    cache_component_css_vars,
    cache_component_js_vars,
)
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()

# Each pair shares the first 6 characters of its MD5, the key that older versions used.
# Finding such a pair took about 4,000 to 9,000 made-up values.
CSS_PAIR = ({"note": "css-value-1865"}, {"note": "css-value-8634"})
JS_PAIR = ({"note": "js-value-773"}, {"note": "js-value-3813"})


class Color(str, enum.Enum):
    RED = "red"


def _make_css_component() -> type[Component]:
    class CssNote(Component):
        template: types.django_html = """
            <div>x</div>
        """
        css: types.css = """
            div { color: var(--note); }
        """

        def get_css_data(self, args, kwargs, slots, context):
            return kwargs["data"]

    return CssNote


def _make_js_component() -> type[Component]:
    class JsNote(Component):
        template: types.django_html = """
            <div>x</div>
        """
        js: types.js = """
            $onComponent(({ note }) => { console.log(note); });
        """

        def get_js_data(self, args, kwargs, slots, context):
            return kwargs["data"]

    return JsNote


def _old_key(data: dict) -> str:
    # This is the key that the pairs above are known to share, so MD5 is the point here.
    return hashlib.md5(json.dumps(data).encode()).hexdigest()[:6]  # noqa: S324


def _new_key(data: dict) -> str:
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()[:32]


def _vars_url(comp_cls: type[Component], data: dict, ext: str) -> str:
    # With the fragment strategy the browser loads the variables by URL, which is
    # what happens to a visitor, so this reads the URL from the page and not from a helper.
    html = comp_cls.render(kwargs={"data": data}, deps_strategy="fragment")
    payload = re.search(r'<script type="application/json" data-djc>(.*?)</script>', html, re.DOTALL)
    assert payload is not None
    tags = [base64.b64decode(tag).decode() for tag in json.loads(payload.group(1))[f"{ext}Tags__toFetch"]]
    url_re = rf"/components/cache/{re.escape(comp_cls.class_id)}\.[0-9a-f]+\.{ext}"
    urls = [match.group(0) for match in (re.search(url_re, tag) for tag in tags) if match]
    assert len(urls) == 1
    return urls[0]


def _holds(body: bytes, data: dict) -> bool:
    # A CSS file has the value as text, and a JS file has the JSON in base64.
    return data["note"].encode() in body or base64.b64encode(json.dumps(data).encode()) in body


@djc_test
class TestVariablesKey:
    @pytest.mark.parametrize(
        ("make_component", "pair", "ext"),
        [(_make_css_component, CSS_PAIR, "css"), (_make_js_component, JS_PAIR, "js")],
    )
    def test_values_that_shared_a_short_key_do_not_share_an_entry(self, make_component, pair, ext):
        first, second = pair
        # Without this the test would pass on any two values.
        assert _old_key(first) == _old_key(second)

        comp_cls = make_component()
        first_url = _vars_url(comp_cls, first, ext)
        second_url = _vars_url(comp_cls, second, ext)
        assert first_url != second_url

        # Each page must get its own value and nothing of the other visitor's.
        client = Client()
        first_body = client.get(first_url).content
        second_body = client.get(second_url).content
        assert _holds(first_body, first)
        assert not _holds(first_body, second)
        assert _holds(second_body, second)
        assert not _holds(second_body, first)

    def test_the_css_key_is_the_start_of_a_sha256(self):
        data = {"note": "x"}
        assert cache_component_css_vars(_make_css_component(), data) == _new_key(data)

    def test_the_js_key_is_the_start_of_a_sha256(self):
        data = {"note": "x"}
        assert cache_component_js_vars(_make_js_component(), data) == _new_key(data)

    def test_the_key_stays_inside_what_the_route_accepts(self):
        # If the route refused a key, every page would lose its variables, and the only sign would be 404s.
        url = _vars_url(_make_css_component(), {"note": "x"}, "css")
        assert len(url.rsplit(".", 2)[1]) == 32
        assert Client().get(url).status_code == 200

    @pytest.mark.parametrize(
        ("first", "second"),
        [
            ({"note": Color.RED}, {"note": "red"}),
            ({"note": "red"}, {"note": Color.RED}),
            ({True: "red"}, {"true": "red"}),
            ({"true": "red"}, {True: "red"}),
        ],
    )
    def test_values_with_the_same_json_get_the_same_text(self, first, second):
        # These share a key, so which one renders first must not change what the stylesheet says.
        comp_cls = _make_css_component()
        first_url = _vars_url(comp_cls, first, "css")
        assert first_url == _vars_url(comp_cls, second, "css")
        assert b": red;" in Client().get(first_url).content
        assert b"Color.RED" not in Client().get(first_url).content
        assert b"--True" not in Client().get(first_url).content

    def test_equal_values_share_one_entry(self):
        # The entry is shared on purpose, as instances with the same values need only one file.
        comp_cls = _make_css_component()
        data = {"note": "same"}
        assert _vars_url(comp_cls, data, "css") == _vars_url(comp_cls, data, "css")

    def test_the_same_values_in_another_component_are_a_separate_entry(self):
        class OtherNote(_make_css_component()):  # type: ignore[misc]
            pass

        data = {"note": "same"}
        assert _vars_url(_make_css_component(), data, "css") != _vars_url(OtherNote, data, "css")


@djc_test
class TestVariablesRouteIsPublic:
    """The URL needs no login. The docs say so, so a change here must change them too."""

    def test_anyone_with_the_url_reads_the_entry(self):
        url = _vars_url(_make_css_component(), {"note": "shared"}, "css")
        # A new client has no cookie and no session.
        response = Client().get(url)
        assert response.status_code == 200
        assert b"shared" in response.content

    def test_a_guess_of_the_values_can_be_checked(self):
        # The docs warn app authors about this. A hit confirms a guess, so with a short
        # unknown field, trying each option reveals that field.
        comp_cls = _make_css_component()
        comp_cls.render(kwargs={"data": {"note": "x"}})
        client = Client()
        right = client.get(f"/components/cache/{comp_cls.class_id}.{_new_key({'note': 'x'})}.css")
        wrong = client.get(f"/components/cache/{comp_cls.class_id}.{_new_key({'note': 'y'})}.css")
        assert right.status_code == 200
        assert wrong.status_code == 404


@djc_test
class TestKeysFromOlderVersions:
    """HTML in `{% cache %}` or a shared cache can outlive an upgrade and name a short key."""

    OLD_KEY = "a5dfa7"

    def _old_html(self, comp_cls: type[Component]) -> str:
        return f"<!-- _RENDERED {comp_cls.class_id},cabc123,,{self.OLD_KEY} --><div>x</div>"

    def test_html_with_a_short_key_whose_entry_is_gone_still_renders(self, caplog):
        comp_cls = _make_css_component()
        with caplog.at_level(logging.WARNING, logger="django_components"):
            rendered = render_dependencies(self._old_html(comp_cls), strategy="fragment")
        assert "<div>x</div>" in rendered
        assert "CSS variables of component" in caplog.text

    def test_an_entry_under_a_short_key_is_still_served(self):
        # The changelog tells apps with a shared cache to clear it after an upgrade because of this.
        comp_cls = _make_css_component()
        style = Style(
            kind="variables",
            content="[x] { --note: old; }",
            attrs={},
            origin_class_id=comp_cls.class_id,
        )
        # Written out in full, as an older version wrote it, so this stays a test of an old entry
        # if `_gen_cache_key()` changes.
        cache_key = f"__components:{comp_cls.class_id}:css:{self.OLD_KEY}"
        get_component_vars_cache().set(cache_key, json.dumps(style.to_json()))
        assert Client().get(f"/components/cache/{comp_cls.class_id}.{self.OLD_KEY}.css").status_code == 200
