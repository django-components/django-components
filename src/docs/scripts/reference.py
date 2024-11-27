"""
Generate reference for all the different kinds of public API that we expose,
like regular Python imports, middleware, template tags, settings, Django URLs, etc.

All pages are generated inside `docs/reference/`.

Generation flow:
1. For each section, like `commands`, we look up the corresponding template
   named `reference_<section>.md`, e.g. `docs/templates/reference_commands.md`.

   This template contains the "preface" or text that will be rendered BEFORE
   the auto-generated docs.

2. For each section, we try to import it same way as the user would. And for each
   section we do filtering and post-processing, to pick only those symbols (e.g. func, class, ...)
   from the public API, that are relevant for that section.

3. Once we have our classes / functions, etc, we generate the mkdocstring entries like
   so:

   ```md
   ::: my_library.my_module.my_class
   ```

   See https://mkdocstrings.github.io/

4. These generated files in `docs/reference` are then picked up by mkdocs / mkdocstrings
   when we build or serve mkdocs, e.g. with:

    ```sh
    mkdocs serve
    ```

Note that this file is set in the `gen-files` plugin in `mkdocs.yml`. That means that
we don't have to run it manually. It will be run each time mkdocs is built.
"""

import inspect
import re
from argparse import ArgumentParser
from importlib import import_module
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Type, Union

from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver

from django_components import ComponentVars, TagFormatterABC
from django_components.component import Component
from django_components.templatetags.component_tags import TagSpec
from django_components.util.misc import get_import_path
from docs.scripts.extensions import _format_source_code_html

root = Path(__file__).parent.parent.parent.parent


def gen_reference_api():
    """
    Generate documentation for the Python API of `django_components`.

    This takes all public symbols exported from `django_components`, except for those
    that are handled in other sections, like components, exceptions, etc.
    """
    module = import_module("django_components")

    preface = (root / "src/docs/templates/reference_api.md").read_text()
    out_file = root / "src/docs/reference/api.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        for name, obj in inspect.getmembers(module):
            if (
                name.startswith("_")
                or inspect.ismodule(obj)
                # Skip entries which are handled in other sections
                or _is_component_cls(obj)
                or _is_error_cls(obj)
                or _is_tag_formatter_instance(obj)
                or _is_tag_formatter_cls(obj)
            ):
                continue

            # For each entry, generate a mkdocstrings entry, e.g.
            # ```
            # ::: django_components.Component
            #     options:
            #       show_if_no_docstring: true
            # ```
            f.write(f"::: {module.__name__}.{name}\n" f"    options:\n" f"      show_if_no_docstring: true\n")

            f.write("\n")


def gen_reference_exceptions():
    """
    Generate documentation for the Exception classes included in the Python API of `django_components`.
    """
    module = import_module("django_components")

    preface = (root / "src/docs/templates/reference_exceptions.md").read_text()
    out_file = root / "src/docs/reference/exceptions.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        for name, obj in inspect.getmembers(module):
            if (
                name.startswith("_")
                or inspect.ismodule(obj)
                # Skip entries which are handled in other sections
                or not _is_error_cls(obj)
            ):
                continue

            # For each entry, generate a mkdocstrings entry, e.g.
            # ```
            # ::: django_components.Component
            #     options:
            #       show_if_no_docstring: true
            # ```
            f.write(f"::: {module.__name__}.{name}\n" f"    options:\n" f"      show_if_no_docstring: true\n")

            f.write("\n")


def gen_reference_components():
    """
    Generate documentation for the Component classes (AKA pre-defined components) included
    in the Python API of `django_components`.
    """
    module = import_module("django_components.components")

    preface = (root / "src/docs/templates/reference_components.md").read_text()
    out_file = root / "src/docs/reference/components.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        for name, obj in inspect.getmembers(module):
            if not _is_component_cls(obj):
                continue

            class_name = get_import_path(obj)

            # If the component classes define any extra methods, we want to show them.
            # BUT, we don't to show the methods that belong to the base Component class.
            unique_methods = _get_unique_methods(Component, obj)
            if unique_methods:
                members = ", ".join(unique_methods)
                members = f"[{ unique_methods }]"
            else:
                # Use `false` to hide all members to show no methods
                members = "false"

            # For each entry, generate a mkdocstrings entry, e.g.
            # ```
            # ::: django_components.components.dynamic.DynamicComponent
            #
            #     options:
            #       ...
            # ```
            f.write(
                f"::: {class_name}\n"
                f"    options:\n"
                f"      inherited_members: false\n"
                f"      show_root_heading: true\n"
                f"      show_signature: false\n"
                f"      separate_signature: false\n"
                f"      members: {members}\n"
            )

            f.write("\n")


