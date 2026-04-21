from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DetectionBox:
    bbox_xyxy: list[float]
    confidence: float
    class_id: int
    label: str
    feature: list[float]
    area_ratio: float
    crop_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DetectionResult:
    image_path: str
    image_size: list[int]
    backend: str
    used_fallback: bool
    detections: list[DetectionBox] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "image_size": self.image_size,
            "backend": self.backend,
            "used_fallback": self.used_fallback,
            "notes": self.notes,
            "detections": [d.to_dict() for d in self.detections],
        }


@dataclass
class RetrievalHit:
    rank: int
    score: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimilarProduct:
    rank: int
    sku_id: str
    title: str
    similarity_score: float
    base_price: float
    material: str
    size_band: str
    craft: str
    risk_level: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuleHit:
    rule_id: str
    rule_name: str
    category: str
    operator: str
    applied: bool
    value: float
    impact_amount: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuoteLineItem:
    detection_index: int
    matched_sku_id: str
    title: str
    base_price: float
    material_coefficient: float
    size_coefficient: float
    craft_coefficient: float
    risk_multiplier: float
    rule_quote: float
    residual_adjustment: float
    final_quote: float
    similarity_score: float
    detection_confidence: float
    matched_product: dict[str, Any]
    topk_similar_items: list[SimilarProduct]
    applied_rules: list[RuleHit]
    price_composition: dict[str, Any]
    breakdown: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "detection_index": self.detection_index,
            "matched_sku_id": self.matched_sku_id,
            "title": self.title,
            "base_price": self.base_price,
            "material_coefficient": self.material_coefficient,
            "size_coefficient": self.size_coefficient,
            "craft_coefficient": self.craft_coefficient,
            "risk_multiplier": self.risk_multiplier,
            "rule_quote": self.rule_quote,
            "residual_adjustment": self.residual_adjustment,
            "final_quote": self.final_quote,
            "similarity_score": self.similarity_score,
            "detection_confidence": self.detection_confidence,
            "matched_product": self.matched_product,
            "topk_similar_items": [item.to_dict() for item in self.topk_similar_items],
            "applied_rules": [item.to_dict() for item in self.applied_rules],
            "price_composition": self.price_composition,
            "breakdown": self.breakdown,
        }


@dataclass
class QuoteResult:
    image_path: str
    detection_backend: str
    embedding_backend: str
    retrieval_backend: str
    currency: str
    total_quote: float
    price_summary: dict[str, Any]
    detection_summary: dict[str, Any]
    line_items: list[QuoteLineItem]
    retrieval_preview: list[list[RetrievalHit]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "detection_backend": self.detection_backend,
            "embedding_backend": self.embedding_backend,
            "retrieval_backend": self.retrieval_backend,
            "currency": self.currency,
            "total_quote": self.total_quote,
            "price_summary": self.price_summary,
            "detection_summary": self.detection_summary,
            "line_items": [item.to_dict() for item in self.line_items],
            "retrieval_preview": [
                [hit.to_dict() for hit in hit_group] for hit_group in self.retrieval_preview
            ],
        }
