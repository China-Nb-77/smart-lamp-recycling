from __future__ import annotations

from pathlib import Path

from backend.app.main import app, create_app, serve_api
from backend.app.config import load_settings

__all__ = ["app", "create_app", "build_server", "serve_api"]


def build_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    config_dir: str | Path = "configs",
):
    settings = load_settings()
    settings.config_dir = (settings.base_dir / Path(config_dir)).resolve()
    return create_app(settings)

