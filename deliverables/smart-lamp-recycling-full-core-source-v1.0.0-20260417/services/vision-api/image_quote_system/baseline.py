from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_config
from .io_utils import ensure_dir, load_json, read_csv_rows, save_json, write_csv_rows
from .pipeline import quote_single_image


def evaluate_baseline(
    config_dir: str | Path = "configs",
    baseline_csv: str | Path | None = None,
    report_name: str = "baseline_report",
    topk: int = 3,
    compare_to: str | Path | None = None,
) -> dict[str, Any]:
    config = load_config(config_dir)
    root = Path(config["project"]["root_dir"]).resolve()
    report_dir = root / config["paths"]["report_dir"]
    report_dir.mkdir(parents=True, exist_ok=True)
    run_report_dir = ensure_dir(report_dir / report_name)
    baseline_path = Path(baseline_csv) if baseline_csv else root / config["paths"]["baseline_cases_csv"]
    cases = read_csv_rows(baseline_path)

    case_reports: list[dict[str, Any]] = []
    detection_ious: list[float] = []
    detection_hits: list[float] = []
    retrieval_top1_hits: list[float] = []
    retrieval_topk_hits: list[float] = []
    reciprocal_ranks: list[float] = []
    quote_rule_errors: list[float] = []
    quote_final_errors: list[float] = []
    quote_rule_sq_errors: list[float] = []
    quote_final_sq_errors: list[float] = []
    quote_rule_pct_errors: list[float] = []
    quote_final_pct_errors: list[float] = []

    for case in cases:
        expected_bbox = json.loads(case["expected_bbox_xyxy"])
        expected_quote = float(case["expected_quote"])
        result = quote_single_image(
            image_path=root / case["query_image"],
            config_override=config,
            topk=topk,
            save_output=False,
        )
        predicted_bbox = None
        predicted_conf = 0.0
        if result.detection_summary["detections"]:
            predicted_bbox = result.detection_summary["detections"][0]["bbox_xyxy"]
            predicted_conf = float(result.detection_summary["detections"][0]["confidence"])
        iou = _iou(expected_bbox, predicted_bbox) if predicted_bbox else 0.0
        detection_ious.append(iou)
        detection_hit = 1.0 if iou >= 0.5 else 0.0
        detection_hits.append(detection_hit)

        top1_sku = result.line_items[0].matched_sku_id if result.line_items else ""
        topk_items = result.line_items[0].topk_similar_items if result.line_items else []
        topk_skus = [item.sku_id for item in topk_items]
        top1_hit = 1.0 if top1_sku == case["expected_sku_id"] else 0.0
        topk_hit = 1.0 if case["expected_sku_id"] in topk_skus else 0.0
        rr = 0.0
        for rank, sku_id in enumerate(topk_skus, start=1):
            if sku_id == case["expected_sku_id"]:
                rr = 1.0 / rank
                break
        retrieval_top1_hits.append(top1_hit)
        retrieval_topk_hits.append(topk_hit)
        reciprocal_ranks.append(rr)

        rule_quote = float(result.line_items[0].rule_quote) if result.line_items else 0.0
        final_quote = float(result.total_quote)
        rule_error = abs(rule_quote - expected_quote)
        final_error = abs(final_quote - expected_quote)
        quote_rule_errors.append(rule_error)
        quote_final_errors.append(final_error)
        quote_rule_sq_errors.append(rule_error**2)
        quote_final_sq_errors.append(final_error**2)
        quote_rule_pct_errors.append(rule_error / max(abs(expected_quote), 1e-6))
        quote_final_pct_errors.append(final_error / max(abs(expected_quote), 1e-6))

        case_reports.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "query_image": case["query_image"],
                "expected_sku_id": case["expected_sku_id"],
                "predicted_top1_sku_id": top1_sku,
                "expected_quote": expected_quote,
                "rule_quote": round(rule_quote, 2),
                "final_quote": round(final_quote, 2),
                "quote_rule_abs_error": round(rule_error, 2),
                "quote_final_abs_error": round(final_error, 2),
                "expected_bbox_xyxy": expected_bbox,
                "predicted_bbox_xyxy": predicted_bbox,
                "detection_iou": round(iou, 4),
                "detection_hit_iou_0_5": bool(detection_hit),
                "detection_backend": result.detection_summary["backend"],
                "detection_used_fallback": bool(result.detection_summary["used_fallback"]),
                "detection_notes": result.detection_summary["notes"],
                "predicted_detection_confidence": round(predicted_conf, 4),
                "retrieval_top1_hit": bool(top1_hit),
                "retrieval_topk_hit": bool(topk_hit),
                "retrieval_reciprocal_rank": round(rr, 4),
                "topk_candidates": [item.to_dict() for item in topk_items],
                "applied_rules": [item.to_dict() for item in (result.line_items[0].applied_rules if result.line_items else [])],
            }
        )

    report = {
        "baseline_csv": str(baseline_path.resolve()),
        "versions": _version_summary(root, config, baseline_path),
        "metrics": {
            "detection": {
                "mean_iou": round(float(np.mean(detection_ious)), 4) if detection_ious else 0.0,
                "precision_at_iou_0_5": round(float(np.mean(detection_hits)), 4) if detection_hits else 0.0,
                "recall_at_iou_0_5": round(float(np.mean(detection_hits)), 4) if detection_hits else 0.0,
            },
            "retrieval": {
                "top1_accuracy": round(float(np.mean(retrieval_top1_hits)), 4) if retrieval_top1_hits else 0.0,
                "recall_at_k": round(float(np.mean(retrieval_topk_hits)), 4) if retrieval_topk_hits else 0.0,
                "mrr": round(float(np.mean(reciprocal_ranks)), 4) if reciprocal_ranks else 0.0,
            },
            "quote": {
                "rule_mae": round(float(np.mean(quote_rule_errors)), 4) if quote_rule_errors else 0.0,
                "final_mae": round(float(np.mean(quote_final_errors)), 4) if quote_final_errors else 0.0,
                "rule_rmse": round(float(np.sqrt(np.mean(quote_rule_sq_errors))), 4) if quote_rule_sq_errors else 0.0,
                "final_rmse": round(float(np.sqrt(np.mean(quote_final_sq_errors))), 4) if quote_final_sq_errors else 0.0,
                "rule_mape": round(float(np.mean(quote_rule_pct_errors) * 100.0), 4) if quote_rule_pct_errors else 0.0,
                "final_mape": round(float(np.mean(quote_final_pct_errors) * 100.0), 4) if quote_final_pct_errors else 0.0,
            },
        },
        "cases": case_reports,
    }

    json_path = report_dir / f"{report_name}.json"
    md_path = report_dir / f"{report_name}.md"
    save_json(json_path, report)
    md_path.write_text(_report_markdown(report), encoding="utf-8")
    report["report_json"] = str(json_path.resolve())
    report["report_markdown"] = str(md_path.resolve())
    report["report_dir"] = str(run_report_dir.resolve())
    detailed_artifacts = _write_detailed_artifacts(
        run_report_dir,
        report,
        compare_to=Path(compare_to).resolve() if compare_to else None,
    )
    report["detail_artifacts"] = detailed_artifacts
    save_json(json_path, report)
    return report


