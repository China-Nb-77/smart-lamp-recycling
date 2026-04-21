from __future__ import annotations

from pathlib import Path

from backend.app.main import create_app, serve_api as _serve_api
from backend.app.config import load_settings

__all__ = ["build_lamp_type_server", "serve_lamp_type_api"]


def build_lamp_type_server(
    host: str = "127.0.0.1",
    port: int = 8090,
    project_root: str | Path = ".",
    model_id: str | None = None,
    candidate_labels: list[str] | None = None,
):
    del host, port, project_root, model_id, candidate_labels
    return create_app()


def serve_lamp_type_api(
    host: str = "127.0.0.1",
    port: int = 8090,
    project_root: str | Path = ".",
    model_id: str | None = None,
    candidate_labels: list[str] | None = None,
) -> None:
    del project_root, model_id, candidate_labels
    _serve_api(host=host, port=port)

