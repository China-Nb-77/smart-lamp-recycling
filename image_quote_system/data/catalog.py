"""Stub for catalog data loader — used in mock/dev mode."""
from __future__ import annotations
from pathlib import Path
from typing import Any


def load_catalog(config_dir: Path | None = None) -> list[dict[str, Any]]:
    return []