def gen_reference_settings():
    """
    Generate documentation for the settings of django-components, as defined by the `ComponentsSettings` class.
    """
    module = import_module("django_components.app_settings")

    preface = (root / "src/docs/templates/reference_settings.md").read_text()
    out_file = root / "src/docs/reference/settings.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        # 1. Insert section from `reference_settings.md`
        f.write(preface + "\n\n")

        # 2. Insert code snippet with default settings from `app_settings.py`
        if not module.__file__:
            raise RuntimeError(f"Failed to get filepath for module '{module.__name__}'")

        default_settings_markdown = _gen_default_settings_section(module.__file__)
        f.write(default_settings_markdown)

        # 3. Print each setting and their descriptions
        setting_cls = module.ComponentsSettings
        class_name = get_import_path(setting_cls)

        # NOTE: If no unique methods, just document the class itself without methods
        unique_methods = _get_unique_methods(NamedTuple, setting_cls)

        for name in sorted(unique_methods):
            # Ignore - these belong to NamedTuple
            if name in ("count", "index"):
                continue

            # For each entry, generate a mkdocstrings entry, e.g.
            # ```
            # ::: django_components.app_settings.ComponentsSettings.autodiscover
            #     options:
            #       ...
            # ```
            f.write(
                f"::: {class_name}.{name}\n"
                f"    options:\n"
                f"      show_root_heading: true\n"
                f"      show_signature: true\n"
                f"      separate_signature: true\n"
                f"      show_symbol_type_heading: false\n"
                f"      show_symbol_type_toc: false\n"
                f"      show_if_no_docstring: true\n"
                f"      show_labels: false\n"
            )
            f.write("\n")


# Get attributes / methods that are unique to the subclass
def _get_unique_methods(base_class: Type, sub_class: Type):
    base_methods = set(dir(base_class))
    subclass_methods = set(dir(sub_class))
    unique_methods = subclass_methods - base_methods

    return [method for method in unique_methods if not method.startswith("_")]


def _gen_default_settings_section(app_settings_filepath: str) -> str:
    # In the soure code (`app_settings.py`), we've inserted following strings
    # to mark the start and end of the where we define the default settings.
    # We copy this as a plain string, so that the comments are preserved.
    settings_sourcecode = Path(app_settings_filepath).read_text()
    defaults_snippet = settings_sourcecode.split("--snippet:defaults--")[1].split("--endsnippet:defaults--")[0]

    # Next we need to clean up the snippet:

    # Remove single line from both ends to remove comments and the snippet strings
    defaults_snippet_lines = defaults_snippet.split("\n")[1:-1]

    # Also remove escape/formatter comments at the end of the lines like
    # `# noqa` or `# type: ignore`
    comment_re = re.compile(r"#\s+(?:type\:|noqa)")

    # Some settings are dynamic in a sense that their value depends on the Django settings,
    # and thus may change anytime. Because the default settings are defined at the top-level
    # of the module, we want to delay evaluation of `settings.my_setting`. For that we use the
    # `Dynamic` class and a lambda function.
    #
    # However, for the documentation, we need to remove those.
    dynamic_re = re.compile(r"Dynamic\(lambda\: (?P<code>.+)\)")
    cleaned_snippet_lines = []
    for line in defaults_snippet_lines:
        line = comment_re.split(line)[0].rstrip()
        line = dynamic_re.sub(
            lambda m: m.group("code"),
            line,
        )
        cleaned_snippet_lines.append(line)
    clean_defaults_snippet = "\n".join(cleaned_snippet_lines)

    return (
        "### Settings defaults\n\n"
        "Here's overview of all available settings and their defaults:\n\n"
        + f"```py\n{clean_defaults_snippet}\n```"
        + "\n\n"
    )


