# ruff: noqa: T201
import os
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.template.engine import Engine

from django_components.template_loader import DjcLoader
from django_components.util.command import CommandArg, ComponentCommand


# TODO_V1 - Remove, no longer needed?
class UpgradeCommand(ComponentCommand):
    name = "upgrade"
    help = "Upgrade django components syntax from '{%% component_block ... %%}' to '{%% component ... %%}'."

    arguments = (
        CommandArg(
            name_or_flags="--path",
            help="Path to search for components",
        ),
    )

    def handle(self, *_args: Any, **options: Any) -> None:
        current_engine = Engine.get_default()
        loader = DjcLoader(current_engine)
        dirs = loader.get_dirs(include_apps=False)

        if settings.BASE_DIR:
            dirs.append(Path(settings.BASE_DIR) / "templates")

        if options["path"]:
            dirs = [options["path"]]

        all_files: list[Path] = []

        for dir_path in dirs:
            print(f"Searching for components in {dir_path}...")
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if not file.endswith((".html", ".py")):
                        continue
                    file_path = Path(root) / file
                    all_files.append(file_path)

        for file_path in all_files:
            with file_path.open("r+", encoding="utf-8") as f:
                content = f.read()
                content_with_closed_components, step0_count = re.subn(
                    r'({%\s*component\s*"(\w+?)"(.*?)%})(?!.*?{%\s*endcomponent\s*%})',
                    r"\1{% endcomponent %}",
                    content,
                    flags=re.DOTALL,
                )
                updated_content, step1_count_opening = re.subn(
                    r'{%\s*component_block\s*"(\w+?)"\s*(.*?)%}',
                    r'{% component "\1" \2%}',
                    content_with_closed_components,
                    flags=re.DOTALL,
                )
                updated_content, step2_count_closing = re.subn(
                    r'{%\s*endcomponent_block\s*"(\w+?)"\s*%}',
                    r"{% endcomponent %}",
                    updated_content,
                    flags=re.DOTALL,
                )
                updated_content, step2_count_closing_no_name = re.subn(
                    r"{%\s*endcomponent_block\s*%}",
                    r"{% endcomponent %}",
                    updated_content,
                    flags=re.DOTALL,
                )
                total_updates = step0_count + step1_count_opening + step2_count_closing + step2_count_closing_no_name
                if total_updates > 0:
                    f.seek(0)
                    f.write(updated_content)
                    f.truncate()
                    print(f"Updated {file_path}: {total_updates} changes made")
