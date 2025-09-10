import re
from pathlib import Path

import pytest
from django.test import override_settings

from django_components.app_settings import ComponentsSettings, app_settings
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config(components={"autodiscover": False})


@djc_test
class TestSettings:
    @djc_test(
        components_settings={
            "context_behavior": "isolated",
        },
    )
    def test_valid_context_behavior(self):
        assert app_settings.CONTEXT_BEHAVIOR == "isolated"

    # NOTE: Since the part that we want to test here is otherwise part of the test setup
    # this test places the `override_settings` and `_load_settings` (which is called by `djc_test`)
    # inside the test.
    def test_raises_on_invalid_context_behavior(self):
        with override_settings(COMPONENTS={"context_behavior": "invalid_value"}):
            with pytest.raises(
                ValueError,
                match=re.escape("Invalid context behavior: invalid_value. Valid options are ['django', 'isolated']"),
            ):
                app_settings._load_settings()

    @djc_test(
        django_settings={
            "BASE_DIR": "base_dir",
        },
    )
    def test_works_when_base_dir_is_string(self):
        assert [Path("base_dir/components")] == app_settings.DIRS

    @djc_test(
        django_settings={
            "BASE_DIR": Path("base_dir"),
        },
    )
    def test_works_when_base_dir_is_path(self):
        assert [Path("base_dir/components")] == app_settings.DIRS

    @djc_test(
        components_settings={
            "context_behavior": "isolated",
        },
    )
    def test_settings_as_dict(self):
        assert app_settings.CONTEXT_BEHAVIOR == "isolated"

    # NOTE: Since the part that we want to test here is otherwise part of the test setup
    # this test places the `override_settings` and `_load_settings` (which is called by `djc_test`)
    # inside the test.
    def test_settings_as_instance(self):
        with override_settings(COMPONENTS=ComponentsSettings(context_behavior="isolated")):
            app_settings._load_settings()
            assert app_settings.CONTEXT_BEHAVIOR == "isolated"
