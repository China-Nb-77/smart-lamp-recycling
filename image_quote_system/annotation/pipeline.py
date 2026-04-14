from __future__ import annotations

import html
import hashlib
import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from ..io_utils import ensure_dir, load_json, save_json, write_csv_rows
from .sam3_adapter import Sam3Annotator


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def prelabel_directory(
    raw_dir: str | Path,
    annotation_dir: str | Path,
    category_name: str,
    config: dict[str, Any] | None = None,
    auto_approve: bool = False,
    reviewer: str = "",
) -> dict[str, Any]:
    raw_root = Path(raw_dir)
    ann_root = ensure_dir(annotation_dir)
    mask_root = ensure_dir(ann_root / "masks")
    json_root = ensure_dir(ann_root / "records")

    annotator = Sam3Annotator(config)
    outputs: list[str] = []
    for image_path in sorted(raw_root.glob("*.png")):
        result = annotator.prelabel(image_path, category_name)
        annotation = {k: v for k, v in result.items() if k != "mask"}
        if auto_approve:
            annotation["objects"][0]["review_status"] = "approved"
            annotation["objects"][0]["reviewer"] = reviewer
            annotation["objects"][0]["reviewed_at"] = _utc_now()
            annotation["objects"][0]["review_note"] = "synthetic sample auto-approved"

        mask_path = mask_root / f"{image_path.stem}.png"
        Image.fromarray((result["mask"] * 255).astype(np.uint8)).save(mask_path)
        annotation["objects"][0]["mask_path"] = str(mask_path.resolve())

        annotation_path = json_root / f"{image_path.stem}.json"
        save_json(annotation_path, annotation)
        outputs.append(str(annotation_path.resolve()))

    return {
        "raw_dir": str(raw_root.resolve()),
        "annotation_dir": str(ann_root.resolve()),
        "records": outputs,
        "backend": annotator.backend_name,
        "placeholder_backend": annotator.is_placeholder,
    }


def review_annotation(annotation_file: str | Path, status: str, reviewer: str, note: str = "") -> dict[str, Any]:
    target = Path(annotation_file)
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["objects"][0]["review_status"] = status
    payload["objects"][0]["reviewer"] = reviewer
    payload["objects"][0]["reviewed_at"] = _utc_now()
    payload["objects"][0]["review_note"] = note
    save_json(target, payload)
    return payload


def apply_review_decisions(decision_file: str | Path, reviewer: str) -> dict[str, Any]:
    decision_path = Path(decision_file)
    payload = load_json(decision_path)
    records = payload["records"] if isinstance(payload, dict) and "records" in payload else payload
    applied = {"approved": 0, "rejected": 0, "pending": 0}
    updated_files: list[str] = []
    for item in records:
        status = item.get("status")
        annotation_file = item.get("annotation_file")
        if status not in {"approved", "rejected", "pending"} or not annotation_file:
            continue
        review_annotation(annotation_file, status=status, reviewer=reviewer, note=item.get("note", ""))
        applied[status] += 1
        updated_files.append(str(Path(annotation_file).resolve()))
    return {
        "decision_file": str(decision_path.resolve()),
        "reviewer": reviewer,
        "applied_counts": applied,
        "updated_files": updated_files,
    }


