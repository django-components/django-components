"""Requests and rendered data must not cost the server more work or memory than their size justifies."""

import itertools
import logging
import re
import sys
import time
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from django.core.cache import caches
from django.test import Client, override_settings
from django.urls import Resolver404, resolve, reverse

from django_components import Component, types
from django_components.app_settings import InternalSettings
from django_components.attributes import _split_style_declarations, parse_string_style, style_comment_re
from django_components.cache import (
    _VARS_ENTRY_OVERHEAD_BYTES,
    ComponentVarsCache,
    get_component_media_cache,
    get_component_vars_cache,
)
from django_components.dependencies import CACHE_ENDPOINT_NAME
from django_components.dependencies import urlpatterns as dependency_urlpatterns
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


def _make_component() -> type[Component]:
    class CachedComp(Component):
        template: types.django_html = """
            <div>x</div>
        """
        css: types.css = """
            .c { color: var(--col); }
        """
        js: types.js = """
            console.log("c");
        """

        class Kwargs:
            col: str = "red"

        def get_css_data(self, args, kwargs, slots, context):
            return {"col": kwargs.col}

    return CachedComp


def _vars_url(comp_cls: type[Component], rendered: str) -> str:
    """Get the URL of the variables stylesheet, by looking up the only variables entry."""
    keys = [key for key in get_component_vars_cache()._entries if f":{comp_cls.class_id}:" in key]  # type: ignore[attr-defined]
    assert len(keys) == 1
    variables_hash = keys[0].rsplit(":", 1)[1]
    assert variables_hash in rendered
    return f"/components/cache/{comp_cls.class_id}.{variables_hash}.css"


@djc_test
class TestCacheRoute:
    def test_each_route_has_one_open_ended_part(self):
        # Two open-ended parts make the regex engine try every way to split a path between them,
        # which is what made a long path slow. This reads the pattern instead of timing a request,
        # because a regression here would take minutes to show up as a slow test.
        for url_pattern in dependency_urlpatterns:
            regex = url_pattern.pattern.regex.pattern
            assert regex.count("+") + regex.count("*") == 1, regex

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("Table_a1b2c3.js", {"comp_cls_id": "Table_a1b2c3", "script_type": "js"}),
            ("Table_a1b2c3.css", {"comp_cls_id": "Table_a1b2c3", "script_type": "css"}),
            (
                "Table_a1b2c3.0ab2c3.js",
                {"comp_cls_id": "Table_a1b2c3", "variables_hash": "0ab2c3", "script_type": "js"},
            ),
            # The hash can grow up to 64 hexadecimal characters without a change to the route.
            (
                f"Table_a1b2c3.{'0' * 32}.css",
                {"comp_cls_id": "Table_a1b2c3", "variables_hash": "0" * 32, "script_type": "css"},
            ),
            (
                f"Table_a1b2c3.{'f' * 64}.js",
                {"comp_cls_id": "Table_a1b2c3", "variables_hash": "f" * 64, "script_type": "js"},
            ),
            # A class ID comes from the class name, which a dynamically created class can fill with anything.
            ("a.b_a1b2c3.js", {"comp_cls_id": "a.b_a1b2c3", "script_type": "js"}),
            (
                "a.b_a1b2c3.0ab2c3.css",
                {"comp_cls_id": "a.b_a1b2c3", "variables_hash": "0ab2c3", "script_type": "css"},
            ),
        ],
    )
    def test_routes_match_and_reverse(self, path, expected):
        url = f"/components/cache/{path}"
        assert resolve(url).kwargs == expected
        assert reverse(CACHE_ENDPOINT_NAME, kwargs=expected) == url

    @pytest.mark.parametrize(
        "path",
        [
            "Table_a1b2c3",
            "Table_a1b2c3.",
            ".js",
            "Table_a1b2c3.html",
            "Table_a1b2c3.js/",
            "Table_a1b2c3.js\n",
            "Table_a1b2c3.0ab2c3.css\n",
            "Table_a1b2c3.0AB2C3X.html",
            f"Table_a1b2c3.{'0' * 65}.xx",
        ],
    )
    def test_routes_reject_other_paths(self, path):
        with pytest.raises(Resolver404):
            resolve(f"/components/cache/{path}")

    @pytest.mark.parametrize(
        "path",
        [
            "." * 1600 + "/",
            "a." * 800 + "/",
            "a" * 3200 + ".",
            "." + "a" * 3200 + ".",
        ],
    )
    def test_long_paths_that_never_match_get_404(self, path):
        assert Client().get(f"/components/cache/{path}").status_code == 404

    @pytest.mark.parametrize(
        "hash_part",
        [
            # Longer than the 250 characters that Django warns about in a cache key.
            "a" * 2000,
            # Upper case and non-hexadecimal characters are never generated.
            "ZZZ",
            "0AB2C3",
            "0ab2c3%0a",
        ],
    )
    def test_made_up_hash_never_reaches_the_cache(self, hash_part):
        # Python keeps every distinct warning message it has shown, so a warning that repeats
        # a made-up key would let each request add to the process's memory for good.
        comp_cls = _make_component()
        comp_cls.render()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            response = Client().get(f"/components/cache/{comp_cls.class_id}.{hash_part}.css")
        assert response.status_code == 404

    def test_cached_scripts_are_served(self):
        comp_cls = _make_component()
        comp_cls.render()
        client = Client()
        assert client.get(f"/components/cache/{comp_cls.class_id}.js").status_code == 200
        assert client.get(f"/components/cache/{comp_cls.class_id}.css").status_code == 200


