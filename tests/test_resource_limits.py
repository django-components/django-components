"""Requests and rendered data must not cost the server more work or memory than their size justifies."""

import warnings

import pytest
from django.test import Client
from django.urls import Resolver404, resolve, reverse

from django_components import Component, types
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

        def get_css_data(self, args, kwargs, slots, context):
            return {"col": "red"}

    return CachedComp


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
