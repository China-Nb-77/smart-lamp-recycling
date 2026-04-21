from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import load_yaml


CONFIG_FILES = [
    "system.yaml",
    "detection.yaml",
    "retrieval.yaml",
    "pricing.yaml",
    "fields.yaml",
]


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_dir: str | Path = "configs") -> dict[str, Any]:
    root = Path(config_dir)
    config: dict[str, Any] = {}
    for name in CONFIG_FILES:
        config = _merge(config, load_yaml(root / name))
    project_root = Path(config.get("project", {}).get("root_dir", "."))
    if not project_root.is_absolute():
        project_root = (root.resolve().parent / project_root).resolve()
    config.setdefault("project", {})
    config["project"]["root_dir"] = str(project_root)
    config["config_dir"] = str(root.resolve())
    return config