def generate_review_dashboard(
    annotation_dir: str | Path,
    output_dir: str | Path,
    status_filter: str = "pending",
    sample_size: int | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    annotation_root = Path(annotation_dir) / "records"
    output_root = ensure_dir(output_dir)
    preview_root = ensure_dir(output_root / "previews")

    annotation_files = sorted(annotation_root.glob("*.json"))
    records: list[dict[str, Any]] = []
    for annotation_file in annotation_files:
        payload = json.loads(annotation_file.read_text(encoding="utf-8"))
        obj = payload["objects"][0]
        if status_filter != "all" and obj.get("review_status") != status_filter:
            continue
        records.append(
            {
                "annotation_file": str(annotation_file.resolve()),
                "image_path": payload["image_path"],
                "bbox_xyxy": obj["bbox_xyxy"],
                "status": obj.get("review_status", "pending"),
                "reviewer": obj.get("reviewer", ""),
                "note": obj.get("review_note", ""),
            }
        )

    if sample_size is not None and sample_size < len(records):
        rng = random.Random(seed)
        records = rng.sample(records, sample_size)
        records.sort(key=lambda item: item["annotation_file"])

    for record in records:
        preview_path = preview_root / f"{Path(record['annotation_file']).stem}.png"
        _draw_bbox_preview(record["image_path"], record["bbox_xyxy"], record["status"], preview_path)
        record["preview_path"] = str(preview_path.resolve())
        record["preview_file_name"] = preview_path.name

    decision_template_path = output_root / "review_decisions.template.json"
    save_json(
        decision_template_path,
        {
            "records": [
                {
                    "annotation_file": record["annotation_file"],
                    "status": record["status"],
                    "note": record["note"],
                }
                for record in records
            ]
        },
    )

    html_path = output_root / "index.html"
    html_path.write_text(_build_dashboard_html(records, decision_template_path.name), encoding="utf-8")
    return {
        "annotation_dir": str(Path(annotation_dir).resolve()),
        "output_dir": str(output_root.resolve()),
        "dashboard_path": str(html_path.resolve()),
        "decision_template_path": str(decision_template_path.resolve()),
        "record_count": len(records),
        "status_filter": status_filter,
    }


def _split_name(index: int, total: int) -> str:
    return "val" if total > 1 and index == total - 1 else "train"


def export_annotations(
    annotation_dir: str | Path,
    dataset_dir: str | Path,
    exports_dir: str | Path,
    category_name: str,
) -> dict[str, Any]:
    annotation_root = Path(annotation_dir) / "records"
    dataset_root = ensure_dir(dataset_dir)
    exports_root = ensure_dir(exports_dir)
    if dataset_root.exists():
        shutil.rmtree(dataset_root)
    if exports_root.exists():
        shutil.rmtree(exports_root)
    dataset_root = ensure_dir(dataset_root)
    exports_root = ensure_dir(exports_root)
    bbox_export_path = exports_root / "bboxes.jsonl"
    mask_export_root = ensure_dir(exports_root / "masks")

    images_train = ensure_dir(dataset_root / "images" / "train")
    images_val = ensure_dir(dataset_root / "images" / "val")
    labels_train = ensure_dir(dataset_root / "labels" / "train")
    labels_val = ensure_dir(dataset_root / "labels" / "val")

    annotation_files = sorted(annotation_root.glob("*.json"))
    bbox_export_lines: list[str] = []
    approved_count = 0
    skipped_records: list[dict[str, Any]] = []
    for index, annotation_file in enumerate(annotation_files):
        payload = json.loads(annotation_file.read_text(encoding="utf-8"))
        obj = payload["objects"][0]
        if obj.get("review_status") != "approved":
            skipped_records.append(
                {
                    "annotation_file": str(annotation_file.resolve()),
                    "review_status": obj.get("review_status", "pending"),
                }
            )
            continue
        approved_count += 1

        split = _split_name(index, len(annotation_files))
        source_image = Path(payload["image_path"])
        destination_image = (images_train if split == "train" else images_val) / source_image.name
        destination_label = (labels_train if split == "train" else labels_val) / f"{source_image.stem}.txt"

        shutil.copy2(source_image, destination_image)
        shutil.copy2(Path(obj["mask_path"]), mask_export_root / f"{source_image.stem}.png")

        width = payload["width"]
        height = payload["height"]
        x1, y1, x2, y2 = obj["bbox_xyxy"]
        x_center = ((x1 + x2) / 2) / width
        y_center = ((y1 + y2) / 2) / height
        bbox_width = (x2 - x1) / width
        bbox_height = (y2 - y1) / height
        destination_label.write_text(
            f"0 {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}\n",
            encoding="utf-8",
        )

        bbox_export_lines.append(
            json.dumps(
                {
                    "image_path": str(destination_image.resolve()),
                    "mask_path": str((mask_export_root / f"{source_image.stem}.png").resolve()),
                    "bbox_xyxy": obj["bbox_xyxy"],
                    "category": category_name,
                    "review_status": obj["review_status"],
                },
                ensure_ascii=False,
            )
        )

    bbox_export_path.write_text("\n".join(bbox_export_lines), encoding="utf-8")

    dataset_yaml = dataset_root / "dataset.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                f"path: {dataset_root.resolve()}",
                "train: images/train",
                "val: images/val",
                "names:",
                f"  0: {category_name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "dataset_yaml": str(dataset_yaml.resolve()),
        "bbox_export_path": str(bbox_export_path.resolve()),
        "mask_export_dir": str(mask_export_root.resolve()),
        "dataset_dir": str(dataset_root.resolve()),
        "approved_count": approved_count,
        "skipped_count": len(skipped_records),
        "skipped_records": skipped_records,
    }


