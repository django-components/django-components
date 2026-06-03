import gc
import tempfile
from pathlib import Path

from django.utils.autoreload import file_changed

from django_components import Component
from django_components.apps import _setup_component_file_reload
from django_components.component_media import (
    UNSET,
    _component_file_cache,
    _get_components_for_file,
    _register_component_file,
    _reset_component_file_cache,
)
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config({"reload_on_file_change": "off"})


def _disconnect_all_djc_handlers():
    """Remove all on_component_file_changed handlers from the file_changed signal."""
    removed = []
    for entry in list(file_changed.receivers):
        receiver_ref = entry[1]
        if callable(receiver_ref) and not hasattr(receiver_ref, "__self__"):
            func = receiver_ref
        elif callable(receiver_ref):
            func = receiver_ref()
        else:
            continue
        if func is not None and "on_component_file_changed" in getattr(func, "__qualname__", ""):
            file_changed.disconnect(func)
            removed.append(func)
    return removed


def _with_hotreload(reload_mode="hot"):
    """
    Helper that connects the hot-reload handler and returns a cleanup function
    that disconnects it. Use in tests to avoid handler leaking across tests.
    """
    previously_disconnected = _disconnect_all_djc_handlers()

    _setup_component_file_reload(reload_mode=reload_mode)

    def cleanup():
        _disconnect_all_djc_handlers()
        for handler in previously_disconnected:
            file_changed.connect(handler, weak=False)

    return cleanup


@djc_test
class TestComponentFileCache:
    """Tests for the file-to-component reverse index."""

    def test_register_and_lookup(self):
        class MyComp(Component):
            template = "hello"

        _register_component_file("/some/path/template.html", MyComp)
        result = _get_components_for_file("/some/path/template.html")
        assert result == [MyComp]

    def test_lookup_unknown_file_returns_empty(self):
        result = _get_components_for_file("/nonexistent/file.html")
        assert result == []

    def test_multiple_components_same_file(self):
        class CompA(Component):
            template = "a"

        class CompB(Component):
            template = "b"

        _register_component_file("/shared/template.html", CompA)
        _register_component_file("/shared/template.html", CompB)

        result = _get_components_for_file("/shared/template.html")
        assert set(result) == {CompA, CompB}

    def test_dead_weakrefs_are_pruned(self):
        class TempComp(Component):
            template = "temp"

        _register_component_file("/test_hotreload/file.html", TempComp)
        assert len(_get_components_for_file("/test_hotreload/file.html")) == 1

        del TempComp
        gc.collect()

        result = _get_components_for_file("/test_hotreload/file.html")
        assert result == []

    def test_reset_clears_cache(self):
        class MyComp(Component):
            template = "hello"

        _register_component_file("/some/file.html", MyComp)
        assert len(_component_file_cache) > 0

        _reset_component_file_cache()
        assert len(_component_file_cache) == 0


@djc_test
class TestComponentMediaReset:
    """Tests for targeted reset methods on ComponentMedia."""

    def test_reset_template_clears_template_cache(self):
        class MyComp(Component):
            template = "original content"

        assert MyComp.template == "original content"
        comp_media = MyComp._component_media  # type: ignore[attr-defined]

        assert comp_media.resolved_template is True
        assert comp_media._template is not UNSET
        assert comp_media.template is not UNSET

        comp_media.reset_template()

        assert comp_media.resolved_template is False
        assert comp_media._template is UNSET
        assert comp_media.template is UNSET

    def test_reset_files_clears_js_css_cache(self):
        class MyComp(Component):
            template = "hello"
            js = "console.log('original');"
            css = ".original { color: red; }"

        assert "original" in MyComp.js
        assert "original" in MyComp.css
        comp_media = MyComp._component_media  # type: ignore[attr-defined]

        assert comp_media.resolved_files is True
        assert comp_media.js is not UNSET
        assert comp_media.css is not UNSET

        comp_media.reset_files()

        assert comp_media.resolved_files is False
        assert comp_media.js is UNSET
        assert comp_media.css is UNSET

    def test_reset_template_preserves_resolved_relative_paths(self):
        class MyComp(Component):
            template = "hello"

        _ = MyComp.template
        comp_media = MyComp._component_media  # type: ignore[attr-defined]
        comp_media.resolved_relative_paths = True

        comp_media.reset_template()
        assert comp_media.resolved_relative_paths is True

    def test_reset_files_preserves_resolved_relative_paths(self):
        class MyComp(Component):
            template = "hello"
            js = "x"

        _ = MyComp.js
        comp_media = MyComp._component_media  # type: ignore[attr-defined]
        comp_media.resolved_relative_paths = True

        comp_media.reset_files()
        assert comp_media.resolved_relative_paths is True


