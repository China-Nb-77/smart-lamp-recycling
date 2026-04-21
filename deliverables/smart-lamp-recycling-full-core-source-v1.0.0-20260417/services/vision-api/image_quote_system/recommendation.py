from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config
from .data.catalog import load_catalog


def recommend_replacement_lamps(
    *,
    reference_sku_id: str,
    preferences: dict[str, str] | None = None,
    config_dir: str | Path = "configs",
    limit: int = 3,
) -> dict[str, Any]:
    config = load_config(config_dir)
    root = Path(config["project"]["root_dir"]).resolve()
    catalog = load_catalog(root / config["paths"]["catalog_csv"])
    preferences = preferences or {}

    anchor = next((item for item in catalog if item.get("sku_id") == reference_sku_id), None)
    if anchor is None:
        raise ValueError(f"reference_sku_id not found in catalog: {reference_sku_id}")

    preferred_install_type = str(preferences.get("install_type", "any"))
    ranked = []
    has_same_style_candidate = False
    for item in catalog:
        if item.get("sku_id") == reference_sku_id:
            continue
        if preferred_install_type != "any" and item.get("visual_style") == preferred_install_type:
            has_same_style_candidate = True
        score, reasons = _score_candidate(item, anchor, preferences)
        ranked.append(
            {
                "sku_id": str(item.get("sku_id", "")),
                "title": str(item.get("title", "")),
                "image_path": str(item.get("image_path", "")),
                "visual_style": str(item.get("visual_style", "")),
                "material": str(item.get("material", "")),
                "size_band": str(item.get("size_band", "")),
                "craft": str(item.get("craft", "")),
                "base_price": round(float(item.get("base_price", 0.0)), 2),
                "fit_score": round(score, 4),
                "recommendation_reasons": reasons,
            }
        )

    if (
        preferred_install_type != "any"
        and anchor.get("visual_style") == preferred_install_type
        and not has_same_style_candidate
    ):
        score, reasons = _score_candidate(anchor, anchor, preferences)
        ranked.append(
            {
                "sku_id": str(anchor.get("sku_id", "")),
                "title": str(anchor.get("title", "")),
                "image_path": str(anchor.get("image_path", "")),
                "visual_style": str(anchor.get("visual_style", "")),
                "material": str(anchor.get("material", "")),
                "size_band": str(anchor.get("size_band", "")),
                "craft": str(anchor.get("craft", "")),
                "base_price": round(float(anchor.get("base_price", 0.0)), 2),
                "fit_score": round(score + 0.3, 4),
                "recommendation_reasons": reasons + ["当前训练库暂无其他同类款式，优先保留同款作为主推荐。"],
            }
        )

    ranked.sort(key=lambda item: item["fit_score"], reverse=True)
    if not ranked:
        score, reasons = _score_candidate(anchor, anchor, preferences)
        ranked = [
            {
                "sku_id": str(anchor.get("sku_id", "")),
                "title": str(anchor.get("title", "")),
                "image_path": str(anchor.get("image_path", "")),
                "visual_style": str(anchor.get("visual_style", "")),
                "material": str(anchor.get("material", "")),
                "size_band": str(anchor.get("size_band", "")),
                "craft": str(anchor.get("craft", "")),
                "base_price": round(float(anchor.get("base_price", 0.0)), 2),
                "fit_score": round(score, 4),
                "recommendation_reasons": reasons + ["当前目录候选较少，保留原相似款作为兜底推荐。"],
            }
        ]

    return {
        "reference": {
            "sku_id": str(anchor.get("sku_id", "")),
            "title": str(anchor.get("title", "")),
            "visual_style": str(anchor.get("visual_style", "")),
            "material": str(anchor.get("material", "")),
            "size_band": str(anchor.get("size_band", "")),
            "craft": str(anchor.get("craft", "")),
            "base_price": round(float(anchor.get("base_price", 0.0)), 2),
        },
        "preferences": {
            "install_type": str(preferences.get("install_type", "any")),
            "budget_level": str(preferences.get("budget_level", "balanced")),
            "material": str(preferences.get("material", "any")),
        },
        "recommendations": ranked[:limit],
    }


def _score_candidate(
    candidate: dict[str, Any],
    anchor: dict[str, Any],
    preferences: dict[str, str],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if candidate.get("visual_style") == anchor.get("visual_style"):
        score += 2.4
        reasons.append("和识别出的旧灯类型接近，上手替换成本更低。")
    if candidate.get("material") == anchor.get("material"):
        score += 1.4
        reasons.append("材质延续旧灯风格，整体观感更统一。")
    if candidate.get("size_band") == anchor.get("size_band"):
        score += 1.0
        reasons.append("尺寸档位接近，适配原安装位置更稳。")
    if candidate.get("craft") == anchor.get("craft"):
        score += 0.8
        reasons.append("工艺质感接近，换新后风格落差更小。")

    install_type = preferences.get("install_type", "any")
    if install_type != "any":
        if candidate.get("visual_style") == install_type:
            score += 2.2
            reasons.append(f"符合你偏好的{_install_type_label(install_type)}类型。")
        else:
            score -= 0.7

    preferred_material = preferences.get("material", "any")
    if preferred_material != "any":
        if candidate.get("material") == preferred_material:
            score += 1.8
            reasons.append(f"材质命中你的偏好：{_material_label(preferred_material)}。")
        else:
            score -= 0.4

    candidate_price = float(candidate.get("base_price", 0.0))
    anchor_price = float(anchor.get("base_price", 0.0))
    budget_level = preferences.get("budget_level", "balanced")
    if budget_level == "economy":
        if candidate_price <= anchor_price:
            score += 1.9
            reasons.append("价格低于或接近旧灯对应款，适合优先控制预算。")
        else:
            score -= min((candidate_price - anchor_price) / max(anchor_price, 1.0), 1.2)
    elif budget_level == "premium":
        if candidate_price >= anchor_price:
            score += 1.9
            reasons.append("价格和配置更偏升级路线，适合换新提升。")
        else:
            score += 0.2
    else:
        price_gap_ratio = abs(candidate_price - anchor_price) / max(anchor_price, 1.0)
        score += max(1.6 - price_gap_ratio * 2.0, 0.1)
        reasons.append("价格梯度相对平衡，适合作为常规换新方案。")

    return score, reasons[:3]


def _install_type_label(value: str) -> str:
    return {
        "pendant": "吊灯",
        "wall": "壁灯",
        "floor": "落地灯",
    }.get(value, value)


def _material_label(value: str) -> str:
    return {
        "aluminum": "铝",
        "glass": "玻璃",
        "brass": "铜",
    }.get(value, value)
