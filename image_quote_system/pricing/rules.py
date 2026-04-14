from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..types import DetectionBox, QuoteLineItem, RetrievalHit, RuleHit, SimilarProduct
from .residual import ResidualAdjuster
from .residual_features import build_residual_feature_dict


class RuleBasedPricer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config["pricing"]
        self.currency = self.config.get("currency", "CNY")
        residual_cfg = deepcopy(self.config.get("residual_model", {}))
        project_root = config["project"]["root_dir"]
        for key in ["model_path", "model_meta_path", "training_data_path", "training_report_path"]:
            if residual_cfg.get(key):
                target = Path(residual_cfg[key])
                if not target.is_absolute():
                    target = (Path(project_root) / target).resolve()
                residual_cfg[key] = str(target)
        self.residual_adjuster = ResidualAdjuster(residual_cfg)

    def quote_detection(
        self,
        detection_index: int,
        detection: DetectionBox,
        retrieval_hits: list[RetrievalHit],
    ) -> QuoteLineItem:
        if not retrieval_hits:
            raise ValueError("retrieval_hits cannot be empty")

        top_hit = retrieval_hits[0]
        metadata = top_hit.metadata
        base_price = float(metadata[self.config.get("base_price_field", "base_price")])
        material_coeff = self._lookup("material_coefficients", metadata.get("material"), 1.0)
        size_coeff = self._lookup("size_coefficients", metadata.get("size_band"), 1.0)
        craft_coeff = self._lookup("craft_coefficients", metadata.get("craft"), 1.0)
        risk_level_coeff = self._lookup("risk_level_coefficients", metadata.get("risk_level"), 1.0)
        risk_penalties = self._risk_penalties(detection, top_hit.score)
        dynamic_penalty = sum(item["rate"] for item in risk_penalties)
        risk_multiplier = round(risk_level_coeff * (1.0 + dynamic_penalty), 4)

        after_material = base_price * material_coeff
        material_adjustment = after_material - base_price
        after_size = after_material * size_coeff
        size_adjustment = after_size - after_material
        after_craft = after_size * craft_coeff
        craft_adjustment = after_craft - after_size
        after_risk_level = after_craft * risk_level_coeff
        risk_level_adjustment = after_risk_level - after_craft
        dynamic_adjustments = [after_risk_level * item["rate"] for item in risk_penalties]
        risk_adjustment = sum(dynamic_adjustments)
        rule_quote = after_risk_level + risk_adjustment

        residual_features = build_residual_feature_dict(
            metadata=metadata,
            detection=detection,
            similarity_score=float(top_hit.score),
            base_price=base_price,
            material_coeff=material_coeff,
            size_coeff=size_coeff,
            craft_coeff=craft_coeff,
            risk_multiplier=risk_multiplier,
            rule_quote=rule_quote,
        )
        residual = self.residual_adjuster.predict(residual_features)
        final_quote = round(max(rule_quote + residual, 0.0), 2)

        topk_similar_items = [
            SimilarProduct(
                rank=hit.rank,
                sku_id=str(hit.metadata.get("sku_id", "")),
                title=str(hit.metadata.get("title", "")),
                similarity_score=round(float(hit.score), 4),
                base_price=round(float(hit.metadata.get(self.config.get("base_price_field", "base_price"), 0.0)), 2),
                material=str(hit.metadata.get("material", "")),
                size_band=str(hit.metadata.get("size_band", "")),
                craft=str(hit.metadata.get("craft", "")),
                risk_level=str(hit.metadata.get("risk_level", "")),
                metadata=hit.metadata,
            )
            for hit in retrieval_hits
        ]
        applied_rules = [
            RuleHit(
                rule_id="base_price",
                rule_name="基础价",
                category="base",
                operator="set",
                applied=True,
                value=round(base_price, 4),
                impact_amount=round(base_price, 2),
                description="基础报价来自检索命中的 Top1 商品 base_price 字段。",
            ),
            RuleHit(
                rule_id="material_coefficient",
                rule_name="材质系数",
                category="multiplier",
                operator="multiply",
                applied=True,
                value=round(material_coeff, 4),
                impact_amount=round(material_adjustment, 2),
                description=f"材质 {metadata.get('material')} 对基础价施加倍率。",
            ),
            RuleHit(
                rule_id="size_coefficient",
                rule_name="尺寸系数",
                category="multiplier",
                operator="multiply",
                applied=True,
                value=round(size_coeff, 4),
                impact_amount=round(size_adjustment, 2),
                description=f"尺寸档位 {metadata.get('size_band')} 对当前价格施加倍率。",
            ),
            RuleHit(
                rule_id="craft_coefficient",
                rule_name="工艺系数",
                category="multiplier",
                operator="multiply",
                applied=True,
                value=round(craft_coeff, 4),
                impact_amount=round(craft_adjustment, 2),
                description=f"工艺 {metadata.get('craft')} 对当前价格施加倍率。",
            ),
            RuleHit(
                rule_id="risk_level_coefficient",
                rule_name="风险等级系数",
                category="risk",
                operator="multiply",
                applied=True,
                value=round(risk_level_coeff, 4),
                impact_amount=round(risk_level_adjustment, 2),
                description=f"风险等级 {metadata.get('risk_level')} 的基准风险倍率。",
            ),
        ]
        for item, impact_amount in zip(risk_penalties, dynamic_adjustments):
            applied_rules.append(
                RuleHit(
                    rule_id=item["rule_id"],
                    rule_name=item["rule_name"],
                    category="risk",
                    operator="add",
                    applied=bool(item["applied"]),
                    value=round(float(item["rate"]), 4),
                    impact_amount=round(float(impact_amount), 2),
                    description=item["description"],
                )
            )
        applied_rules.append(
            RuleHit(
                rule_id="residual_adjustment",
                rule_name="LightGBM 残差修正",
                category="residual",
                operator="add",
                applied=self.residual_adjuster.active,
                value=round(float(residual), 4),
                impact_amount=round(float(residual), 2),
                description="残差模型启用时，对规则报价做最终修正；未启用时为 0。",
            )
        )

        price_composition = {
            "base_price": round(base_price, 2),
            "after_material": round(after_material, 2),
            "material_adjustment": round(material_adjustment, 2),
            "after_size": round(after_size, 2),
            "size_adjustment": round(size_adjustment, 2),
            "after_craft": round(after_craft, 2),
            "craft_adjustment": round(craft_adjustment, 2),
            "after_risk_level": round(after_risk_level, 2),
            "risk_level_adjustment": round(risk_level_adjustment, 2),
            "risk_penalty_adjustment": round(risk_adjustment, 2),
            "subtotal_before_residual": round(rule_quote, 2),
            "residual_adjustment": round(residual, 2),
            "final_quote": final_quote,
        }
        breakdown = {
            "formula": "base_price * material_coeff * size_coeff * craft_coeff * risk_multiplier + residual",
            "material": metadata.get("material"),
            "size_band": metadata.get("size_band"),
            "craft": metadata.get("craft"),
            "risk_level": metadata.get("risk_level"),
            "dynamic_risk_penalty": round(dynamic_penalty, 4),
            "residual_model_active": self.residual_adjuster.active,
            "hit_rules": [item.rule_id for item in applied_rules if item.applied],
            "residual_feature_order": sorted(residual_features.keys()),
            "residual_features": {key: round(float(value), 6) for key, value in residual_features.items()},
        }
        return QuoteLineItem(
            detection_index=detection_index,
            matched_sku_id=str(metadata.get("sku_id", "")),
            title=str(metadata.get("title", "")),
            base_price=round(base_price, 2),
            material_coefficient=material_coeff,
            size_coefficient=size_coeff,
            craft_coefficient=craft_coeff,
            risk_multiplier=risk_multiplier,
            rule_quote=round(rule_quote, 2),
            residual_adjustment=round(residual, 2),
            final_quote=final_quote,
            similarity_score=round(float(top_hit.score), 4),
            detection_confidence=round(float(detection.confidence), 4),
            matched_product=topk_similar_items[0].to_dict(),
            topk_similar_items=topk_similar_items,
            applied_rules=applied_rules,
            price_composition=price_composition,
            breakdown=breakdown,
        )

    def _lookup(self, section: str, key: str | None, default: float) -> float:
        return float(self.config.get(section, {}).get(key, default))

    def _risk_penalties(self, detection: DetectionBox, similarity_score: float) -> list[dict[str, Any]]:
        risk_cfg = self.config.get("risk", {})
        low_conf_applied = detection.confidence < risk_cfg.get("low_conf_threshold", 0.45)
        low_similarity_applied = similarity_score < risk_cfg.get("low_similarity_threshold", 0.22)
        large_roi_applied = detection.area_ratio > risk_cfg.get("large_roi_threshold", 0.35)
        return [
            {
                "rule_id": "low_conf_penalty",
                "rule_name": "低置信风险修正",
                "rate": float(risk_cfg.get("low_conf_penalty", 0.08)) if low_conf_applied else 0.0,
                "applied": low_conf_applied,
                "description": f"检测置信度 {detection.confidence:.4f} 低于阈值时增加风险修正。",
            },
            {
                "rule_id": "low_similarity_penalty",
                "rule_name": "低相似度风险修正",
                "rate": float(risk_cfg.get("low_similarity_penalty", 0.06)) if low_similarity_applied else 0.0,
                "applied": low_similarity_applied,
                "description": f"Top1 相似度 {similarity_score:.4f} 低于阈值时增加风险修正。",
            },
            {
                "rule_id": "large_roi_penalty",
                "rule_name": "大目标风险修正",
                "rate": float(risk_cfg.get("large_roi_penalty", 0.03)) if large_roi_applied else 0.0,
                "applied": large_roi_applied,
                "description": f"ROI 面积占比 {detection.area_ratio:.4f} 超过阈值时增加风险修正。",
            },
        ]
