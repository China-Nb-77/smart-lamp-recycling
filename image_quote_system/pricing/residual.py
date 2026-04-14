from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import lightgbm as lgb  # type: ignore

    HAS_LIGHTGBM = True
except ImportError:
    lgb = None
    HAS_LIGHTGBM = False


class ResidualAdjuster:
    def __init__(self, residual_config: dict[str, Any]) -> None:
        self.config = residual_config
        self.model = None
        self.feature_order: list[str] | None = None
        if self.config.get("enabled") and HAS_LIGHTGBM and Path(self.config["model_path"]).exists():
            self.model = lgb.Booster(model_str=Path(self.config["model_path"]).read_text(encoding="utf-8"))
            meta_path = Path(self.config.get("model_meta_path", ""))
            if meta_path.exists():
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
                self.feature_order = payload.get("feature_order")

    @property
    def active(self) -> bool:
        return self.model is not None

    def predict(self, features: dict[str, float]) -> float:
        if not self.model:
            return 0.0
        feature_order = self.feature_order or sorted(features.keys())
        ordered = [[float(features[name]) for name in feature_order]]
        return float(self.model.predict(ordered)[0])