def gen_reference_middlewares():
    """
    Generate documentation for all available middleware of django-components,
    as listed in module `django_components.middleware`.
    """
    module = import_module("django_components.middleware")

    preface = (root / "src/docs/templates/reference_middlewares.md").read_text()
    out_file = root / "src/docs/reference/middlewares.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        for name, obj in inspect.getmembers(module):
            if not inspect.isclass(obj):
                continue

            class_name = get_import_path(obj)

            # For each entry, generate a mkdocstrings entry, e.g.
            # ```
            # ::: django_components.middleware.ComponentDependencyMiddleware
            #     options:
            #       ...
            # ```
            f.write(
                f"::: {class_name}\n"
                f"    options:\n"
                f"      inherited_members: false\n"
                f"      show_root_heading: true\n"
                f"      show_signature: false\n"
                f"      separate_signature: false\n"
                f"      show_symbol_type_heading: false\n"
                f"      show_symbol_type_toc: false\n"
                f"      show_if_no_docstring: true\n"
                f"      show_labels: false\n"
            )

            f.write("\n")


def gen_reference_tagformatters():
    """
    Generate documentation for all pre-defined TagFormatters included
    in the Python API of `django_components`.
    """
    module = import_module("django_components")

    preface = (root / "src/docs/templates/reference_tagformatters.md").read_text()
    out_file = root / "src/docs/reference/tag_formatters.md"

    tag_formatter_classes: Dict[str, Type[TagFormatterABC]] = {}
    tag_formatter_instances: Dict[str, TagFormatterABC] = {}
    for name, obj in inspect.getmembers(module):
        if _is_tag_formatter_instance(obj):
            tag_formatter_instances[name] = obj
        elif _is_tag_formatter_cls(obj):
            tag_formatter_classes[name] = obj

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        # Generate a summary of avilable tag formatters.
        # For each pre-defined TagFormatter entry, generate e.g.
        # ```markdown
        # - `django_components.component_formatter` for [ComponentFormatter](#django_components.ComponentFormatter)
        # ```
        formatted_instances_lines: List[str] = []
        for name, inst in tag_formatter_instances.items():
            cls = inst.__class__
            cls_link_hash = f"#{get_import_path(cls)}"
            formatted_instances_lines.append(f"- `django_components.{name}` for [{cls.__name__}]({cls_link_hash})\n")

        formatted_instances = "\n".join(formatted_instances_lines)
        f.write("### Available tag formatters\n\n" + formatted_instances)

        for name, obj in tag_formatter_classes.items():
            class_name = get_import_path(obj)

            # Generate reference entry for each TagFormatter class.
            # For each entry TagFormatter class, generate a mkdocstrings entry, e.g.
            # ```
            # ::: django_components.tag_formatter.ComponentFormatter
            #     options:
            #       ...
            # ```
            f.write(
                f"::: {class_name}\n"
                f"    options:\n"
                f"      inherited_members: false\n"
                f"      show_root_heading: true\n"
                f"      show_signature: false\n"
                f"      separate_signature: false\n"
                f"      show_symbol_type_heading: false\n"
                f"      show_symbol_type_toc: false\n"
                f"      show_if_no_docstring: true\n"
                f"      show_labels: false\n"
                f"      members: false\n"
            )

            f.write("\n")


def gen_reference_urls():
    """
    Generate documentation for all URLs (`urlpattern` entries) defined by django-components.
    """
    module = import_module("django_components.urls")

    preface = (root / "src/docs/templates/reference_urls.md").read_text()
    out_file = root / "src/docs/reference/urls.md"

    all_urls = _list_urls(module.urlpatterns)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        # Simply list all URLs, e.g.
        # `- components/cache/<str:comp_cls_hash>.<str:script_type>/`
        f.write("\n".join([f"- `{url_path}`\n" for url_path in all_urls]))


def gen_reference_commands():
    """
    Generate documentation for all Django admin commands defined by django-components.

    These are discovered by looking at the files defined inside `management/commands`.
    """
    command_files = Path("./src/django_components/management/commands").glob("*.py")
    command_modules = [
        (p.stem, f"django_components.management.commands.{p.stem}")
        for p in command_files
        if not p.stem.startswith("_")
    ]

    preface = (root / "src/docs/templates/reference_commands.md").read_text()
    out_file = root / "src/docs/reference/commands.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        for cmd_name, cmd_path in command_modules:
            cmd_module = import_module(cmd_path)
            cmd_cls: BaseCommand = cmd_module.Command
            cmd_summary = cmd_cls.help
            cmd_desc = dedent(cmd_cls.__doc__ or "")
            cmd_parser: ArgumentParser = cmd_cls().create_parser("manage.py", cmd_name)
            cmd_usage: str = cmd_parser.format_usage()
            formatted_args = _format_command_args(cmd_parser)

            # Add link to source code
            module_rel_path = Path(cmd_module.__file__).relative_to(Path.cwd())  # type: ignore[arg-type]
            obj_lineno = inspect.findsource(cmd_cls)[1]
            source_code_link = _format_source_code_html(module_rel_path, obj_lineno)

            # NOTE: For the commands we have to generate the markdown entries ourselves,
            # instead of delegating to mkdocs, for two reasons:
            # 1. All commands have to use the class name `Command` for Django to pick them up
            # 2. The command name is actually defined by the file name.
            f.write(
                f"## `{cmd_name}`\n\n"
                f"```txt\n{cmd_usage}\n```\n\n"
                f"{source_code_link}\n\n"
                f"{cmd_summary}\n\n"
                f"{formatted_args}\n\n"
                f"{cmd_desc}\n\n"
            )


