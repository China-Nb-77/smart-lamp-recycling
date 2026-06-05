"""Stub for system config — used in mock/dev mode."""
from __future__ import annotations
from pathlib import Path
from typing import Any


def load_config(config_dir: Path | None = None) -> dict[str, Any]:
    return {}
