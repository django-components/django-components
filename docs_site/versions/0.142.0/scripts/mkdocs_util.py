"""Utilities for interacting with MkDocs configuration."""

from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import griffe
import yaml  # type: ignore[import-untyped]


@lru_cache
def load_config() -> Dict:
    mkdocs_config_str = Path("mkdocs.yml").read_text()
    # NOTE: Use BaseLoader to avoid resolving tags like `!ENV`
    #       See https://stackoverflow.com/questions/45966633/yaml-error-could-not-determine-a-constructor-for-the-tag
    mkdocs_config = yaml.load(mkdocs_config_str, yaml.BaseLoader)  # noqa: S506
    return mkdocs_config


@lru_cache
def find_plugin(name: str) -> Optional[Dict]:
    config = load_config()
    plugins: List[Union[str, Dict[str, Dict]]] = config.get("plugins", [])
    if not plugins:
        return None

    for plugin in plugins:
        if isinstance(plugin, str):
            plugin = {plugin: {}}  # noqa: PLW2901
        plugin_name, plugin_conf = next(iter(plugin.items()))
        if plugin_name == name:
            return plugin_conf

    return None


def get_mkdocstrings_plugin_handler_options() -> Optional[Dict]:
    plugin = find_plugin("mkdocstrings")
    if plugin is None:
        return None

    return plugin.get("handlers", {}).get("python", {}).get("options", {})


def import_object(obj: griffe.Object) -> Any:
    module = import_module(obj.module.path)
    runtime_obj = getattr(module, obj.name)
    return runtime_obj