def _version_summary(root: Path, config: dict[str, Any], baseline_path: Path) -> dict[str, Any]:
    detector_weights = root / config["paths"]["detector_model_dir"] / config["detector"]["train_name"] / "best.pt"
    index_meta = root / config["retrieval"]["faiss_meta_path"]
    pricing_cfg = Path(config["config_dir"]) / "pricing.yaml"
    residual_model = root / config["pricing"]["residual_model"]["model_path"]
    return {
        "baseline_hash": _file_hash(baseline_path),
        "detector_weights": str(detector_weights.resolve()),
        "detector_hash": _file_hash(detector_weights) if detector_weights.exists() else None,
        "index_meta": str(index_meta.resolve()),
        "index_hash": _file_hash(index_meta) if index_meta.exists() else None,
        "pricing_config": str(pricing_cfg.resolve()),
        "pricing_hash": _file_hash(pricing_cfg),
        "residual_model": str(residual_model.resolve()),
        "residual_hash": _file_hash(residual_model) if residual_model.exists() else None,
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def _iou(expected_bbox: list[float], predicted_bbox: list[float] | None) -> float:
    if predicted_bbox is None:
        return 0.0
    ax1, ay1, ax2, ay2 = [float(value) for value in expected_bbox]
    bx1, by1, bx2, by2 = [float(value) for value in predicted_bbox]
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(inter_x2 - inter_x1, 0.0)
    inter_h = max(inter_y2 - inter_y1, 0.0)
    inter_area = inter_w * inter_h
    area_a = max(ax2 - ax1, 0.0) * max(ay2 - ay1, 0.0)
    area_b = max(bx2 - bx1, 0.0) * max(by2 - by1, 0.0)
    denom = area_a + area_b - inter_area
    return inter_area / denom if denom > 0 else 0.0


def _report_markdown(report: dict[str, Any]) -> str:
    detection = report["metrics"]["detection"]
    retrieval = report["metrics"]["retrieval"]
    quote = report["metrics"]["quote"]
    lines = [
        "# Baseline Report",
        "",
        "## Detection",
        f"- mean_iou: {detection['mean_iou']}",
        f"- precision_at_iou_0_5: {detection['precision_at_iou_0_5']}",
        f"- recall_at_iou_0_5: {detection['recall_at_iou_0_5']}",
        "",
        "## Retrieval",
        f"- top1_accuracy: {retrieval['top1_accuracy']}",
        f"- recall_at_k: {retrieval['recall_at_k']}",
        f"- mrr: {retrieval['mrr']}",
        "",
        "## Quote",
        f"- rule_mae: {quote['rule_mae']}",
        f"- final_mae: {quote['final_mae']}",
        f"- rule_rmse: {quote['rule_rmse']}",
        f"- final_rmse: {quote['final_rmse']}",
        f"- rule_mape: {quote['rule_mape']}",
        f"- final_mape: {quote['final_mape']}",
    ]
    return "\n".join(lines) + "\n"


def _write_detailed_artifacts(
    run_report_dir: Path,
    report: dict[str, Any],
    compare_to: Path | None = None,
) -> dict[str, Any]:
    summary_json = run_report_dir / "summary.json"
    summary_md = run_report_dir / "summary.md"
    case_overview_csv = run_report_dir / "case_overview.csv"
    detection_csv = run_report_dir / "detection_details.csv"
    retrieval_csv = run_report_dir / "retrieval_details.csv"
    quote_csv = run_report_dir / "quote_details.csv"
    rule_csv = run_report_dir / "quote_rule_details.csv"
    version_json = run_report_dir / "version_manifest.json"
    sample_md = run_report_dir / "sample_report.md"

    save_json(summary_json, report)
    summary_md.write_text(_report_markdown(report), encoding="utf-8")
    save_json(version_json, report["versions"])

    case_rows: list[dict[str, Any]] = []
    detection_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    quote_rows: list[dict[str, Any]] = []
    rule_rows: list[dict[str, Any]] = []
    for case in report["cases"]:
        case_rows.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "expected_sku_id": case["expected_sku_id"],
                "predicted_top1_sku_id": case["predicted_top1_sku_id"],
                "expected_quote": case["expected_quote"],
                "rule_quote": case["rule_quote"],
                "final_quote": case["final_quote"],
                "quote_rule_abs_error": case["quote_rule_abs_error"],
                "quote_final_abs_error": case["quote_final_abs_error"],
                "detection_iou": case["detection_iou"],
                "retrieval_top1_hit": case["retrieval_top1_hit"],
                "retrieval_topk_hit": case["retrieval_topk_hit"],
            }
        )
        detection_rows.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "detection_backend": case["detection_backend"],
                "detection_used_fallback": case["detection_used_fallback"],
                "expected_bbox_xyxy": json.dumps(case["expected_bbox_xyxy"], ensure_ascii=False),
                "predicted_bbox_xyxy": json.dumps(case["predicted_bbox_xyxy"], ensure_ascii=False),
                "detection_iou": case["detection_iou"],
                "detection_hit_iou_0_5": case["detection_hit_iou_0_5"],
                "predicted_detection_confidence": case["predicted_detection_confidence"],
                "detection_notes": " | ".join(case["detection_notes"]),
            }
        )
        quote_rows.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "expected_quote": case["expected_quote"],
                "rule_quote": case["rule_quote"],
                "final_quote": case["final_quote"],
                "quote_rule_abs_error": case["quote_rule_abs_error"],
                "quote_final_abs_error": case["quote_final_abs_error"],
                "expected_sku_id": case["expected_sku_id"],
                "predicted_top1_sku_id": case["predicted_top1_sku_id"],
                "predicted_detection_confidence": case["predicted_detection_confidence"],
                "retrieval_reciprocal_rank": case["retrieval_reciprocal_rank"],
            }
        )
        for candidate in case["topk_candidates"]:
            retrieval_rows.append(
                {
                    "case_id": case["case_id"],
                    "split": case["split"],
                    "rank": candidate["rank"],
                    "sku_id": candidate["sku_id"],
                    "title": candidate["title"],
                    "similarity_score": candidate["similarity_score"],
                    "is_expected_sku": candidate["sku_id"] == case["expected_sku_id"],
                    "is_top1_prediction": candidate["rank"] == 1,
                    "base_price": candidate["base_price"],
                    "material": candidate["material"],
                    "size_band": candidate["size_band"],
                    "craft": candidate["craft"],
                    "risk_level": candidate["risk_level"],
                }
            )
        for rule in case["applied_rules"]:
            rule_rows.append(
                {
                    "case_id": case["case_id"],
                    "split": case["split"],
                    "rule_id": rule["rule_id"],
                    "rule_name": rule["rule_name"],
                    "category": rule["category"],
                    "operator": rule["operator"],
                    "applied": rule["applied"],
                    "value": rule["value"],
                    "impact_amount": rule["impact_amount"],
                    "description": rule["description"],
                }
            )

    write_csv_rows(case_overview_csv, case_rows, fieldnames=list(case_rows[0].keys()) if case_rows else [])
    write_csv_rows(detection_csv, detection_rows, fieldnames=list(detection_rows[0].keys()) if detection_rows else [])
    write_csv_rows(retrieval_csv, retrieval_rows, fieldnames=list(retrieval_rows[0].keys()) if retrieval_rows else [])
    write_csv_rows(quote_csv, quote_rows, fieldnames=list(quote_rows[0].keys()) if quote_rows else [])
    write_csv_rows(rule_csv, rule_rows, fieldnames=list(rule_rows[0].keys()) if rule_rows else [])
    sample_md.write_text(_sample_report_markdown(report), encoding="utf-8")

    comparison_artifacts: dict[str, str] | None = None
    if compare_to is not None:
        comparison = _build_comparison_report(report, load_json(compare_to))
        comparison_json = run_report_dir / "comparison.json"
        comparison_md = run_report_dir / "comparison.md"
        save_json(comparison_json, comparison)
        comparison_md.write_text(_comparison_markdown(comparison), encoding="utf-8")
        comparison_artifacts = {
            "comparison_json": str(comparison_json.resolve()),
            "comparison_markdown": str(comparison_md.resolve()),
        }

    artifacts: dict[str, Any] = {
        "summary_json": str(summary_json.resolve()),
        "summary_markdown": str(summary_md.resolve()),
        "case_overview_csv": str(case_overview_csv.resolve()),
        "detection_csv": str(detection_csv.resolve()),
        "retrieval_csv": str(retrieval_csv.resolve()),
        "quote_csv": str(quote_csv.resolve()),
        "rule_csv": str(rule_csv.resolve()),
        "version_manifest_json": str(version_json.resolve()),
        "sample_report_markdown": str(sample_md.resolve()),
    }
    if comparison_artifacts:
        artifacts["comparison"] = comparison_artifacts
    return artifacts


