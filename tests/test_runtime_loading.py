"""
Injected page markup must not change how the client-side manager loads.

Here we check what the server writes. `test_runtime_loading_e2e.py` checks what a browser does with it.
"""

import base64
import dataclasses
import hashlib
import json
import re
from typing import ClassVar

from django.test import Client
from pytest_django.asserts import assertInHTML

from django_components import Component, ComponentExtension, OnDependenciesContext, Script, types
from django_components.testing import djc_test

from .testutils import CORE_JS_INTEGRITY, setup_test_config

setup_test_config()


class PageComponent(Component):
    template: types.django_html = """
        <!doctype html>
        <html><head></head><body><div>hi</div></body></html>
    """
    js: types.js = "$onComponent(() => {});"
    css: types.css = ".page { color: red; }"


class FragmentComponent(Component):
    template: types.django_html = """
        <div>hi</div>
    """
    js: types.js = "$onComponent(() => {});"
    css: types.css = ".fragment { color: var(--color); }"

    def get_js_data(self, args, kwargs, slots, context):
        return {"value": 1}

    def get_css_data(self, args, kwargs, slots, context):
        return {"color": "red"}


class HookExtension(ComponentExtension):
    """Applies whatever function a test puts in `edit` to every `Script`."""

    name = "test_hook"
    edit: ClassVar = None

    def on_dependencies(self, ctx: OnDependenciesContext):
        scripts = [HookExtension.edit(script) for script in ctx.scripts]
        return scripts, ctx.styles


def _sha384(content: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(content).digest()).decode()


def _data_block(html: str) -> dict:
    match = re.search(r"<script[^>]*data-djc[^>]*>(.*?)</script>", html, re.DOTALL)
    assert match is not None
    return json.loads(match.group(1))


def _tags_to_fetch(html: str) -> list[dict]:
    data = _data_block(html)
    tags = [*data["jsTags__toFetch"], *data["cssTags__toFetch"]]
    return [json.loads(base64.b64decode(tag)) for tag in tags]


@djc_test
class TestRuntimeIntegrity:
    def test_document_pins_the_runtime(self):
        rendered = PageComponent.render(deps_strategy="document")

        assert f'integrity="{CORE_JS_INTEGRITY}"' in rendered
        assert 'crossorigin="anonymous"' in rendered

    def test_fragment_loader_pins_the_runtime(self):
        rendered = FragmentComponent.render(deps_strategy="fragment")

        assert f's.integrity = "{CORE_JS_INTEGRITY}";' in rendered
        assert 's.crossOrigin = "anonymous";' in rendered

    @djc_test(django_settings={"STATIC_URL": "https://cdn.example.com/static/"})
    def test_full_url_is_left_alone(self):
        # `<base>` cannot move this URL, and the CDN might not send CORS headers.
        document = PageComponent.render(deps_strategy="document")
        assertInHTML(
            '<script src="https://cdn.example.com/static/django_components/django_components.min.js"></script>',
            document,
            count=1,
        )

        fragment = FragmentComponent.render(deps_strategy="fragment")
        assert "s.integrity" not in fragment
        assert "s.crossOrigin" not in fragment

    @djc_test(django_settings={"STATIC_URL": "//cdn.example.com/static/"})
    def test_protocol_relative_url_is_left_alone(self):
        assert "integrity" not in PageComponent.render(deps_strategy="document")


@djc_test
class TestFragmentFileIntegrity:
    def test_hash_matches_the_bytes_the_cache_view_serves(self):
        rendered = FragmentComponent.render(deps_strategy="fragment")
        tags = _tags_to_fetch(rendered)

        # Component JS, JS variables, component CSS and CSS variables
        assert len(tags) == 4
        client = Client()
        for tag in tags:
            attrs = tag["attrs"]
            response = client.get(attrs.get("src") or attrs.get("href"))
            assert response.status_code == 200
            assert attrs["integrity"] == _sha384(response.content)
            assert attrs["crossorigin"] == "anonymous"

    def test_media_files_get_no_hash(self):
        # We do not know the bytes of a developer's static files, see the docs on `base-uri`.
        class MediaComponent(Component):
            template: types.django_html = "<div>hi</div>"

            class Media:
                js = ("script.js",)

        tags = _tags_to_fetch(MediaComponent.render(deps_strategy="fragment"))

        assert [tag["attrs"] for tag in tags] == [{"src": "script.js"}]


@djc_test(components_settings={"extensions": [HookExtension]})
class TestHooks:
    def _render_with(self, edit) -> str:
        HookExtension.edit = staticmethod(edit)
        return PageComponent.render(deps_strategy="document")

    def test_hook_that_changes_the_url_loses_the_hash(self):
        def edit(script: Script) -> Script:
            if script.kind == "core" and script.url:
                script.url = "/somewhere/else.js"
            return script

        rendered = self._render_with(edit)

        assertInHTML('<script src="/somewhere/else.js"></script>', rendered, count=1)

    def test_hook_keeps_its_own_attributes(self):
        def edit(script: Script) -> Script:
            if script.kind == "core" and script.url:
                script.attrs["integrity"] = "sha512-mine"
                script.attrs["CrossOrigin"] = "use-credentials"
            return script

        rendered = self._render_with(edit)

        assert CORE_JS_INTEGRITY not in rendered
        assert 'integrity="sha512-mine"' in rendered
        assert 'CrossOrigin="use-credentials"' in rendered
        assert "anonymous" not in rendered

    def test_replace_keeps_the_hash(self):
        rendered = self._render_with(dataclasses.replace)

        assert f'integrity="{CORE_JS_INTEGRITY}"' in rendered


@djc_test(components_settings={"extensions": [HookExtension]})
class TestDataBlockNonce:
    @staticmethod
    def _set_nonce_on_runtime(script: Script) -> Script:
        # CSP needs no nonce on a JSON block, so a hook has no reason to add one
        if "data-djc" not in script.attrs and script.kind == "core":
            script.attrs["nonce"] = "abc"
        return script

    def test_document_block_gets_the_runtime_nonce(self):
        HookExtension.edit = staticmethod(self._set_nonce_on_runtime)

        rendered = PageComponent.render(deps_strategy="document")

        assert '<script type="application/json" data-djc nonce="abc">' in rendered

    def test_fragment_block_gets_the_loader_nonce(self):
        HookExtension.edit = staticmethod(self._set_nonce_on_runtime)

        rendered = FragmentComponent.render(deps_strategy="fragment")

        assert '<script type="application/json" data-djc nonce="abc">' in rendered

    def test_block_keeps_a_nonce_of_its_own(self):
        def edit(script: Script) -> Script:
            script.attrs["nonce"] = "own" if "data-djc" in script.attrs else "abc"
            return script

        HookExtension.edit = staticmethod(edit)

        rendered = PageComponent.render(deps_strategy="document")

        assert '<script type="application/json" data-djc nonce="own">' in rendered

    def test_no_nonce_is_added_when_the_page_has_none(self):
        HookExtension.edit = staticmethod(lambda script: script)

        rendered = PageComponent.render(deps_strategy="document")

        assert "nonce" not in rendered

    def test_nonce_on_a_component_script_does_not_count(self):
        # Only our own core scripts tell what the runtime tag carries.
        def edit(script: Script) -> Script:
            if script.kind != "core":
                script.attrs["nonce"] = "abc"
            return script

        HookExtension.edit = staticmethod(edit)

        rendered = PageComponent.render(deps_strategy="document")

        assert '<script type="application/json" data-djc>' in rendered
