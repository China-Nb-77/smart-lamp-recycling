from __future__ import annotations


class AgentBackend:
    def __init__(self) -> None:
        raise RuntimeError(
            "Legacy AgentBackend has been replaced by the FastAPI workflow service in backend.app.service. "
            "Use backend.app.main.create_app() to serve the system."
        )