def _sample_report_markdown(report: dict[str, Any]) -> str:
    cases = report["cases"]
    best_quote_cases = sorted(cases, key=lambda item: item["quote_final_abs_error"])[:3]
    worst_quote_cases = sorted(cases, key=lambda item: item["quote_final_abs_error"], reverse=True)[:3]
    low_iou_cases = sorted(cases, key=lambda item: item["detection_iou"])[:3]
    retrieval_misses = [case for case in cases if not case["retrieval_top1_hit"]]

    lines = [
        "# Sample Report",
        "",
        "## Best Quote Cases",
    ]
    for case in best_quote_cases:
        lines.append(
            f"- {case['case_id']}: final_error={case['quote_final_abs_error']}, "
            f"top1={case['predicted_top1_sku_id']}, iou={case['detection_iou']}"
        )
    lines.extend(["", "## Worst Quote Cases"])
    for case in worst_quote_cases:
        lines.append(
            f"- {case['case_id']}: final_error={case['quote_final_abs_error']}, "
            f"rule_error={case['quote_rule_abs_error']}, top1={case['predicted_top1_sku_id']}"
        )
    lines.extend(["", "## Lowest IoU Cases"])
    for case in low_iou_cases:
        lines.append(
            f"- {case['case_id']}: iou={case['detection_iou']}, "
            f"confidence={case['predicted_detection_confidence']}, backend={case['detection_backend']}"
        )
    lines.extend(["", "## Retrieval Top1 Misses"])
    if retrieval_misses:
        for case in retrieval_misses:
            lines.append(
                f"- {case['case_id']}: expected={case['expected_sku_id']}, predicted={case['predicted_top1_sku_id']}, "
                f"rr={case['retrieval_reciprocal_rank']}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _build_comparison_report(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    metric_deltas: dict[str, dict[str, float]] = {}
    for section, metrics in current["metrics"].items():
        previous_metrics = previous.get("metrics", {}).get(section, {})
        metric_deltas[section] = {}
        for key, value in metrics.items():
            previous_value = previous_metrics.get(key)
            if isinstance(value, (int, float)) and isinstance(previous_value, (int, float)):
                metric_deltas[section][key] = round(float(value) - float(previous_value), 4)

    previous_cases = {case["case_id"]: case for case in previous.get("cases", [])}
    case_deltas = []
    for case in current["cases"]:
        previous_case = previous_cases.get(case["case_id"])
        if previous_case is None:
            continue
        case_deltas.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "detection_iou_delta": round(float(case["detection_iou"]) - float(previous_case.get("detection_iou", 0.0)), 4),
                "top1_hit_delta": int(bool(case["retrieval_top1_hit"])) - int(bool(previous_case.get("retrieval_top1_hit", False))),
                "final_abs_error_delta": round(
                    float(case["quote_final_abs_error"]) - float(previous_case.get("quote_final_abs_error", 0.0)),
                    4,
                ),
                "rule_abs_error_delta": round(
                    float(case["quote_rule_abs_error"]) - float(previous_case.get("quote_rule_abs_error", 0.0)),
                    4,
                ),
            }
        )
    return {
        "current_report": current.get("report_json"),
        "previous_report": previous.get("report_json"),
        "metric_deltas": metric_deltas,
        "case_deltas": sorted(case_deltas, key=lambda item: item["case_id"]),
    }


def _comparison_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# Comparison Report",
        "",
        f"- current_report: {comparison.get('current_report') or 'n/a'}",
        f"- previous_report: {comparison.get('previous_report') or 'n/a'}",
        "",
        "## Metric Deltas",
    ]
    for section, metrics in comparison["metric_deltas"].items():
        lines.append(f"### {section}")
        if metrics:
            for key, value in metrics.items():
                lines.append(f"- {key}: {value:+.4f}")
        else:
            lines.append("- no comparable metrics")
    lines.extend(["", "## Case Deltas"])
    if comparison["case_deltas"]:
        for item in comparison["case_deltas"][:10]:
            lines.append(
                f"- {item['case_id']}: iou={item['detection_iou_delta']:+.4f}, "
                f"top1_hit={item['top1_hit_delta']:+d}, final_error={item['final_abs_error_delta']:+.4f}"
            )
    else:
        lines.append("- no overlapping cases")
    return "\n".join(lines) + "\n"
