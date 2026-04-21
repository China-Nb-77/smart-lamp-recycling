from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from ..io_utils import ensure_dir


MATERIAL_COLORS = {
    "aluminum": (156, 163, 175),
    "brass": (203, 157, 47),
    "glass": (112, 183, 214),
}


def _size_scale(size_band: str) -> float:
    return {"S": 0.82, "M": 1.0, "L": 1.18}.get(size_band, 1.0)


def _draw_hanging_lamp(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, fill: tuple[int, int, int]) -> list[int]:
    top = cy - int(90 * scale)
    bottom = cy + int(65 * scale)
    width = int(110 * scale)
    draw.line((cx, top - int(60 * scale), cx, top), fill=(60, 60, 60), width=max(2, int(5 * scale)))
    draw.rounded_rectangle(
        (cx - width, top, cx + width, bottom),
        radius=int(28 * scale),
        fill=fill,
        outline=(70, 70, 70),
        width=max(2, int(4 * scale)),
    )
    draw.ellipse(
        (cx - int(26 * scale), bottom - int(10 * scale), cx + int(26 * scale), bottom + int(24 * scale)),
        fill=(248, 233, 178),
        outline=(90, 90, 90),
    )
    return [cx - width, top - int(60 * scale), cx + width, bottom + int(24 * scale)]


def _draw_floor_lamp(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, fill: tuple[int, int, int]) -> list[int]:
    pole_top = cy - int(120 * scale)
    pole_bottom = cy + int(125 * scale)
    draw.line((cx, pole_top, cx, pole_bottom), fill=(55, 55, 55), width=max(3, int(7 * scale)))
    shade = [cx - int(85 * scale), pole_top - int(10 * scale), cx + int(85 * scale), pole_top + int(105 * scale)]
    draw.polygon(
        [
            (shade[0] + int(18 * scale), shade[1]),
            (shade[2] - int(18 * scale), shade[1]),
            (shade[2], shade[3]),
            (shade[0], shade[3]),
        ],
        fill=fill,
        outline=(60, 60, 60),
    )
    draw.ellipse(
        (cx - int(70 * scale), pole_bottom - int(14 * scale), cx + int(70 * scale), pole_bottom + int(14 * scale)),
        fill=(75, 75, 75),
    )
    return [shade[0], shade[1], shade[2], pole_bottom + int(16 * scale)]


def _draw_wall_lamp(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, fill: tuple[int, int, int]) -> list[int]:
    left = cx - int(130 * scale)
    right = cx + int(90 * scale)
    top = cy - int(95 * scale)
    draw.rectangle((left, cy - int(18 * scale), left + int(26 * scale), cy + int(18 * scale)), fill=(85, 85, 85))
    draw.arc((left + int(8 * scale), top, right, top + int(175 * scale)), start=270, end=45, fill=(75, 75, 75), width=max(3, int(6 * scale)))
    draw.ellipse((right - int(90 * scale), top + int(20 * scale), right, top + int(110 * scale)), fill=fill, outline=(60, 60, 60))
    glow = (right - int(84 * scale), top + int(72 * scale), right + int(15 * scale), top + int(160 * scale))
    draw.ellipse(glow, fill=(248, 226, 154))
    return [left, top, right + int(15 * scale), top + int(160 * scale)]


STYLE_TO_DRAWER = {
    "pendant": _draw_hanging_lamp,
    "floor": _draw_floor_lamp,
    "wall": _draw_wall_lamp,
}

QUERY_VARIANTS = [
    {"suffix": "_query", "offset": 0, "split": "train", "variant_name": "base"},
    {"suffix": "_query_v1", "offset": 10, "split": "train", "variant_name": "offset-right"},
    {"suffix": "_query_v2", "offset": -12, "split": "test", "variant_name": "offset-left"},
]

MATERIAL_RESIDUAL = {"aluminum": -4.0, "brass": 12.0, "glass": 8.0}
CRAFT_RESIDUAL = {"matte": 0.0, "brushed": 5.0, "frosted": 7.0, "premium-handmade": 14.0}
VARIANT_RESIDUAL = {"base": 2.5, "offset-right": -1.5, "offset-left": 4.0}


