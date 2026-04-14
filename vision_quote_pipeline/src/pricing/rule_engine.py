from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class QuoteResult:
    base_similarity_price: float
    material_adjustment: float
    size_adjustment: float
    process_adjustment: float
    urgent_adjustment: float
    final_price: float
    explanation: dict[str, Any]


class RuleQuoteEngine:
    material_adjustments = {
        "metal": 20.0,
        "glass": 30.0,
        "metal+glass": 45.0,
        "acrylic": 10.0,
        "copper": 80.0,
    }
    process_adjustments = {
        "paint": 10.0,
        "plating": 25.0,
        "brushed": 18.0,
        "handmade": 60.0,
    }

    def quote_from_neighbors(
        self,
        neighbors: pd.DataFrame,
        query_meta: dict[str, Any] | None = None,
    ) -> QuoteResult:
        if neighbors.empty:
            raise ValueError("没有相似样本，无法报价")

        query_meta = query_meta or {}
        weighted_price = self._weighted_average_price(neighbors)

        material = str(query_meta.get("material", "")).strip().lower()
        process = str(query_meta.get("process", "")).strip().lower()
        size_mm = float(query_meta.get("size_mm", 0) or 0)
        urgent = bool(query_meta.get("urgent", False))

        material_adj = self.material_adjustments.get(material, 0.0)
        process_adj = self.process_adjustments.get(process, 0.0)
        size_adj = self._size_adjustment(size_mm, neighbors)
        urgent_adj = 50.0 if urgent else 0.0

        final_price = weighted_price + material_adj + process_adj + size_adj + urgent_adj
        final_price = round(max(final_price, 0.0), 2)

        return QuoteResult(
            base_similarity_price=round(weighted_price, 2),
            material_adjustment=round(material_adj, 2),
            size_adjustment=round(size_adj, 2),
            process_adjustment=round(process_adj, 2),
            urgent_adjustment=round(urgent_adj, 2),
            final_price=final_price,
            explanation={
                "neighbors": neighbors[[c for c in neighbors.columns if c != "embedding"]].to_dict(orient="records"),
                "query_meta": query_meta,
            },
        )

    @staticmethod
    def _weighted_average_price(neighbors: pd.DataFrame) -> float:
        scores = neighbors["score"].clip(lower=1e-6)
        prices = neighbors["base_price"].astype(float)
        return float((scores * prices).sum() / scores.sum())

    @staticmethod
    def _size_adjustment(size_mm: float, neighbors: pd.DataFrame) -> float:
        if size_mm <= 0 or "size_mm" not in neighbors.columns:
            return 0.0
        ref_size = float(neighbors["size_mm"].astype(float).mean())
        delta = size_mm - ref_size
        return delta * 0.15