@djc_test
class TestStyleParsing:
    def test_an_unclosed_comment_is_one_match(self):
        # The cost of the slow case was the regex searching to the end of the text again from
        # every `/*`. One match that reaches the end means no later `/*` is tried at all.
        assert len(style_comment_re.findall("/* " * 1000)) == 1

    @pytest.mark.parametrize(
        ("css_text", "expected"),
        [
            ("a: 1; /* x */ b: 2", {"a": "1", "b": "2"}),
            ("a: 1 /* x */ /* y */; b: 2", {"a": "1", "b": "2"}),
            # Nothing closes these, so the text stays, as it did before.
            ("a: 1 /* open", {"a": "1 /* open"}),
            ("a: 1 /* open /* again; b: 2", {"a": "1 /* open /* again", "b": "2"}),
            ("/* closed */ a: 1 /* open", {"a": "1 /* open"}),
            ("a: /*/", {"a": "/*/"}),
            ("a: /*/ */ b", {"a": "b"}),
            # `/*/*/` closes itself, and a run of `/*` is a run of short comments.
            ("/*/*/a: 1", {"a": "1"}),
            ("a: url(data:image/png;base64,AA==); b: 2", {"a": "url(data:image/png;base64,AA==)", "b": "2"}),
        ],
    )
    def test_comments_and_delimiters(self, css_text, expected):
        assert parse_string_style(css_text) == expected

    def test_split_follows_the_regex_rule(self):
        # Every short string over the characters that matter, against the rule we replaced.
        rule = re.compile(r";(?![^(]*\))", re.DOTALL)
        for length in range(6):
            for chars in itertools.product(";()a\n", repeat=length):
                text = "".join(chars)
                assert _split_style_declarations(text) == rule.split(text), repr(text)

    @pytest.mark.parametrize(
        "css_text",
        [
            ";" * 240_000,
            ";" * 240_000 + ")",
            "a;" * 120_000,
            "/* " * 80_000,
        ],
    )
    def test_long_values_stay_quick(self, css_text):
        # This one does use the clock, as nothing else can see the time a plain walk takes.
        # These sizes took 15 to 40 seconds with the old regexes and take well under 0.1 seconds now,
        # so the limit leaves a wide margin for a slow machine.
        start = time.perf_counter()
        parse_string_style(css_text)
        assert time.perf_counter() - start < 5


class FakeClock:
    """A clock that a test moves by hand, so that entries can expire without the test having to wait."""

    def __init__(self) -> None:
        self.now = 1000.0


@contextmanager
def fake_clock() -> Iterator[FakeClock]:
    clock = FakeClock()
    with patch("time.time", lambda: clock.now):
        yield clock


def _entry_size(cache: ComponentVarsCache, key: str, value: str) -> int:
    return sys.getsizeof(cache.make_key(key)) + sys.getsizeof(value) + _VARS_ENTRY_OVERHEAD_BYTES


