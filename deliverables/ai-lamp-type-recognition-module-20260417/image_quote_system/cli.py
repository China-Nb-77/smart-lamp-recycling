from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .annotation.pipeline import (
    apply_review_decisions,
    export_annotations,
    export_training_version,
    generate_review_dashboard,
    prelabel_directory,
    review_annotation,
)
from .annotation.sam3_community import download_community_checkpoint
from .baseline import evaluate_baseline
from .config import load_config
from .data.catalog import load_catalog
from .data.prepare import prepare_data
from .detection.yolo_transformer import YoloTransformerDetector
from .embedding.openclip_embedder import OpenClipEmbedder
from .io_utils import save_json
from .pipeline import quote_single_image
from .pricing.residual_training import train_residual_model
from .retrieval.faiss_index import FaissCatalogIndex
from .serving.api import serve_api
from .serving.lamp_type_api import serve_lamp_type_api


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="image-quote-system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare-data")
    prepare_parser.add_argument("--config-dir", default="configs")
    prepare_parser.add_argument("--no-auto-approve", action="store_true")

    prelabel_parser = subparsers.add_parser("prelabel-sam3")
    prelabel_parser.add_argument("--config-dir", default="configs")
    prelabel_parser.add_argument("--raw-dir", required=True)
    prelabel_parser.add_argument("--annotation-dir", required=True)
    prelabel_parser.add_argument("--category-name", default="lamp")
    prelabel_parser.add_argument("--auto-approve", action="store_true")
    prelabel_parser.add_argument("--reviewer", default="")

    download_sam3_parser = subparsers.add_parser("download-sam3-community")
    download_sam3_parser.add_argument("--config-dir", default="configs")
    download_sam3_parser.add_argument("--repo-id")
    download_sam3_parser.add_argument("--filename")
    download_sam3_parser.add_argument("--revision")
    download_sam3_parser.add_argument("--output")
    download_sam3_parser.add_argument("--force", action="store_true")

    export_parser = subparsers.add_parser("export-annotations")
    export_parser.add_argument("--annotation-dir", required=True)
    export_parser.add_argument("--dataset-dir", required=True)
    export_parser.add_argument("--exports-dir", required=True)
    export_parser.add_argument("--category-name", default="lamp")

    export_training_parser = subparsers.add_parser("export-training-version")
    export_training_parser.add_argument("--config-dir", default="configs")
    export_training_parser.add_argument("--annotation-dir")
    export_training_parser.add_argument("--dataset-dir")
    export_training_parser.add_argument("--exports-dir")
    export_training_parser.add_argument("--version-root")
    export_training_parser.add_argument("--version-tag", required=True)
    export_training_parser.add_argument("--category-name")
    export_training_parser.add_argument("--decision-file")
    export_training_parser.add_argument("--reviewer", default="")
    export_training_parser.add_argument("--note", default="")
    export_training_parser.add_argument("--overwrite", action="store_true")

    review_parser = subparsers.add_parser("review-annotation")
    review_parser.add_argument("--annotation-file", required=True)
    review_parser.add_argument("--status", choices=["approved", "rejected", "pending"], required=True)
    review_parser.add_argument("--reviewer", required=True)
    review_parser.add_argument("--note", default="")

    audit_parser = subparsers.add_parser("audit-annotations")
    audit_parser.add_argument("--config-dir", default="configs")
    audit_parser.add_argument("--annotation-dir")
    audit_parser.add_argument("--output-dir")
    audit_parser.add_argument("--status-filter", choices=["pending", "approved", "rejected", "all"], default="pending")
    audit_parser.add_argument("--sample-size", type=int)
    audit_parser.add_argument("--seed", type=int, default=42)

    apply_review_parser = subparsers.add_parser("apply-review-decisions")
    apply_review_parser.add_argument("--decision-file", required=True)
    apply_review_parser.add_argument("--reviewer", required=True)

    train_parser = subparsers.add_parser("train-detector")
    train_parser.add_argument("--config-dir", default="configs")
    train_parser.add_argument("--data-yaml")
    train_parser.add_argument("--epochs", type=int, default=1)
    train_parser.add_argument("--imgsz", type=int)
    train_parser.add_argument("--batch", type=int)
    train_parser.add_argument("--project")
    train_parser.add_argument("--name")

    val_parser = subparsers.add_parser("validate-detector")
    val_parser.add_argument("--config-dir", default="configs")
    val_parser.add_argument("--data-yaml")
    val_parser.add_argument("--weights")
    val_parser.add_argument("--split", default="val")
    val_parser.add_argument("--project", default="runs/detect")
    val_parser.add_argument("--name", default="val")

    export_detector_parser = subparsers.add_parser("export-detector")
    export_detector_parser.add_argument("--config-dir", default="configs")
    export_detector_parser.add_argument("--weights")
    export_detector_parser.add_argument("--format")
    export_detector_parser.add_argument("--imgsz", type=int)

    infer_parser = subparsers.add_parser("infer-detector")
    infer_parser.add_argument("--config-dir", default="configs")
    infer_parser.add_argument("--image", required=True)
    infer_parser.add_argument("--output-dir", default="artifacts/detections")
    infer_parser.add_argument("--weights")

    build_parser = subparsers.add_parser("build-index")
    build_parser.add_argument("--config-dir", default="configs")

    evaluate_parser = subparsers.add_parser("evaluate-baseline")
    evaluate_parser.add_argument("--config-dir", default="configs")
    evaluate_parser.add_argument("--baseline-csv")
    evaluate_parser.add_argument("--report-name", default="baseline_report")
    evaluate_parser.add_argument("--topk", type=int, default=3)
    evaluate_parser.add_argument("--compare-to")

    residual_parser = subparsers.add_parser("train-residual")
    residual_parser.add_argument("--config-dir", default="configs")
    residual_parser.add_argument("--baseline-csv")
    residual_parser.add_argument("--num-boost-round", type=int, default=50)

    retrieve_parser = subparsers.add_parser("retrieve-similar")
    retrieve_parser.add_argument("--config-dir", default="configs")
    retrieve_parser.add_argument("--image", required=True)
    retrieve_parser.add_argument("--topk", type=int, default=3)

    quote_parser = subparsers.add_parser("quote-image")
    quote_parser.add_argument("--config-dir", default="configs")
    quote_parser.add_argument("--image", required=True)
    quote_parser.add_argument("--topk", type=int, default=3)
    quote_parser.add_argument("--output")

    serve_parser = subparsers.add_parser("serve-api")
    serve_parser.add_argument("--config-dir", default="configs")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    serve_lamp_type_parser = subparsers.add_parser("serve-lamp-type-api")
    serve_lamp_type_parser.add_argument("--host", default="127.0.0.1")
    serve_lamp_type_parser.add_argument("--port", type=int, default=8090)
    serve_lamp_type_parser.add_argument("--project-root", default=".")
    serve_lamp_type_parser.add_argument("--model-id", default="openai/clip-vit-base-patch32")
    serve_lamp_type_parser.add_argument(
        "--labels",
        default="chandelier,ceiling lamp,pendant light,table lamp,desk lamp,floor lamp,wall lamp,spotlight",
    )

    args = parser.parse_args(argv)

    if args.command == "prepare-data":
        _print(prepare_data(args.config_dir, auto_approve_sample=not args.no_auto_approve))
        return 0

    if args.command == "prelabel-sam3":
        _print(
            prelabel_directory(
                raw_dir=args.raw_dir,
                annotation_dir=args.annotation_dir,
                category_name=args.category_name,
                config=load_config(args.config_dir),
                auto_approve=args.auto_approve,
                reviewer=args.reviewer,
            )
        )
        return 0

    if args.command == "download-sam3-community":
        config = load_config(args.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        sam3_config = (config.get("annotation", {}) or {}).get("sam3", {})
        community_config = sam3_config.get("community_checkpoint", {})
        default_output = (
            args.output
            or community_config.get("local_path")
            or sam3_config.get("official", {}).get("checkpoint")
            or "artifacts/models/sam3-community/sam3.safetensors"
        )
        resolved_output = Path(default_output)
        if not resolved_output.is_absolute():
            resolved_output = (root / resolved_output).resolve()
        _print(
            download_community_checkpoint(
                repo_id=args.repo_id or community_config.get("repo_id", "AEmotionStudio/sam3"),
                filename=args.filename or community_config.get("filename", "sam3.safetensors"),
                revision=args.revision or community_config.get("revision", "main"),
                output_path=resolved_output,
                force=args.force,
            )
        )
        return 0

    if args.command == "export-annotations":
        _print(
            export_annotations(
                annotation_dir=args.annotation_dir,
                dataset_dir=args.dataset_dir,
                exports_dir=args.exports_dir,
                category_name=args.category_name,
            )
        )
        return 0

    if args.command == "export-training-version":
        config = load_config(args.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        _print(
            export_training_version(
                annotation_dir=args.annotation_dir or str((root / config["paths"]["annotation_dir"]).resolve()),
                dataset_dir=args.dataset_dir or str((root / config["paths"]["detection_dataset_dir"]).resolve()),
                exports_dir=args.exports_dir or str((root / config["paths"]["annotation_exports_dir"]).resolve()),
                category_name=args.category_name or config["project"]["default_category_name"],
                version_tag=args.version_tag,
                version_root=args.version_root or str((root / config["paths"].get("dataset_version_dir", "artifacts/dataset_versions")).resolve()),
                decision_file=args.decision_file,
                reviewer=args.reviewer,
                note=args.note,
                overwrite=args.overwrite,
            )
        )
        return 0

    if args.command == "review-annotation":
        _print(review_annotation(args.annotation_file, args.status, args.reviewer, args.note))
        return 0

    if args.command == "audit-annotations":
        config = load_config(args.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        annotation_dir = args.annotation_dir or str((root / config["paths"]["annotation_dir"]).resolve())
        output_dir = args.output_dir or str((root / config["paths"]["annotation_review_dir"]).resolve())
        _print(
            generate_review_dashboard(
                annotation_dir=annotation_dir,
                output_dir=output_dir,
                status_filter=args.status_filter,
                sample_size=args.sample_size,
                seed=args.seed,
            )
        )
        return 0

    if args.command == "apply-review-decisions":
        _print(apply_review_decisions(args.decision_file, args.reviewer))
        return 0

    if args.command == "train-detector":
        config = load_config(args.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        detector = YoloTransformerDetector(config)
        data_yaml = args.data_yaml or str(root / config["paths"]["detection_dataset_dir"] / "dataset.yaml")
        _print(
            detector.train(
                data_yaml,
                args.epochs,
                args.imgsz or int(config["detector"].get("train_image_size", 320)),
                args.batch or int(config["detector"].get("train_batch", 1)),
                args.project or config["detector"].get("train_project", "runs/detect"),
                args.name or config["detector"].get("train_name", "rtdetr-lamp"),
            )
        )
        return 0

    if args.command == "validate-detector":
        config = load_config(args.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        detector = YoloTransformerDetector(config)
        data_yaml = args.data_yaml or str(root / config["paths"]["detection_dataset_dir"] / "dataset.yaml")
        weights = args.weights or str(detector.default_promoted_weights())
        _print(detector.validate(data_yaml=data_yaml, split=args.split, weights=weights, project=args.project, name=args.name))
        return 0

    if args.command == "export-detector":
        config = load_config(args.config_dir)
        detector = YoloTransformerDetector(config)
        weights = args.weights or str(detector.default_promoted_weights())
        _print(
            detector.export(
                export_format=args.format or config["detector"].get("export_format", "torchscript"),
                weights=weights,
                imgsz=args.imgsz or int(config["detector"].get("train_image_size", 320)),
            )
        )
        return 0

    if args.command == "infer-detector":
        config = load_config(args.config_dir)
        detector = YoloTransformerDetector(config)
        detection = detector.infer(args.image, weights=args.weights)
        detector.save_crops(args.image, detection.detections, args.output_dir)
        output_path = Path(args.output_dir) / f"{Path(args.image).stem}_detections.json"
        save_json(output_path, detection.to_dict())
        _print({"output_path": str(output_path.resolve()), "result": detection.to_dict()})
        return 0

    if args.command == "build-index":
        config = load_config(args.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        catalog_rows = load_catalog(root / config["paths"]["catalog_csv"])
        embedder = OpenClipEmbedder(config)
        vectors = [embedder.embed_image(root / row["image_path"]) for row in catalog_rows]
        index = FaissCatalogIndex(
            root / config["retrieval"]["faiss_index_path"],
            root / config["retrieval"]["faiss_meta_path"],
        )
        _print(index.build(vectors, catalog_rows))
        return 0

    if args.command == "evaluate-baseline":
        _print(
            evaluate_baseline(
                config_dir=args.config_dir,
                baseline_csv=args.baseline_csv,
                report_name=args.report_name,
                topk=args.topk,
                compare_to=args.compare_to,
            )
        )
        return 0

    if args.command == "train-residual":
        _print(
            train_residual_model(
                config_dir=args.config_dir,
                baseline_csv=args.baseline_csv,
                num_boost_round=args.num_boost_round,
            )
        )
        return 0

    if args.command == "retrieve-similar":
        config = load_config(args.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        embedder = OpenClipEmbedder(config)
        index = FaissCatalogIndex(
            root / config["retrieval"]["faiss_index_path"],
            root / config["retrieval"]["faiss_meta_path"],
        )
        vector = embedder.embed_image(args.image)
        _print({"hits": [item.to_dict() for item in index.search(vector, topk=args.topk)]})
        return 0

    if args.command == "quote-image":
        result = quote_single_image(args.image, config_dir=args.config_dir, topk=args.topk, output_path=args.output)
        _print(result.to_dict())
        return 0

    if args.command == "serve-api":
        serve_api(args.host, args.port, args.config_dir)
        return 0

    if args.command == "serve-lamp-type-api":
        serve_lamp_type_api(
            args.host,
            args.port,
            args.project_root,
            args.model_id,
            [item.strip() for item in str(args.labels).split(",") if item.strip()],
        )
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
