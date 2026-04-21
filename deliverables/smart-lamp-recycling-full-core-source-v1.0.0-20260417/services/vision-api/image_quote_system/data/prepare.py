from __future__ import annotations

from pathlib import Path
from typing import Any

from ..annotation.pipeline import export_annotations, prelabel_directory
from ..config import load_config
from ..io_utils import ensure_dir, save_json, write_csv_rows
from .catalog import load_catalog
from .sample_data import generate_sample_assets


def prepare_data(config_dir: str | Path = "configs", auto_approve_sample: bool = True) -> dict[str, Any]:
    config = load_config(config_dir)
    root = Path(config["project"]["root_dir"]).resolve()
    ensure_dir(root / "artifacts")

    catalog_rows = load_catalog(root / config["paths"]["catalog_csv"])
    sample_summary = generate_sample_assets(root, catalog_rows, config["pricing"])
    baseline_cases_path = root / config["paths"]["baseline_cases_csv"]
    write_csv_rows(
        baseline_cases_path,
        sample_summary["baseline_cases"],
        fieldnames=[
            "case_id",
            "split",
            "query_image",
            "expected_sku_id",
            "expected_bbox_xyxy",
            "expected_quote",
            "expected_material",
            "expected_size_band",
            "expected_craft",
            "expected_risk_level",
            "detector_version",
            "index_version",
            "pricing_version",
        ],
    )

    annotation_summary = prelabel_directory(
        raw_dir=root / config["paths"]["raw_dir"],
        annotation_dir=root / config["paths"]["annotation_dir"],
        category_name=config["project"]["default_category_name"],
        config=config,
        auto_approve=auto_approve_sample,
        reviewer="system-sample-generator" if auto_approve_sample else "",
    )
    export_summary = export_annotations(
        annotation_dir=root / config["paths"]["annotation_dir"],
        dataset_dir=root / config["paths"]["detection_dataset_dir"],
        exports_dir=root / config["paths"]["annotation_exports_dir"],
        category_name=config["project"]["default_category_name"],
    )

    manifest_path = root / "data" / "manifests" / "prepared_data_summary.json"
    summary = {
        "sample_assets": sample_summary,
        "baseline_cases_csv": str(baseline_cases_path.resolve()),
        "annotations": annotation_summary,
        "exports": export_summary,
    }
    save_json(manifest_path, summary)
    return summary