def export_training_version(
    annotation_dir: str | Path,
    dataset_dir: str | Path,
    exports_dir: str | Path,
    category_name: str,
    version_tag: str,
    version_root: str | Path,
    decision_file: str | Path | None = None,
    reviewer: str = "",
    note: str = "",
    overwrite: bool = False,
) -> dict[str, Any]:
    if decision_file and not reviewer:
        raise ValueError("reviewer is required when decision_file is provided")

    annotation_root = Path(annotation_dir).resolve()
    dataset_root = Path(dataset_dir).resolve()
    exports_root = Path(exports_dir).resolve()
    version_root_path = ensure_dir(version_root)
    version_dir = version_root_path / version_tag
    if version_dir.exists():
        if not overwrite:
            raise FileExistsError(f"training version already exists: {version_dir}")
        shutil.rmtree(version_dir)
    ensure_dir(version_dir)

    review_summary = None
    decision_snapshot_path = None
    if decision_file:
        review_summary = apply_review_decisions(decision_file, reviewer)
        decision_snapshot_path = version_dir / Path(decision_file).name
        shutil.copy2(decision_file, decision_snapshot_path)

    export_summary = export_annotations(
        annotation_dir=annotation_root,
        dataset_dir=dataset_root,
        exports_dir=exports_root,
        category_name=category_name,
    )

    dataset_snapshot_dir = version_dir / "detection_dataset"
    exports_snapshot_dir = version_dir / "annotation_exports"
    shutil.copytree(dataset_root, dataset_snapshot_dir)
    shutil.copytree(exports_root, exports_snapshot_dir)

    status_rows = _collect_annotation_status_rows(annotation_root)
    status_csv_path = version_dir / "annotation_status.csv"
    write_csv_rows(
        status_csv_path,
        status_rows,
        fieldnames=["annotation_file", "review_status", "reviewer", "reviewed_at", "review_note", "image_path"],
    )

    manifest = {
        "version_tag": version_tag,
        "created_at": _utc_now(),
        "annotation_dir": str(annotation_root),
        "dataset_dir": str(dataset_root),
        "exports_dir": str(exports_root),
        "dataset_snapshot_dir": str(dataset_snapshot_dir.resolve()),
        "exports_snapshot_dir": str(exports_snapshot_dir.resolve()),
        "status_csv": str(status_csv_path.resolve()),
        "category_name": category_name,
        "note": note,
        "review_summary": review_summary,
        "decision_file": str(Path(decision_file).resolve()) if decision_file else None,
        "decision_file_hash": _file_hash(Path(decision_file)) if decision_file else None,
        "decision_snapshot_path": str(decision_snapshot_path.resolve()) if decision_snapshot_path else None,
        "annotation_status_counts": _summarize_annotation_status_rows(status_rows),
        "export_summary": export_summary,
    }
    manifest_path = version_dir / "manifest.json"
    save_json(manifest_path, manifest)
    return {
        "version_tag": version_tag,
        "version_dir": str(version_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "status_csv": str(status_csv_path.resolve()),
        "dataset_snapshot_dir": str(dataset_snapshot_dir.resolve()),
        "exports_snapshot_dir": str(exports_snapshot_dir.resolve()),
        "review_summary": review_summary,
        "export_summary": export_summary,
    }


def _draw_bbox_preview(image_path: str | Path, bbox_xyxy: list[int], status: str, preview_path: str | Path) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    x1, y1, x2, y2 = bbox_xyxy
    color = {"approved": (34, 197, 94), "rejected": (239, 68, 68), "pending": (245, 158, 11)}.get(status, (59, 130, 246))
    draw.rectangle((x1, y1, x2, y2), outline=color, width=4)
    draw.rectangle((x1, max(0, y1 - 28), x1 + 180, y1), fill=color)
    draw.text((x1 + 8, max(0, y1 - 22)), f"{status} {x1},{y1},{x2},{y2}", fill=(255, 255, 255))
    image.save(preview_path)


def _build_dashboard_html(records: list[dict[str, Any]], decision_template_name: str) -> str:
    cards = []
    for index, record in enumerate(records):
        cards.append(
            f"""
            <article class="card" data-index="{index}">
              <img src="previews/{html.escape(record['preview_file_name'])}" alt="preview {index}">
              <div class="meta">
                <div><strong>Annotation</strong>: {html.escape(record['annotation_file'])}</div>
                <div><strong>Status</strong>: <span class="status">{html.escape(record['status'])}</span></div>
                <div><strong>Reviewer</strong>: {html.escape(record['reviewer'] or '-')}</div>
                <div><strong>Note</strong>: {html.escape(record['note'] or '-')}</div>
              </div>
              <div class="controls">
                <label><input type="radio" name="status-{index}" value="approved" {"checked" if record["status"] == "approved" else ""}>通过</label>
                <label><input type="radio" name="status-{index}" value="rejected" {"checked" if record["status"] == "rejected" else ""}>驳回</label>
                <label><input type="radio" name="status-{index}" value="pending" {"checked" if record["status"] == "pending" else ""}>待定</label>
                <input type="text" id="note-{index}" value="{html.escape(record['note'])}" placeholder="审核备注">
              </div>
            </article>
            """
        )

    record_json = json.dumps(
        [
            {
                "annotation_file": record["annotation_file"],
                "status": record["status"],
                "note": record["note"],
            }
            for record in records
        ],
        ensure_ascii=False,
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Annotation Audit</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 24px; background: #f4f4ef; color: #1f2937; }}
    .toolbar {{ display: flex; gap: 12px; align-items: center; margin-bottom: 20px; flex-wrap: wrap; }}
    .toolbar a, .toolbar button {{ border: 0; background: #111827; color: #fff; padding: 10px 14px; border-radius: 10px; cursor: pointer; text-decoration: none; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
    .card {{ background: #fff; border-radius: 18px; overflow: hidden; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08); }}
    .card img {{ width: 100%; height: 280px; object-fit: contain; background: #fafaf9; }}
    .meta, .controls {{ padding: 14px 16px; }}
    .meta div {{ margin-bottom: 8px; word-break: break-all; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; border-top: 1px solid #e5e7eb; }}
    .controls input[type='text'] {{ flex: 1; min-width: 220px; padding: 8px 10px; border-radius: 8px; border: 1px solid #d1d5db; }}
  </style>
</head>
<body>
  <div class="toolbar">
    <button onclick="downloadDecisions()">导出审核结果 JSON</button>
    <a href="{html.escape(decision_template_name)}" download>下载初始模板</a>
    <span>导出后执行：<code>python -m image_quote_system.cli apply-review-decisions --decision-file REVIEW_DECISIONS.json --reviewer your_name</code></span>
  </div>
  <section class="grid">
    {''.join(cards)}
  </section>
  <script>
    const records = {record_json};
    function downloadDecisions() {{
      const payload = {{
        records: records.map((record, index) => {{
          const status = document.querySelector(`input[name="status-${{index}}"]:checked`).value;
          const note = document.getElementById(`note-${{index}}`).value;
          return {{ ...record, status, note }};
        }})
      }};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'review_decisions.json';
      link.click();
      URL.revokeObjectURL(link.href);
    }}
  </script>
</body>
</html>
"""


def _collect_annotation_status_rows(annotation_dir: Path) -> list[dict[str, Any]]:
    annotation_root = annotation_dir / "records"
    rows: list[dict[str, Any]] = []
    for annotation_file in sorted(annotation_root.glob("*.json")):
        payload = json.loads(annotation_file.read_text(encoding="utf-8"))
        obj = payload["objects"][0]
        rows.append(
            {
                "annotation_file": str(annotation_file.resolve()),
                "review_status": obj.get("review_status", "pending"),
                "reviewer": obj.get("reviewer", ""),
                "reviewed_at": obj.get("reviewed_at", ""),
                "review_note": obj.get("review_note", ""),
                "image_path": payload.get("image_path", ""),
            }
        )
    return rows


def _summarize_annotation_status_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"approved": 0, "pending": 0, "rejected": 0}
    for row in rows:
        status = str(row.get("review_status", "pending"))
        summary[status] = summary.get(status, 0) + 1
    return summary


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]
