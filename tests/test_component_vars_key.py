"""Each distinct value from `get_js_data()` and `get_css_data()` must get its own stored entry."""

import base64
import enum
import hashlib
import json
import logging
import re

import pytest
from django.conf import settings
from django.test import Client, override_settings
from django.utils.crypto import salted_hmac

from django_components import Component, render_dependencies, types
from django_components import dependencies as dependencies_module
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


# Written out here rather than imported, so a change to the label or the algorithm fails these tests.
KEY_LABEL = "django_components.dependencies.variables-name"


def _new_key(data: dict, secret: str | None = None) -> str:
    secret = settings.SECRET_KEY if secret is None else secret
    return salted_hmac(KEY_LABEL, json.dumps(data), secret=secret, algorithm="sha256").hexdigest()[:32]


def _plain_key(data: dict) -> str:
    # The key that anyone could calculate from a guess, without the secret.
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()[:32]


# Made-up secrets for the tests that change SECRET_KEY.
OLD_SECRET_KEY = "old-secret-key"  # noqa: S105
NEW_SECRET_KEY = "new-secret-key"  # noqa: S105
WRONG_SECRET_KEY = "wrong-secret-key"  # noqa: S105

SHARED_CACHE_SETTINGS = {
    "CACHES": {
        "shared": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "vars-key-shared",
        },
    },
}


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

    def test_the_css_key_is_an_hmac_under_the_secret_key(self):
        data = {"note": "x"}
        assert cache_component_css_vars(_make_css_component(), data) == _new_key(data)

    def test_the_js_key_is_an_hmac_under_the_secret_key(self):
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

    def test_the_route_sends_no_cors_header(self):
        # The docs say that other sites can still load the URL with a tag, but cannot read it with fetch().
        # The 404 counts too, as with that header another site could read which URLs exist.
        comp_cls = _make_css_component()
        url = _vars_url(comp_cls, {"note": "shared"}, "css")
        client = Client()
        found = client.get(url, headers={"Origin": "https://other.example"})
        missing = client.get(
            f"/components/cache/{comp_cls.class_id}.{'0' * 32}.css", headers={"Origin": "https://other.example"}
        )
        assert found.status_code == 200
        assert missing.status_code == 404
        assert "Access-Control-Allow-Origin" not in found.headers
        assert "Access-Control-Allow-Origin" not in missing.headers

    @pytest.mark.parametrize(
        ("make_component", "ext"),
        [(_make_css_component, "css"), (_make_js_component, "js")],
    )
    def test_a_guess_of_the_values_cannot_be_checked_without_the_secret_key(self, make_component, ext):
        # Without `SECRET_KEY`, anyone could calculate the URL for values they guessed, and a 200 would
        # confirm the guess. A short unknown field could then be found by trying each option.
        comp_cls = make_component()
        data = {"note": "x"}
        page_url = _vars_url(comp_cls, data, ext)
        client = Client()
        assert client.get(page_url).status_code == 200

        # The values are guessed right, but the key is calculated without `SECRET_KEY` or with a wrong one.
        for guessed_key in (_plain_key(data), _new_key(data, secret=""), _new_key(data, secret=WRONG_SECRET_KEY)):
            assert guessed_key not in page_url
            assert client.get(f"/components/cache/{comp_cls.class_id}.{guessed_key}.{ext}").status_code == 404


@djc_test
class TestVariablesKeyAndSecretKey:
    """The key comes from `SECRET_KEY`, so changing or leaving out `SECRET_KEY` must not break pages."""

    @pytest.mark.parametrize(
        ("make_component", "ext"),
        [(_make_css_component, "css"), (_make_js_component, "js")],
    )
    def test_a_url_made_before_a_secret_key_change_keeps_working(self, make_component, ext):
        comp_cls = make_component()
        data = {"note": "rotated"}
        with override_settings(SECRET_KEY=OLD_SECRET_KEY):
            old_url = _vars_url(comp_cls, data, ext)

        # Django's way to change `SECRET_KEY`: set the new value and list the old one in `SECRET_KEY_FALLBACKS`.
        with override_settings(SECRET_KEY=NEW_SECRET_KEY, SECRET_KEY_FALLBACKS=[OLD_SECRET_KEY]):
            new_url = _vars_url(comp_cls, data, ext)
            client = Client()
            # A page rendered before the change, or kept in a cache, still gets its values.
            assert client.get(old_url).status_code == 200
            assert client.get(new_url).status_code == 200
        assert old_url != new_url
        assert _new_key(data, secret=OLD_SECRET_KEY) in old_url
        assert _new_key(data, secret=NEW_SECRET_KEY) in new_url

    @pytest.mark.parametrize(
        ("make_component", "ext"),
        [(_make_css_component, "css"), (_make_js_component, "js")],
    )
    def test_an_empty_secret_key_does_not_break_renders(self, make_component, ext):
        # Django raises when code reads an empty SECRET_KEY, so reading it carelessly here would
        # make every render with these values fail in projects that leave it empty.
        comp_cls = make_component()
        data = {"note": "no-secret"}
        with override_settings(SECRET_KEY=""):
            url = _vars_url(comp_cls, data, ext)
            assert Client().get(url).status_code == 200
        # Everyone knows an empty secret, so the key must not be made with it.
        assert _plain_key(data) not in url
        assert _new_key(data, secret="") not in url

    @djc_test(components_settings={"cache": "shared"}, django_settings=SHARED_CACHE_SETTINGS)
    def test_with_an_empty_secret_key_each_process_finds_the_names_of_the_others(self, monkeypatch):
        # Each process makes its own secret, so two processes calculate different keys for the same values.
        # The route only looks a key up in the shared cache, so both keys keep working.
        comp_cls = _make_css_component()
        data = {"note": "two-processes"}
        with override_settings(SECRET_KEY=""):
            first_url = _vars_url(comp_cls, data, "css")
            monkeypatch.setattr(dependencies_module, "_PROCESS_VARIABLES_SECRET", "another-process")
            second_url = _vars_url(comp_cls, data, "css")
            client = Client()
            assert first_url != second_url
            assert client.get(first_url).status_code == 200
            assert client.get(second_url).status_code == 200


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