@djc_test
class TestHotReloadSignalHandler:
    """Tests for the file_changed signal handler."""

    def test_hot_mode_returns_true_for_tracked_file(self):
        cleanup = _with_hotreload(reload_mode="hot")
        try:

            class MyComp(Component):
                template = "hello"

            abs_path = "/some/tracked/template.html"
            _register_component_file(abs_path, MyComp)

            results = file_changed.send(sender=None, file_path=Path(abs_path))
            assert any(result is True for _, result in results)
        finally:
            cleanup()

    def test_restart_mode_returns_none_for_tracked_file(self):
        cleanup = _with_hotreload(reload_mode="restart")
        try:

            class MyComp(Component):
                template = "hello"

            abs_path = "/some/tracked/template.html"
            _register_component_file(abs_path, MyComp)

            results = file_changed.send(sender=None, file_path=Path(abs_path))
            assert not any(result is True for _, result in results)
        finally:
            cleanup()

    def test_untracked_file_returns_none(self):
        cleanup = _with_hotreload(reload_mode="hot")
        try:
            results = file_changed.send(
                sender=None,
                file_path=Path("/nonexistent/untracked.html"),
            )
            assert not any(result is True for _, result in results)
        finally:
            cleanup()

    def test_signal_resets_component_media(self):
        cleanup = _with_hotreload(reload_mode="hot")
        try:

            class MyComp(Component):
                template = "original"
                js = "console.log('original');"

            _ = MyComp.template
            _ = MyComp.js

            comp_media = MyComp._component_media  # type: ignore[attr-defined]
            assert comp_media.resolved_template is True
            assert comp_media.resolved_files is True

            abs_path = "/some/component/template.html"
            _register_component_file(abs_path, MyComp)

            file_changed.send(sender=None, file_path=Path(abs_path))

            assert comp_media.resolved_template is False
            assert comp_media.resolved_files is False
            assert comp_media._template is UNSET
            assert comp_media.js is UNSET
        finally:
            cleanup()

    def test_multiple_components_sharing_file_all_get_reset(self):
        cleanup = _with_hotreload(reload_mode="hot")
        try:

            class CompA(Component):
                template = "a"

            class CompB(Component):
                template = "b"

            abs_path = "/shared/template.html"
            _register_component_file(abs_path, CompA)
            _register_component_file(abs_path, CompB)

            _ = CompA.template
            _ = CompB.template

            media_a = CompA._component_media  # type: ignore[attr-defined]
            media_b = CompB._component_media  # type: ignore[attr-defined]
            assert media_a.resolved_template is True
            assert media_b.resolved_template is True

            file_changed.send(sender=None, file_path=Path(abs_path))

            assert media_a.resolved_template is False
            assert media_b.resolved_template is False
        finally:
            cleanup()

    def test_inlined_content_not_in_file_cache(self):
        class MyComp(Component):
            template = "inlined content"
            js = "console.log('inlined');"
            css = ".inlined { color: red; }"

        _ = MyComp.template
        _ = MyComp.js
        _ = MyComp.css

        abs_paths = [p for p, refs in _component_file_cache.items() if any(r() is MyComp for r in refs)]
        assert abs_paths == []


