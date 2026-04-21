from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np

from ..config import load_config
from ..io_utils import read_csv_rows, save_json
from ..pipeline import quote_single_image

try:
    import lightgbm as lgb  # type: ignore

    HAS_LIGHTGBM = True
except ImportError:
    lgb = None
    HAS_LIGHTGBM = False


def train_residual_model(
    config_dir: str | Path = "configs",
    baseline_csv: str | Path | None = None,
    num_boost_round: int = 50,
) -> dict[str, Any]:
    if not HAS_LIGHTGBM:
        return {"status": "placeholder", "reason": "lightgbm not installed"}

    config = load_config(config_dir)
    root = Path(config["project"]["root_dir"]).resolve()
    residual_cfg = config["pricing"]["residual_model"]
    baseline_path = Path(baseline_csv) if baseline_csv else root / residual_cfg["training_data_path"]
    cases = read_csv_rows(baseline_path)

    rule_only_config = deepcopy(config)
    rule_only_config["pricing"]["residual_model"]["enabled"] = False

    rows: list[dict[str, Any]] = []
    feature_order: list[str] | None = None
    for case in cases:
        result = quote_single_image(
            image_path=root / case["query_image"],
            config_override=rule_only_config,
            topk=3,
            save_output=False,
        )
        if not result.line_items:
            continue
        item = result.line_items[0]
        feature_names = sorted(item.breakdown["residual_feature_order"])
        feature_dict = {
            name: float(item.breakdown["residual_features"][name]) if "residual_features" in item.breakdown else 0.0
            for name in feature_names
        }
        if not feature_dict:
            feature_dict = _extract_feature_dict(item)
            feature_names = sorted(feature_dict.keys())
        feature_order = feature_names
        rows.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "expected_quote": float(case["expected_quote"]),
                "rule_quote": float(item.rule_quote),
                "target_residual": float(case["expected_quote"]) - float(item.rule_quote),
                "features": feature_dict,
            }
        )

    if not rows:
        return {"status": "error", "reason": "no usable residual training rows"}

    if feature_order is None:
        feature_order = sorted(rows[0]["features"].keys())
    x = np.asarray([[row["features"][name] for name in feature_order] for row in rows], dtype=np.float32)
    y = np.asarray([row["target_residual"] for row in rows], dtype=np.float32)

    train_indices = [idx for idx, row in enumerate(rows) if row["split"] == "train"]
    test_indices = [idx for idx, row in enumerate(rows) if row["split"] != "train"]
    if not train_indices:
        train_indices = list(range(len(rows)))

    train_data = lgb.Dataset(x[train_indices], label=y[train_indices], feature_name=feature_order)
    booster = lgb.train(
        {
            "objective": "regression",
            "metric": "l2",
            "verbosity": -1,
            "learning_rate": 0.08,
            "num_leaves": 15,
            "min_data_in_leaf": 1,
            "feature_fraction": 1.0,
            "bagging_fraction": 1.0,
            "bagging_freq": 0,
            "seed": 42,
        },
        train_data,
        num_boost_round=num_boost_round,
    )

    model_path = root / residual_cfg["model_path"]
    meta_path = root / residual_cfg["model_meta_path"]
    report_path = root / residual_cfg["training_report_path"]
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(booster.model_to_string(), encoding="utf-8")

    predictions = booster.predict(x)
    final_quotes = np.asarray([row["rule_quote"] for row in rows], dtype=np.float32) + predictions
    expected_quotes = np.asarray([row["expected_quote"] for row in rows], dtype=np.float32)

    meta_payload = {
        "feature_order": feature_order,
        "model_path": str(model_path.resolve()),
        "baseline_csv": str(baseline_path.resolve()),
    }
    save_json(meta_path, meta_payload)

    report = {
        "status": "ok",
        "baseline_csv": str(baseline_path.resolve()),
        "model_path": str(model_path.resolve()),
        "model_meta_path": str(meta_path.resolve()),
        "feature_order": feature_order,
        "train_case_count": len(train_indices),
        "test_case_count": len(test_indices),
        "metrics": {
            "residual_rmse": _rmse(y, predictions),
            "final_mae": _mae(expected_quotes, final_quotes),
            "final_rmse": _rmse(expected_quotes, final_quotes),
            "final_mape": _mape(expected_quotes, final_quotes),
            "rule_only_mae": _mae(expected_quotes, np.asarray([row["rule_quote"] for row in rows], dtype=np.float32)),
        },
        "cases": [
            {
                "case_id": row["case_id"],
                "split": row["split"],
                "expected_quote": row["expected_quote"],
                "rule_quote": row["rule_quote"],
                "predicted_residual": round(float(predictions[idx]), 4),
                "predicted_final_quote": round(float(final_quotes[idx]), 2),
                "target_residual": round(float(row["target_residual"]), 4),
            }
            for idx, row in enumerate(rows)
        ],
    }
    save_json(report_path, report)
    report["training_report_path"] = str(report_path.resolve())
    return report


def _extract_feature_dict(item: Any) -> dict[str, float]:
    feature_candidates = item.breakdown.get("residual_features")
    if feature_candidates:
        return {key: float(value) for key, value in feature_candidates.items()}
    return {}


def _mae(expected: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(expected - predicted)))


def _rmse(expected: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(expected - predicted))))


def _mape(expected: np.ndarray, predicted: np.ndarray) -> float:
    denom = np.clip(np.abs(expected), 1e-6, None)
    return float(np.mean(np.abs((expected - predicted) / denom)) * 100.0)