def create_sample_lamp_image(output_path: str | Path, metadata: dict[str, Any], variant_offset: int = 0) -> list[int]:
    target = Path(output_path)
    ensure_dir(target.parent)

    canvas = Image.new("RGB", (512, 512), (247, 247, 244))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, 488, 488), radius=28, outline=(228, 228, 224), width=3)

    material = metadata["material"]
    color = MATERIAL_COLORS.get(material, (150, 150, 150))
    scale = _size_scale(metadata["size_band"])
    cx = 256 + variant_offset
    cy = 250 + int(math.sin(variant_offset) * 8)
    style = metadata.get("visual_style", "pendant")
    bbox = STYLE_TO_DRAWER[style](draw, cx, cy, scale, color)

    if metadata["craft"] == "frosted":
        for x in range(0, 512, 14):
            draw.line((x, 0, x + 80, 512), fill=(255, 255, 255), width=1)
    elif metadata["craft"] == "brushed":
        for y in range(40, 472, 11):
            draw.line((48, y, 464, y), fill=(236, 236, 230), width=1)
    elif metadata["craft"] == "premium-handmade":
        draw.arc((90, 90, 420, 420), start=20, end=140, fill=(228, 206, 138), width=5)

    canvas.save(target)
    return bbox


def generate_sample_assets(
    project_root: str | Path,
    catalog_rows: list[dict[str, Any]],
    pricing_config: dict[str, Any],
) -> dict[str, Any]:
    root = Path(project_root)
    raw_dir = ensure_dir(root / "data" / "raw")
    query_dir = ensure_dir(root / "data" / "queries")
    catalog_img_dir = ensure_dir(root / "data" / "catalog" / "images")
    evaluation_dir = ensure_dir(root / "data" / "evaluation")

    generated: list[dict[str, Any]] = []
    baseline_cases: list[dict[str, Any]] = []
    for index, row in enumerate(catalog_rows):
        catalog_img_path = root / row["image_path"]
        raw_img_path = raw_dir / f"{row['sku_id']}.png"

        create_sample_lamp_image(catalog_img_path, row, variant_offset=0)
        bbox = create_sample_lamp_image(raw_img_path, row, variant_offset=index * 8)
        default_query_path = query_dir / f"{row['sku_id']}_query.png"
        create_sample_lamp_image(default_query_path, row, variant_offset=index * 10)
        generated.append(
            {
                "sku_id": row["sku_id"],
                "catalog_image": str(catalog_img_path.resolve()),
                "raw_image": str(raw_img_path.resolve()),
                "query_image": str(default_query_path.resolve()),
                "bbox_xyxy": bbox,
            }
        )

        for variant in QUERY_VARIANTS:
            query_img_path = query_dir / f"{row['sku_id']}{variant['suffix']}.png"
            variant_bbox = create_sample_lamp_image(query_img_path, row, variant_offset=index * 10 + variant["offset"])
            baseline_cases.append(
                {
                    "case_id": f"{row['sku_id']}{variant['suffix']}",
                    "split": variant["split"],
                    "query_image": str(query_img_path.relative_to(root)),
                    "expected_sku_id": row["sku_id"],
                    "expected_bbox_xyxy": json.dumps(variant_bbox, ensure_ascii=False),
                    "expected_quote": round(_expected_quote(row, pricing_config, variant["variant_name"]), 2),
                    "expected_material": row["material"],
                    "expected_size_band": row["size_band"],
                    "expected_craft": row["craft"],
                    "expected_risk_level": row["risk_level"],
                    "detector_version": "rtdetr-lamp",
                    "index_version": "catalog-v1",
                    "pricing_version": "rule-v1",
                }
            )

    return {
        "raw_dir": str(raw_dir.resolve()),
        "query_dir": str(query_dir.resolve()),
        "catalog_image_dir": str(catalog_img_dir.resolve()),
        "evaluation_dir": str(evaluation_dir.resolve()),
        "generated_items": generated,
        "baseline_cases": baseline_cases,
    }


def _expected_quote(metadata: dict[str, Any], pricing_config: dict[str, Any], variant_name: str) -> float:
    base_price = float(metadata["base_price"])
    material_coeff = float(pricing_config["material_coefficients"][metadata["material"]])
    size_coeff = float(pricing_config["size_coefficients"][metadata["size_band"]])
    craft_coeff = float(pricing_config["craft_coefficients"][metadata["craft"]])
    risk_level_coeff = float(pricing_config["risk_level_coefficients"][metadata["risk_level"]])
    rule_base = base_price * material_coeff * size_coeff * craft_coeff * risk_level_coeff
    residual = (
        MATERIAL_RESIDUAL.get(metadata["material"], 0.0)
        + CRAFT_RESIDUAL.get(metadata["craft"], 0.0)
        + VARIANT_RESIDUAL.get(variant_name, 0.0)
    )
    return max(rule_base + residual, 0.0)
