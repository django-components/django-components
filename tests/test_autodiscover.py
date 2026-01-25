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