class TestComponentVarsCache:
    def test_entries_stay_within_the_byte_limit(self):
        cache = ComponentVarsCache(max_age=3600, max_bytes=10_000)
        for index in range(100):
            cache.set(f"k{index:02d}", "x" * 500)
        assert cache._total_bytes <= 10_000
        # The newest entries are the ones kept.
        assert cache.get("k99") == "x" * 500
        assert cache.get("k00") is None

    def test_an_entry_a_render_used_recently_is_kept_longer(self):
        value = "x" * 100
        cache = ComponentVarsCache(max_age=3600, max_bytes=3 * _entry_size(ComponentVarsCache(1, 1), "k0", value))
        for index in range(3):
            cache.set(f"k{index}", value)
        assert cache.has_key("k0")
        cache.set("k3", value)
        assert cache.get("k0") == value
        assert cache.get("k1") is None

    def test_reading_an_entry_does_not_keep_it(self):
        # Anyone can request a stored file, and that must not keep it in memory.
        value = "x" * 100
        cache = ComponentVarsCache(max_age=3600, max_bytes=3 * _entry_size(ComponentVarsCache(1, 1), "k0", value))
        for index in range(3):
            cache.set(f"k{index}", value)
        assert cache.get("k0") == value
        cache.set("k3", value)
        assert cache.get("k0") is None

        with fake_clock() as clock:
            cache = ComponentVarsCache(max_age=10, max_bytes=10_000)
            cache.set("k", "v")
            clock.now += 6
            assert cache.get("k") == "v"
            clock.now += 6
            assert cache.get("k") is None

    def test_an_expired_entry_is_gone(self):
        with fake_clock() as clock:
            cache = ComponentVarsCache(max_age=10, max_bytes=10_000)
            cache.set("k", "v")
            clock.now += 9
            assert cache.get("k") == "v"
            clock.now += 1
            assert cache.get("k") is None
            assert not cache.has_key("k")
            assert cache._total_bytes == 0

    def test_a_write_removes_expired_entries_nobody_reads(self):
        # Most values are stored once and never read again, so expiry cannot wait for a read.
        with fake_clock() as clock:
            cache = ComponentVarsCache(max_age=10, max_bytes=1_000_000)
            for index in range(100):
                cache.set(f"k{index}", "v")
            clock.now += 11
            cache.set("new", "v")
            assert list(cache._entries) == [cache.make_key("new")]
            assert cache._total_bytes == _entry_size(cache, "new", "v")

    def test_a_render_renews_the_age_of_an_entry(self):
        # Without this, an entry in steady use would expire right after a render linked it.
        with fake_clock() as clock:
            cache = ComponentVarsCache(max_age=10, max_bytes=10_000)
            cache.set("k", "v")
            for _ in range(5):
                clock.now += 9
                assert cache.has_key("k")
            assert cache.get("k") == "v"

    def test_a_renewed_entry_does_not_hide_later_expired_entries(self):
        with fake_clock() as clock:
            cache = ComponentVarsCache(max_age=10, max_bytes=1_000_000)
            cache.set("renewed", "v")
            cache.set("left", "v")
            clock.now += 5
            cache.has_key("renewed")
            clock.now += 6
            cache.set("new", "v")
            assert set(cache._entries) == {cache.make_key("renewed"), cache.make_key("new")}

    def test_the_byte_count_follows_rewrites_deletes_and_clear(self):
        cache = ComponentVarsCache(max_age=3600, max_bytes=1_000_000)
        cache.set("a", "x" * 100)
        cache.set("a", "x" * 50)
        cache.set("b", "x" * 10)
        assert cache.delete("b")
        assert not cache.delete("b")
        assert cache._total_bytes == _entry_size(cache, "a", "x" * 50)
        cache.clear()
        assert cache._total_bytes == 0
        assert cache.get("a") is None

    def test_add_writes_only_a_new_key(self):
        cache = ComponentVarsCache(max_age=3600, max_bytes=1_000_000)
        assert cache.add("k", "first")
        assert not cache.add("k", "second")
        assert cache.get("k") == "first"

    def test_touch_on_a_missing_key(self):
        assert not ComponentVarsCache(max_age=3600, max_bytes=10_000).touch("k")

    def test_get_gives_the_default_for_a_missing_key(self):
        assert ComponentVarsCache(max_age=3600, max_bytes=10_000).get("k", "fallback") == "fallback"

    def test_an_entry_larger_than_the_limit_is_not_stored(self, caplog):
        cache = ComponentVarsCache(max_age=3600, max_bytes=1_000)
        cache.set("other", "kept")
        cache.set("k", "small")
        with caplog.at_level(logging.WARNING, logger="django_components"):
            cache.set("k", "secret" * 1000)
        # The old value is gone too, as it is not what the render asked to store.
        assert cache.get("k") is None
        # Refusing it must not first empty the store to make room.
        assert cache.get("other") == "kept"
        assert "vars_cache_max_bytes" in caplog.text
        assert "secret" not in caplog.text

    def test_wide_characters_count_the_memory_they_really_take(self):
        # One character above U+FFFF makes CPython store the whole string at four bytes per character.
        cache = ComponentVarsCache(max_age=3600, max_bytes=10_000_000)
        assert _entry_size(cache, "k", "x" * 9_999 + "\U0001f600") > 3 * _entry_size(cache, "k", "x" * 10_000) - 1_000