@djc_test
class TestHotReloadEndToEnd:
    """End-to-end tests: modify file on disk, verify next render picks up the change."""

    @djc_test(
        django_settings={
            "TEMPLATES": [
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
                    "OPTIONS": {
                        "builtins": ["django_components.templatetags.component_tags"],
                        "loaders": [
                            "django.template.loaders.filesystem.Loader",
                            "django.template.loaders.app_directories.Loader",
                            "django_components.template_loader.Loader",
                        ],
                    },
                },
            ],
        },
    )
    def test_template_file_change_updates_next_render(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpl_path = Path(tmpdir) / "hotreload_test.html"
            tmpl_path.write_text("original {{ var }}")

            cleanup = _with_hotreload(reload_mode="hot")
            try:

                @djc_test(components_settings={"dirs": [tmpdir]})
                def inner():
                    class HotReloadComp(Component):
                        template_file = "hotreload_test.html"

                        def get_template_data(self, args, kwargs, slots, context):
                            return {"var": "value"}

                    rendered = HotReloadComp.render(kwargs={"var": "value"})
                    assert "original" in rendered

                    tmpl_path.write_text("updated {{ var }}")
                    file_changed.send(sender=None, file_path=tmpl_path)

                    rendered = HotReloadComp.render(kwargs={"var": "value"})
                    assert "updated" in rendered

                inner()
            finally:
                cleanup()

    def test_js_file_change_updates_next_access(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            js_path = Path(tmpdir) / "test.js"
            js_path.write_text("console.log('original');")

            cleanup = _with_hotreload(reload_mode="hot")
            try:

                @djc_test(components_settings={"dirs": [tmpdir]})
                def inner():
                    class JsComp(Component):
                        template = "hello"
                        js_file = "test.js"

                    assert JsComp.js is not None
                    assert "original" in JsComp.js

                    js_path.write_text("console.log('updated');")
                    file_changed.send(sender=None, file_path=js_path)

                    assert JsComp.js is not None
                    assert "updated" in JsComp.js

                inner()
            finally:
                cleanup()

    def test_css_file_change_updates_next_access(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_path = Path(tmpdir) / "test.css"
            css_path.write_text(".original { color: red; }")

            cleanup = _with_hotreload(reload_mode="hot")
            try:

                @djc_test(components_settings={"dirs": [tmpdir]})
                def inner():
                    class CssComp(Component):
                        template = "hello"
                        css_file = "test.css"

                    assert CssComp.css is not None
                    assert "original" in CssComp.css

                    css_path.write_text(".updated { color: blue; }")
                    file_changed.send(sender=None, file_path=css_path)

                    assert CssComp.css is not None
                    assert "updated" in CssComp.css

                inner()
            finally:
                cleanup()


@djc_test
class TestReloadOnFileChangeSetting:
    """Tests for the reload_on_file_change setting normalization."""

    @djc_test(components_settings={"reload_on_file_change": True})
    def test_true_maps_to_hot(self):
        from django_components.app_settings import app_settings

        assert app_settings.RELOAD_ON_FILE_CHANGE == "hot"

    @djc_test(components_settings={"reload_on_file_change": False})
    def test_false_maps_to_off(self):
        from django_components.app_settings import app_settings

        assert app_settings.RELOAD_ON_FILE_CHANGE == "off"

    @djc_test(components_settings={"reload_on_file_change": "hot"})
    def test_hot_string(self):
        from django_components.app_settings import app_settings

        assert app_settings.RELOAD_ON_FILE_CHANGE == "hot"

    @djc_test(components_settings={"reload_on_file_change": "off"})
    def test_off_string(self):
        from django_components.app_settings import app_settings

        assert app_settings.RELOAD_ON_FILE_CHANGE == "off"

    @djc_test(components_settings={"reload_on_file_change": "restart"})
    def test_restart_string(self):
        from django_components.app_settings import app_settings

        assert app_settings.RELOAD_ON_FILE_CHANGE == "restart"

    def test_invalid_value_raises(self):
        import pytest

        @djc_test(components_settings={"reload_on_file_change": "invalid"})
        def inner():
            pass

        with pytest.raises(ValueError, match="Invalid value"):
            inner()
