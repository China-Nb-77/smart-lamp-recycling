from __future__ import annotations

from pathlib import Path

from .config import load_config
from .data.catalog import load_catalog
from .detection.yolo_transformer import YoloTransformerDetector
from .embedding.openclip_embedder import OpenClipEmbedder
from .io_utils import ensure_dir, save_json
from .pricing.rules import RuleBasedPricer
from .retrieval.faiss_index import FaissCatalogIndex
from .types import QuoteResult


def quote_single_image(
    image_path: str | Path,
    config_dir: str | Path = "configs",
    topk: int | None = None,
    output_path: str | Path | None = None,
    config_override: dict | None = None,
    save_output: bool = True,
) -> QuoteResult:
    config = config_override or load_config(config_dir)
    root = Path(config["project"]["root_dir"]).resolve()
    image_path = Path(image_path).resolve()

    detector = YoloTransformerDetector(config)
    detection_result = detector.infer(image_path)

    quote_dir = ensure_dir(root / config["paths"]["quote_artifact_dir"] / image_path.stem)
    detector.save_crops(image_path, detection_result.detections, quote_dir)

    embedder = OpenClipEmbedder(config)
    index_path = root / config["retrieval"]["faiss_index_path"]
    meta_path = root / config["retrieval"]["faiss_meta_path"]
    index = FaissCatalogIndex(index_path, meta_path)
    if not index_path.exists() or not meta_path.exists():
        catalog_rows = load_catalog(root / config["paths"]["catalog_csv"])
        vectors = [embedder.embed_image(root / row["image_path"]) for row in catalog_rows]
        index.build(vectors, catalog_rows)
    index.load()

    pricer = RuleBasedPricer(config)
    topk_value = topk or int(config["retrieval"].get("topk", 3))
    retrieval_preview = []
    line_items = []
    for index_id, detection in enumerate(detection_result.detections):
        if not detection.crop_path:
            continue
        vector = embedder.embed_image(detection.crop_path)
        hits = index.search(vector, topk=topk_value)
        retrieval_preview.append(hits)
        line_items.append(pricer.quote_detection(index_id, detection, hits))

    subtotal_before_residual = round(sum(item.rule_quote for item in line_items), 2)
    residual_total = round(sum(item.residual_adjustment for item in line_items), 2)
    total_quote = round(sum(item.final_quote for item in line_items), 2)
    result = QuoteResult(
        image_path=str(image_path),
        detection_backend=detection_result.backend,
        embedding_backend=embedder.backend_name,
        retrieval_backend=index.backend_name,
        currency=pricer.currency,
        total_quote=total_quote,
        price_summary={
            "line_item_count": len(line_items),
            "subtotal_before_residual": subtotal_before_residual,
            "residual_total": residual_total,
            "total_quote": total_quote,
            "currency": pricer.currency,
        },
        detection_summary={
            "backend": detection_result.backend,
            "used_fallback": detection_result.used_fallback,
            "notes": detection_result.notes,
            "detections": [
                {
                    "detection_index": idx,
                    "bbox_xyxy": detection.bbox_xyxy,
                    "confidence": round(float(detection.confidence), 4),
                    "label": detection.label,
                    "area_ratio": round(float(detection.area_ratio), 4),
                    "crop_path": detection.crop_path,
                }
                for idx, detection in enumerate(detection_result.detections)
            ],
        },
        line_items=line_items,
        retrieval_preview=retrieval_preview,
    )

    payload = {
        "quote": result.to_dict(),
        "detection": detection_result.to_dict(),
    }
    if save_output:
        save_json(output_path or quote_dir / "quote_result.json", payload)
    return result