class TestVarsCacheSettings:
    @pytest.mark.parametrize("name", ["vars_cache_max_age", "vars_cache_max_bytes"])
    @pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "1", sys.maxsize + 1, [1]])
    def test_invalid_values_are_rejected(self, name, value):
        with override_settings(COMPONENTS={name: value}), pytest.raises(ValueError, match=f"COMPONENTS.{name}"):
            InternalSettings()._load_settings()

    @pytest.mark.parametrize("name", ["vars_cache_max_age", "vars_cache_max_bytes"])
    @pytest.mark.parametrize("value", [1, sys.maxsize])
    def test_values_in_range_are_kept(self, name, value):
        internal_settings = InternalSettings()
        with override_settings(COMPONENTS={name: value}):
            internal_settings._load_settings()
        assert getattr(internal_settings._settings, name) == value

    def test_defaults(self):
        internal_settings = InternalSettings()
        with override_settings(COMPONENTS={"vars_cache_max_age": None}):
            internal_settings._load_settings()
        assert internal_settings._settings.vars_cache_max_age == 86400
        assert internal_settings._settings.vars_cache_max_bytes == 64 * 1024 * 1024


@djc_test
class TestVarsCacheInRendering:
    @djc_test(components_settings={"vars_cache_max_bytes": 20_000})
    def test_many_distinct_values_stay_within_the_limit(self):
        comp_cls = _make_component()
        for index in range(300):
            comp_cls.render(kwargs={"col": f"{index}-" + "x" * 1000})
        cache = get_component_vars_cache()
        assert isinstance(cache, ComponentVarsCache)
        assert 0 < cache._total_bytes <= 20_000
        assert len(cache._entries) < 20

    @djc_test(components_settings={"vars_cache_max_bytes": 5_000})
    def test_many_distinct_values_do_not_push_out_component_scripts(self):
        # The JS and CSS of a component are what every page needs. Only a later render of
        # that same component would store them again, so a flood must not be able to remove them.
        comp_cls = _make_component()
        comp_cls.render()
        for index in range(100):
            comp_cls.render(kwargs={"col": f"{index}-" + "x" * 500})

        media_cache = get_component_media_cache()
        assert media_cache.has_key(f"__components:{comp_cls.class_id}:js")
        assert media_cache.has_key(f"__components:{comp_cls.class_id}:css")
        assert Client().get(f"/components/cache/{comp_cls.class_id}.css").status_code == 200

    @djc_test(components_settings={"vars_cache_max_age": 100})
    def test_variables_expire_and_come_back_with_the_next_render(self):
        comp_cls = _make_component()
        with fake_clock() as clock:
            url = _vars_url(comp_cls, comp_cls.render(kwargs={"col": "red"}, deps_strategy="document"))
            client = Client()
            assert client.get(url).status_code == 200

            clock.now += 101
            assert client.get(url).status_code == 404

            comp_cls.render(kwargs={"col": "red"})
            response = client.get(url)
            assert response.status_code == 200
            assert b"--col: red" in response.content

    @djc_test(components_settings={"vars_cache_max_bytes": 1_000})
    def test_a_render_with_too_much_data_still_renders(self, caplog):
        comp_cls = _make_component()
        with caplog.at_level(logging.WARNING, logger="django_components"):
            rendered = comp_cls.render(kwargs={"col": "x" * 5_000}, deps_strategy="document")
        assert "<div" in rendered
        assert "x" * 5_000 not in rendered
        assert "vars_cache_max_bytes" in caplog.text

    def test_variables_are_served_from_their_own_store(self):
        comp_cls = _make_component()
        url = _vars_url(comp_cls, comp_cls.render(kwargs={"col": "blue"}, deps_strategy="document"))
        response = Client().get(url)
        assert response.status_code == 200
        assert b"--col: blue" in response.content

    @djc_test(components_settings={"cache": "named"})
    def test_a_named_cache_holds_everything_and_keeps_its_own_timeout(self):
        locmem = "django.core.cache.backends.locmem.LocMemCache"
        cache_settings = {
            "default": {"BACKEND": locmem, "LOCATION": "default"},
            "named": {"BACKEND": locmem, "LOCATION": "djc-test-named", "TIMEOUT": 5},
        }
        with override_settings(CACHES=cache_settings):
            cache = caches["named"]
            try:
                # A new class stores its scripts right away, so it needs the cache to exist.
                comp_cls = _make_component()
                assert get_component_vars_cache() is cache
                assert get_component_media_cache() is cache

                with fake_clock() as clock:
                    comp_cls.render(kwargs={"col": "red"})
                    # Only the variables have a hash after the script type in their key.
                    keys = [key for key in cache._cache if re.search(r":css:[0-9a-f]+$", key)]
                    assert len(keys) == 1
                    # This cache has its own `TIMEOUT`, so `vars_cache_max_age` does not apply to it.
                    assert cache._expire_info[keys[0]] == clock.now + 5
            finally:
                cache.clear()
