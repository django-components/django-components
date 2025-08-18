import tempfile
from io import StringIO
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestCreateComponentCommand:
    def test_default_file_names(self):
        temp_dir = tempfile.mkdtemp()

        component_name = "defaultcomponent"
        call_command("components", "create", component_name, "--path", temp_dir)

        expected_files = [
            Path(temp_dir) / component_name / "script.js",
            Path(temp_dir) / component_name / "style.css",
            Path(temp_dir) / component_name / "template.html",
        ]
        for file_path in expected_files:
            assert file_path.exists()

        rmtree(temp_dir)

    def test_nondefault_creation(self):
        temp_dir = tempfile.mkdtemp()

        component_name = "testcomponent"
        call_command(
            "components",
            "create",
            component_name,
            "--path",
            temp_dir,
            "--js",
            "test.js",
            "--css",
            "test.css",
            "--template",
            "test.html",
        )

        expected_files = [
            Path(temp_dir) / component_name / "test.js",
            Path(temp_dir) / component_name / "test.css",
            Path(temp_dir) / component_name / "test.html",
            Path(temp_dir) / component_name / f"{component_name}.py",
        ]

        for file_path in expected_files:
            assert file_path.exists(), f"File {file_path} was not created"

        rmtree(temp_dir)

    def test_dry_run(self):
        temp_dir = tempfile.mkdtemp()

        component_name = "dryruncomponent"
        call_command(
            "components",
            "create",
            component_name,
            "--path",
            temp_dir,
            "--dry-run",
        )

        component_path = Path(temp_dir) / component_name
        assert not component_path.exists()

        rmtree(temp_dir)

    def test_force_overwrite(self):
        temp_dir = tempfile.mkdtemp()

        component_name = "existingcomponent"
        component_path = Path(temp_dir) / component_name
        component_path.mkdir(parents=True)

        filepath = component_path / f"{component_name}.py"
        with filepath.open("w", encoding="utf-8") as f:
            f.write("hello world")

        call_command(
            "components",
            "create",
            component_name,
            "--path",
            temp_dir,
            "--force",
        )

        filepath = component_path / f"{component_name}.py"
        with filepath.open("r", encoding="utf-8") as f:
            assert "hello world" not in f.read()

        rmtree(temp_dir)

    def test_error_existing_component_no_force(self):
        temp_dir = tempfile.mkdtemp()

        component_name = "existingcomponent_2"
        component_path = Path(temp_dir) / component_name
        component_path.mkdir(parents=True)

        with pytest.raises(CommandError):
            call_command("components", "create", component_name, "--path", temp_dir)

        rmtree(temp_dir)

    def test_verbose_output(self):
        temp_dir = tempfile.mkdtemp()

        component_name = "verbosecomponent"
        out = StringIO()
        with patch("sys.stdout", new=out):
            call_command(
                "components",
                "create",
                component_name,
                "--path",
                temp_dir,
                "--verbose",
                stdout=out,
            )
        output = out.getvalue()
        assert "component at" in output

        rmtree(temp_dir)

    # TODO_V1 - REMOVE - deprecated
    def test_startcomponent(self):
        temp_dir = tempfile.mkdtemp()

        component_name = "defaultcomponent"
        call_command("startcomponent", component_name, "--path", temp_dir)

        expected_files = [
            Path(temp_dir) / component_name / "script.js",
            Path(temp_dir) / component_name / "style.css",
            Path(temp_dir) / component_name / "template.html",
        ]
        for file_path in expected_files:
            assert file_path.exists()

        rmtree(temp_dir)
