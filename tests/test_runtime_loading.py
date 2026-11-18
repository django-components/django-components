"""
Injected page markup must not change how the client-side manager loads.

Here we check what the server writes. `test_runtime_loading_e2e.py` checks what a browser does with it.
"""

import base64
import dataclasses
import hashlib
import json
import re
from typing import Any, ClassVar
from unittest.mock import patch

from django.test import Client
from django.utils.functional import SimpleLazyObject
from pytest_django.asserts import assertInHTML

from django_components import Component, ComponentExtension, OnDependenciesContext, Script, render_dependencies, types
from django_components.cache import get_component_media_cache, get_component_vars_cache
from django_components.dependencies import get_script
from django_components.testing import djc_test

from .testutils import CORE_JS_INTEGRITY, CORE_JS_URL, setup_test_config

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


class PageFragment(Component):
    template: types.django_html = """
        <div>no variables</div>
    """
    js: types.js = "$onComponent(() => {});"
    css: types.css = ".no-variables { color: red; }"


class HookExtension(ComponentExtension):
    """Applies whatever function a test puts in `edit` to every `Script`."""

    name = "test_hook"
    edit: ClassVar[Any] = None

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

        assert f'src="{CORE_JS_URL}"' in rendered
        assert f'integrity="{CORE_JS_INTEGRITY}"' in rendered
        assert 'crossorigin="anonymous"' in rendered

    def test_fragment_loader_pins_the_runtime(self):
        rendered = FragmentComponent.render(deps_strategy="fragment")

        assert f's.src = "{CORE_JS_URL}";' in rendered
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
        assert 's.src = "https://cdn.example.com/static/django_components/django_components.min.js";' in fragment
        assert "s.integrity" not in fragment
        assert "s.crossOrigin" not in fragment

    @djc_test(django_settings={"STATIC_URL": "/static/"})
    def test_version_stays_before_a_url_fragment(self):
        with patch("django_components.dependencies.static", return_value="/static/x.js#part"):
            rendered = PageComponent.render(deps_strategy="document")

        assert re.search(r'src="/static/x\.js\?v=[0-9a-f]{12}#part"', rendered)

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

    def test_file_gone_from_the_cache_is_written_again(self):
        # A `Component.Cache` hit skips the step that stores the file, and another worker may have run it
        raw = PageFragment.render(deps_strategy="ignore")
        get_component_media_cache().clear()

        rendered = render_dependencies(raw, strategy="fragment")

        tags = _tags_to_fetch(rendered)
        assert len(tags) == 2
        assert all("integrity" in tag["attrs"] for tag in tags)

    def test_variables_gone_from_the_cache_get_no_tag(self):
        # Only the render that made them had the values, so a tag could not carry a hash.
        raw = FragmentComponent.render(deps_strategy="ignore")
        get_component_media_cache().clear()
        get_component_vars_cache().clear()

        with patch("django_components.dependencies.logger") as logger:
            rendered = render_dependencies(raw, strategy="fragment")

        assert len(_tags_to_fetch(rendered)) == 2
        assert logger.warning.call_count == 2

    def test_variables_gone_after_the_check_get_no_tag(self):
        # The variables can expire between the check that they exist and the read that hashes
        # them. The read must still leave out the tag, because the tag could not carry a hash.
        raw = FragmentComponent.render(deps_strategy="ignore")
        get_component_vars_cache().clear()

        with (
            patch("django_components.dependencies._is_script_in_cache", return_value=True),
            patch("django_components.dependencies.logger") as logger,
        ):
            rendered = render_dependencies(raw, strategy="fragment")

        tags = _tags_to_fetch(rendered)
        assert len(tags) == 2
        assert all("integrity" in tag["attrs"] for tag in tags)
        left_out = [call.args[0] for call in logger.warning.call_args_list if call.args[0].startswith("Left out")]
        assert len(left_out) == 2

    def test_many_instances_read_each_file_once(self):
        rendered = "".join(FragmentComponent.render(deps_strategy="ignore") for _ in range(20))

        with patch("django_components.dependencies.get_script", wraps=get_script) as spy:
            render_dependencies(rendered, strategy="fragment")

        # Component JS, JS variables, component CSS and CSS variables
        assert spy.call_count == 4

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

        assert _data_block(rendered)["nonce"] == "abc"

    def test_fragment_block_gets_the_loader_nonce(self):
        HookExtension.edit = staticmethod(self._set_nonce_on_runtime)

        rendered = FragmentComponent.render(deps_strategy="fragment")

        assert _data_block(rendered)["nonce"] == "abc"

    def test_lazy_nonce_works(self):
        # Django 6.0's nonce is a lazy object like this one
        def edit(script: Script) -> Script:
            if "data-djc" not in script.attrs and script.kind == "core":
                script.attrs["nonce"] = SimpleLazyObject(lambda: "abc")
            return script

        HookExtension.edit = staticmethod(edit)

        rendered = PageComponent.render(deps_strategy="document")

        assert _data_block(rendered)["nonce"] == "abc"

    def test_nonce_cannot_end_the_block(self):
        def edit(script: Script) -> Script:
            if "data-djc" not in script.attrs and script.kind == "core":
                script.attrs["nonce"] = "</script>"
            return script

        HookExtension.edit = staticmethod(edit)

        rendered = PageComponent.render(deps_strategy="document")

        assert _data_block(rendered)["nonce"] == "</script>"

    def test_block_uses_a_nonce_of_its_own(self):
        def edit(script: Script) -> Script:
            script.attrs["nonce"] = "own" if "data-djc" in script.attrs else "abc"
            return script

        HookExtension.edit = staticmethod(edit)

        rendered = PageComponent.render(deps_strategy="document")

        assert _data_block(rendered)["nonce"] == "own"

    def test_no_nonce_is_added_when_the_page_has_none(self):
        HookExtension.edit = staticmethod(lambda script: script)

        rendered = PageComponent.render(deps_strategy="document")

        assert "nonce" not in rendered
        assert "nonce" not in _data_block(rendered)

    def test_nonce_on_a_component_script_does_not_count(self):
        # Only our own core scripts tell what the runtime tag carries.
        def edit(script: Script) -> Script:
            if script.kind != "core":
                script.attrs["nonce"] = "abc"
            return script

        HookExtension.edit = staticmethod(edit)

        rendered = PageComponent.render(deps_strategy="document")

        assert "nonce" not in _data_block(rendered)