def gen_reference_templatetags():
    """
    Generate documentation for all Django template tags defined by django-components,
    like `{% slot %}`, `{% component %}`, etc.

    These are discovered by looking at the files defined inside `django_components/template_tags`.
    """
    tags_files = Path("./src/django_components/templatetags").glob("*.py")
    tags_modules = [
        (p.stem, f"django_components.templatetags.{p.stem}") for p in tags_files if not p.stem.startswith("_")
    ]

    preface = (root / "src/docs/templates/reference_templatetags.md").read_text()
    out_file = root / "src/docs/reference/template_tags.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        for mod_name, mod_path in tags_modules:
            tags_module = import_module(mod_path)
            module_rel_path = Path(tags_module.__file__).relative_to(Path.cwd())  # type: ignore[arg-type]

            f.write(
                f"All following template tags are defined in\n\n"
                f"`{mod_path}`\n\n"
                f"Import as\n```django\n{{% load {mod_name} %}}\n```\n\n"
            )

            for name, obj in inspect.getmembers(tags_module):
                if not _is_template_tag(obj):
                    continue

                tag_spec: TagSpec = obj._tag_spec
                tag_signature = _format_tag_signature(tag_spec)
                obj_lineno = inspect.findsource(obj)[1]
                source_code_link = _format_source_code_html(module_rel_path, obj_lineno)

                # Use the tag's function's docstring
                docstring = dedent(obj.__doc__ or "").strip()

                # Rebuild (almost) the same documentation than as if we used
                # mkdocstrings' `::: path.to.module` syntax.
                # Instead we rebuild it, so we can format the function signature as template tag,
                # e.g.
                # ```django
                # {% component [arg, ...] **kwargs [only] %}
                # {% endcomponent %}
                # ```
                f.write(
                    f"## {name}\n\n"
                    f"```django\n"
                    f"{tag_signature}\n"
                    f"```\n\n"
                    f"{source_code_link}\n\n"
                    f"{docstring}\n\n"
                )


def gen_reference_templatevars():
    """
    Generate documentation for all variables that are available inside the component templates
    under the `{{ component_vars }}` variable, as defined by `ComponentVars`.
    """
    preface = (root / "src/docs/templates/reference_templatevars.md").read_text()
    out_file = root / "src/docs/reference/template_vars.md"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as f:
        f.write(preface + "\n\n")

        for field in ComponentVars._fields:
            f.write(f"::: {ComponentVars.__module__}.{ComponentVars.__name__}.{field}\n\n")


def _list_urls(urlpatterns: Sequence[Union[URLPattern, URLResolver]], prefix=""):
    """Recursively extract all URLs and their associated views from Django's urlpatterns"""
    urls: List[str] = []

    for pattern in urlpatterns:
        if isinstance(pattern, URLPattern):
            # Direct view pattern
            path = prefix + str(pattern.pattern)
            urls.append(path)
        elif isinstance(pattern, URLResolver):
            # Included URLs, resolve recursively
            nested_patterns = pattern.url_patterns
            nested_prefix = prefix + str(pattern.pattern)
            urls += _list_urls(nested_patterns, nested_prefix)

    return urls


def _format_tag_signature(tag_spec: TagSpec) -> str:
    """
    Given the TagSpec instance, format the tag's function signature like:
    ```django
    {% component [arg, ...] **kwargs [only] %}
    {% endcomponent %}
    ```
    """
    params: List[str] = [tag_spec.tag]

    if tag_spec.positional_only_args:
        params.extend([*tag_spec.positional_only_args, "/"])

    optional_kwargs = set(tag_spec.optional_kwargs or [])

    params.extend([f"{name}=None" if name in optional_kwargs else name for name in tag_spec.pos_or_keyword_args or []])

    if tag_spec.positional_args_allow_extra:
        params.append("[arg, ...]")

    if tag_spec.keywordonly_args is True:
        params.append("**kwargs")
    elif tag_spec.keywordonly_args:
        params.extend(
            [f"{name}=None" if name in optional_kwargs else name for name in (tag_spec.keywordonly_args or [])]
        )

    if tag_spec.flags:
        params.extend([f"[{name}]" for name in tag_spec.flags])

    # Create the function signature
    full_tag = f"{{% {' '.join(params)} %}}"
    if tag_spec.end_tag:
        full_tag += f"\n{{% {tag_spec.end_tag} %}}"

    return full_tag


