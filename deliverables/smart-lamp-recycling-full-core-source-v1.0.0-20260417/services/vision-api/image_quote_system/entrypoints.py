from __future__ import annotations

import sys

from .cli import run_cli


def _run(subcommand: str) -> None:
    raise SystemExit(run_cli([subcommand, *sys.argv[1:]]))


def prepare_data_main() -> None:
    _run("prepare-data")


def train_detector_main() -> None:
    _run("train-detector")


def validate_detector_main() -> None:
    _run("validate-detector")


def export_detector_main() -> None:
    _run("export-detector")


def infer_detector_main() -> None:
    _run("infer-detector")


def build_index_main() -> None:
    _run("build-index")


def evaluate_baseline_main() -> None:
    _run("evaluate-baseline")


def train_residual_main() -> None:
    _run("train-residual")


def retrieve_similar_main() -> None:
    _run("retrieve-similar")


def quote_image_main() -> None:
    _run("quote-image")


def serve_api_main() -> None:
    _run("serve-api")


def serve_lamp_type_api_main() -> None:
    _run("serve-lamp-type-api")


def prelabel_sam3_main() -> None:
    _run("prelabel-sam3")


def download_sam3_community_main() -> None:
    _run("download-sam3-community")


def export_annotations_main() -> None:
    _run("export-annotations")


def export_training_version_main() -> None:
    _run("export-training-version")


def review_annotation_main() -> None:
    _run("review-annotation")


def audit_annotations_main() -> None:
    _run("audit-annotations")


def apply_review_decisions_main() -> None:
    _run("apply-review-decisions")
