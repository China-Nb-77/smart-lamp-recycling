from __future__ import annotations

from typing import Any

from ..types import DetectionBox


MATERIALS = ["aluminum", "brass", "glass"]
SIZE_BANDS = ["S", "M", "L"]
CRAFTS = ["matte", "brushed", "frosted", "premium-handmade"]
RISK_LEVELS = ["low", "medium", "high"]


def build_residual_feature_dict(
    metadata: dict[str, Any],
    detection: DetectionBox,
    similarity_score: float,
    base_price: float,
    material_coeff: float,
    size_coeff: float,
    craft_coeff: float,
    risk_multiplier: float,
    rule_quote: float,
) -> dict[str, float]:
    features: dict[str, float] = {
        "base_price": float(base_price),
        "material_coeff": float(material_coeff),
        "size_coeff": float(size_coeff),
        "craft_coeff": float(craft_coeff),
        "risk_multiplier": float(risk_multiplier),
        "rule_quote": float(rule_quote),
        "similarity_score": float(similarity_score),
        "detection_confidence": float(detection.confidence),
        "area_ratio": float(detection.area_ratio),
        "width_mm": float(metadata.get("width_mm", 0.0)),
        "height_mm": float(metadata.get("height_mm", 0.0)),
    }

    material = str(metadata.get("material", ""))
    size_band = str(metadata.get("size_band", ""))
    craft = str(metadata.get("craft", ""))
    risk_level = str(metadata.get("risk_level", ""))
    for item in MATERIALS:
        features[f"material__{item}"] = 1.0 if material == item else 0.0
    for item in SIZE_BANDS:
        features[f"size_band__{item}"] = 1.0 if size_band == item else 0.0
    for item in CRAFTS:
        features[f"craft__{item}"] = 1.0 if craft == item else 0.0
    for item in RISK_LEVELS:
        features[f"risk_level__{item}"] = 1.0 if risk_level == item else 0.0
    return features