# For simplicity, we let `ArgumentParser` format the command args properly.
# And then we parse that to extract the available args and their descriptions.
#
# NOTE: Based on `ArgumentParser.format_help()`, but skips usage and description,
#       and prints only the inputs.
def _gen_command_args(parser: ArgumentParser) -> str:
    formatter = parser._get_formatter()

    # positionals, optionals and user-defined groups
    for action_group in parser._action_groups:
        formatter.start_section(action_group.title)
        formatter.add_text(action_group.description)
        formatter.add_arguments(action_group._group_actions)
        formatter.end_section()

    return formatter.format_help()


# PARSE THIS:
# ```
# options:
#   -h, --help            show this help message and exit
#   --path PATH           Path to search for components
# ```
#
# INTO THIS:
# ```
# {'options': [{'desc': 'show this help message and exit',
#               'names': ['-h', '--help']},
#              {'desc': 'Path to search for components',
#               'names': ['--path PATH']},
#              {'desc': "Show program's version number and exit.",
# ```
def _parse_command_args(cmd_inputs: str) -> Dict[str, List[Dict]]:
    section: Optional[str] = None
    data: Dict[str, List[Dict]] = {}

    for line in cmd_inputs.split("\n"):
        if not line:
            section = None
            continue

        if section is None:
            if not line.endswith(":"):
                raise RuntimeError("Expected a new section")
            section = line[:-1]
            data[section] = []
            continue

        # New entry, e.g.
        # `  -h, --help            show this help message and exit`
        if re.compile(r"^  \S").match(line):
            # ["-h, --help", "          show this help message and exit"]
            if "  " in line.strip():
                arg_input, arg_desc = line.strip().split("  ", 1)
            else:
                arg_input = line.strip()
                arg_desc = ""

            # ["-h", "--help"]
            arg_inputs = arg_input.split(", ")
            arg = {
                "names": arg_inputs,
                "desc": arg_desc.strip(),
            }
            data[section].append(arg)

        # Description of argument that was defined on the previous line(s). E.g.
        # `                        your Django settings.`
        else:
            # Append the description to the last argument
            desc = line.strip()
            data[section][-1]["desc"] += " " + desc

    return data


def _format_command_args(cmd_parser: ArgumentParser):
    cmd_inputs: str = _gen_command_args(cmd_parser)
    parsed_cmd_inputs = _parse_command_args(cmd_inputs)

    formatted_args = ""
    for section, args in parsed_cmd_inputs.items():
        formatted_args += f"**{section.title()}:**\n\n"
        for arg in args:
            formatted_args += (
                "- " + ", ".join([f"`{name}`" for name in arg["names"]]) + f"\n    - {arg['desc']}" + "\n"
            )
        formatted_args += "\n"

    return formatted_args


def _is_component_cls(obj: Any) -> bool:
    return inspect.isclass(obj) and issubclass(obj, Component) and obj is not Component


def _is_error_cls(obj: Any) -> bool:
    return inspect.isclass(obj) and issubclass(obj, Exception) and obj is not Exception


def _is_tag_formatter_cls(obj: Any) -> bool:
    return inspect.isclass(obj) and issubclass(obj, TagFormatterABC) and obj is not TagFormatterABC


def _is_tag_formatter_instance(obj: Any) -> bool:
    return isinstance(obj, TagFormatterABC)


def _is_template_tag(obj: Any) -> bool:
    return callable(obj) and hasattr(obj, "_tag_spec")


def gen_reference():
    """The entrypoint to generate all the reference documentation."""
    gen_reference_api()
    gen_reference_exceptions()
    gen_reference_components()
    gen_reference_middlewares()
    gen_reference_settings()
    gen_reference_tagformatters()
    gen_reference_urls()
    gen_reference_commands()
    gen_reference_templatetags()
    gen_reference_templatevars()


# This is run when `gen-files` plugin is run in mkdocs.yml
gen_reference()