class CdnMediaFragment(Component):
    template: types.django_html = """
        <div>hi</div>
    """
    js: types.js = "$onComponent(() => {});"

    class Media:
        js = ("https://cdn.example.com/lib.js", "local.js", "/elsewhere/app.js")


@djc_test(django_settings={"STATIC_URL": "/static/"}, components_settings={"extensions": [HookExtension]})
class TestFragmentScriptsWithoutNonce:
    """
    A fragment without a nonce goes into a page without one, where the runtime loads only the
    app's own files. The server tells the developer which scripts of a fragment it will skip.
    """

    @staticmethod
    def _warned_urls(component: type[Component]) -> list[str]:
        with (
            patch("django_components.dependencies.logger") as logger,
            patch("django_components.dependencies._warned_skipped_urls", set()),
        ):
            component.render(deps_strategy="fragment")
            component.render(deps_strategy="fragment")
        matches = [re.search(r"script '([^']+)'", call.args[0]) for call in logger.warning.call_args_list]
        assert all(match is not None for match in matches)
        return [match.group(1) for match in matches if match is not None]

    def test_warns_once_for_each_script_outside_the_app_files(self):
        HookExtension.edit = staticmethod(lambda script: script)

        # `local.js` becomes `/static/local.js`, and the component's own file is in `/components/cache/`
        assert self._warned_urls(CdnMediaFragment) == ["https://cdn.example.com/lib.js", "/elsewhere/app.js"]

    def test_no_warning_on_a_page_with_a_nonce(self):
        # There the runtime checks the nonce, and loads every script the block names
        HookExtension.edit = staticmethod(TestDataBlockNonce._set_nonce_on_runtime)

        assert self._warned_urls(CdnMediaFragment) == []

    @djc_test(django_settings={"STATIC_URL": "https://cdn.example.com/static/"})
    def test_full_static_url_counts_as_the_static_folder(self):
        class StaticCdnFragment(Component):
            template: types.django_html = "<div>hi</div>"

            class Media:
                js = ("local.js", "https://cdn.example.com/lib.js", "//cdn.example.com/static/other.js")

        HookExtension.edit = staticmethod(lambda script: script)

        assert self._warned_urls(StaticCdnFragment) == ["https://cdn.example.com/lib.js"]

    @djc_test(django_settings={"STATIC_URL": "/"})
    def test_static_url_at_the_root_is_not_a_folder(self):
        # The root of the page's origin would let through every path, such as uploaded files
        class RootStaticFragment(Component):
            template: types.django_html = "<div>hi</div>"

            class Media:
                js = ("local.js",)

        HookExtension.edit = staticmethod(lambda script: script)

        assert self._warned_urls(RootStaticFragment) == ["/local.js"]

    def test_encoded_slash_is_not_in_the_folder(self):
        class EncodedFragment(Component):
            template: types.django_html = "<div>hi</div>"

            class Media:
                js = ("/static/..%2Fuploads/x.js",)

        HookExtension.edit = staticmethod(lambda script: script)

        assert self._warned_urls(EncodedFragment) == ["/static/..%2Fuploads/x.js"]

    def test_runtime_outside_its_folder_gives_no_folder(self):
        # A CDN or proxy that moves the file out of its `django_components/` folder leaves the
        # runtime nothing to read `STATIC_URL` from
        HookExtension.edit = staticmethod(lambda script: script)

        with patch("django_components.dependencies.static", return_value="/static/bundle.js"):
            assert self._warned_urls(CdnMediaFragment) == [
                "https://cdn.example.com/lib.js",
                "/static/local.js",
                "/elsewhere/app.js",
            ]
