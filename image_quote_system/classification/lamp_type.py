"""Stub for lamp type classification — used in mock/dev mode."""
from __future__ import annotations
from typing import Any

DEFAULT_LAMP_LABELS = [
    "吊灯",
    "壁灯",
    "落地灯",
    "台灯",
    "射灯",
    "筒灯",
    "荧光灯",
    "节能灯",
]


class OpenSourceLampTypeClassifier:
    model_id: str = "stub"
    backend: str = "stub"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def _classify_with_model(self, image: Any, labels: list[str]) -> list[dict[str, Any]]:
        return [{"label": label, "score": 1.0 / len(labels)} for label in labels]

    def _normalize_predictions(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return raw
