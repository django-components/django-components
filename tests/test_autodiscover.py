import importlib
import sys

import pytest

from django_components import AlreadyRegistered, registry
from django_components.autodiscovery import autodiscover, import_libraries
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


@djc_test
class TestAutodiscover:
    def test_autodiscover(self):
        all_components = registry.all().copy()
        assert "single_file_component" not in all_components
        assert "multi_file_component" not in all_components
        assert "relative_file_component" not in all_components
        assert "relative_file_pathobj_component" not in all_components

        try:
            modules = autodiscover(map_module=lambda p: "tests." + p if p.startswith("components") else p)
        except AlreadyRegistered:
            pytest.fail("Autodiscover should not raise AlreadyRegistered exception")

        assert "tests.components" in modules
        assert "tests.components.single_file" in modules
        assert "tests.components.staticfiles.staticfiles" in modules
        assert "tests.components.multi_file.multi_file" in modules
        assert "tests.components.relative_file_pathobj.relative_file_pathobj" in modules
        assert "tests.components.relative_file.relative_file" in modules
        assert "tests.test_app.components.app_lvl_comp.app_lvl_comp" in modules
        assert "django_components.components" in modules
        assert "django_components.components.dynamic" in modules

        all_components = registry.all().copy()
        assert "single_file_component" in all_components
        assert "multi_file_component" in all_components
        assert "relative_file_component" in all_components
        assert "relative_file_pathobj_component" in all_components


@djc_test
class TestImportLibraries:
    @djc_test(
        components_settings={
            "libraries": ["tests.components.single_file", "tests.components.multi_file.multi_file"],
        },
    )
    def test_import_libraries(self):
        all_components = registry.all().copy()

        # Ensure that the components are unregistered before importing again
        if "single_file_component" in all_components:
            registry.unregister("single_file_component")
        if "multi_file_component" in all_components:
            registry.unregister("multi_file_component")

        # Ensure that the modules are executed again after import
        if "tests.components.single_file" in sys.modules:
            del sys.modules["tests.components.single_file"]
        if "tests.components.multi_file.multi_file" in sys.modules:
            del sys.modules["tests.components.multi_file.multi_file"]

        try:
            modules = import_libraries()
        except AlreadyRegistered:
            pytest.fail("Autodiscover should not raise AlreadyRegistered exception")

        assert "tests.components.single_file" in modules
        assert "tests.components.multi_file.multi_file" in modules

        all_components = registry.all().copy()
        assert "single_file_component" in all_components
        assert "multi_file_component" in all_components

    @djc_test(
        components_settings={
            "libraries": ["tests.components.single_file", "tests.components.multi_file.multi_file"],
        },
    )
    def test_import_libraries_map_modules(self):
        # Strict `register()` requires explicit unregister before a reimport produces
        # a fresh class object under the same name.
        all_components = registry.all().copy()
        if "single_file_component" in all_components:
            registry.unregister("single_file_component")
        if "multi_file_component" in all_components:
            registry.unregister("multi_file_component")

        # Ensure that the modules are executed again after import
        if "tests.components.single_file" in sys.modules:
            del sys.modules["tests.components.single_file"]
        if "tests.components.multi_file.multi_file" in sys.modules:
            del sys.modules["tests.components.multi_file.multi_file"]

        seen = []
        try:
            import_libraries(map_module=lambda p: seen.append(p) or p)  # type: ignore[func-returns-value]
        except AlreadyRegistered:
            pytest.fail("Autodiscover should not raise AlreadyRegistered exception")

        assert seen == ["tests.components.single_file", "tests.components.multi_file.multi_file"]


@djc_test
class TestSysModulesIsolation:
    """
    Regression coverage for #1598: modules present before a @djc_test should not be
    re-executed by the test teardown.
    """

    def test_modules_present_before_test_are_not_reimported(self):
        # Ensure the target module is in `sys.modules` before any @djc_test cycle
        # touches it. This is the precondition the fix must preserve.
        importlib.import_module("tests.components.single_file")

        module_before = sys.modules.get("tests.components.single_file")
        assert module_before is not None
        module_id_before = id(module_before)

        @djc_test
        def inner_test() -> None:
            from django_components.autodiscovery import autodiscover

            autodiscover(map_module=lambda p: "tests." + p if p.startswith("components") else p)

        # Run two cycles - prior to the fix, the first teardown would pop the module from
        # `sys.modules`, and the second setup's `autodiscover` would re-execute it.
        inner_test()  # type: ignore[call-arg]
        inner_test()  # type: ignore[call-arg]

        module_after = sys.modules.get("tests.components.single_file")
        assert module_after is not None
        assert id(module_after) == module_id_before, (
            "tests.components.single_file was re-executed across @djc_test cycles; "
            "the sys.modules snapshot in _clear_djc_global_state should have prevented this."
        )

    # A directory without `__init__.py` is a namespace package. It has no `.py` file, so it's
    # missing from the list of modules that autodiscovery records for cleanup.
    def test_namespace_package_is_removed_with_its_parent(self, tmp_path, monkeypatch):
        package_dir = tmp_path / "djc_cleanup_pkg"
        (package_dir / "namespace").mkdir(parents=True)
        (package_dir / "__init__.py").write_text("")
        (package_dir / "namespace" / "recorded.py").write_text("VALUE = 1\n")
        (package_dir / "namespace" / "unrecorded.py").write_text("VALUE = 2\n")
        monkeypatch.syspath_prepend(tmp_path)

        @djc_test(
            components_settings={
                "libraries": ["djc_cleanup_pkg", "djc_cleanup_pkg.namespace.recorded"],
            },
        )
        def inner_test() -> None:
            import_libraries()
            # Imported directly, so it's not recorded by `import_libraries()`
            importlib.import_module("djc_cleanup_pkg.namespace.unrecorded")
            assert "djc_cleanup_pkg.namespace" in sys.modules

        inner_test()  # type: ignore[call-arg]

        leftovers = [name for name in sys.modules if name.startswith("djc_cleanup_pkg")]
        assert leftovers == []

        # With the parent package gone, a leftover namespace package raises
        # `KeyError: 'djc_cleanup_pkg'` here, because it looks up its parent in `sys.modules`.
        module = importlib.import_module("djc_cleanup_pkg.namespace.recorded")
        assert module.VALUE == 1

        for name in [name for name in sys.modules if name.startswith("djc_cleanup_pkg")]:
            del sys.modules[name]
