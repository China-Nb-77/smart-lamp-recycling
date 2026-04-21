from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from ..io_utils import ensure_dir, save_json
from ..types import DetectionBox, DetectionResult

try:
    from ultralytics import RTDETR  # type: ignore

    HAS_ULTRALYTICS = True
except ImportError:
    RTDETR = None
    HAS_ULTRALYTICS = False


class YoloTransformerDetector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.full_config = config
        self.config = config["detector"]
        self.paths = config["paths"]
        self.category_name = config["project"]["default_category_name"]
        self.project_root = Path(config["project"]["root_dir"]).resolve()
        self.model_registry_root = self.project_root / self.paths.get("detector_model_dir", "artifacts/models/detector")
        self._model = None

    @property
    def preferred_backend(self) -> str:
        return self.config.get("backend", "auto")

    def default_promoted_weights(self, run_name: str | None = None) -> Path:
        target_name = run_name or self.config.get("train_name", "rtdetr-lamp")
        return self.model_registry_root / target_name / "best.pt"

    def train(
        self,
        data_yaml: str,
        epochs: int,
        imgsz: int,
        batch: int,
        project: str,
        name: str,
    ) -> dict[str, Any]:
        if not HAS_ULTRALYTICS:
            return {"status": "placeholder", "reason": "ultralytics not installed"}

        model = self._load_model()
        with self._project_cwd():
            results = model.train(
                data=self._ultra_path(data_yaml),
                epochs=epochs,
                imgsz=imgsz,
                batch=batch,
                project=self._ultra_path(project),
                name=name,
                device=self.config.get("device", "cpu"),
            )
        return self._summarize_train(results, run_name=name)

    def validate(
        self,
        data_yaml: str,
        split: str = "val",
        weights: str | Path | None = None,
        project: str | Path = "runs/detect",
        name: str = "val",
    ) -> dict[str, Any]:
        if not HAS_ULTRALYTICS:
            return {"status": "placeholder", "reason": "ultralytics not installed"}
        model = self._load_model(weights)
        with self._project_cwd():
            result = model.val(
                data=self._ultra_path(data_yaml),
                split=split,
                device=self.config.get("device", "cpu"),
                project=self._ultra_path(project),
                name=name,
            )
        summary = {
            "status": "ok",
            "stage": "val",
            "split": split,
            "weights": str(self._resolve_path(weights).resolve()) if weights else None,
            "save_dir": str(Path(result.save_dir).resolve()),
            "metrics": self._serialize_metrics(getattr(result, "results_dict", {})),
            "speed": getattr(result, "speed", {}),
        }
        if weights:
            weights_path = self._resolve_path(weights)
            summary_path = weights_path.parent / "val_summary.json"
            save_json(summary_path, summary)
            summary["summary_path"] = str(summary_path.resolve())
        return summary

    def export(
        self,
        export_format: str = "torchscript",
        weights: str | Path | None = None,
        imgsz: int | None = None,
    ) -> dict[str, Any]:
        if not HAS_ULTRALYTICS:
            return {"status": "placeholder", "reason": "ultralytics not installed"}
        model = self._load_model(weights)
        with self._project_cwd():
            exported = model.export(
                format=export_format,
                device=self.config.get("device", "cpu"),
                imgsz=imgsz or self.config.get("train_image_size", 320),
            )
        artifact_path = self._resolve_path(exported)
        summary = {
            "status": "ok",
            "stage": "export",
            "format": export_format,
            "weights": str(self._resolve_path(weights).resolve()) if weights else None,
            "artifact": str(artifact_path.resolve()),
        }
        if weights:
            weights_path = self._resolve_path(weights)
            target_path = weights_path.parent / artifact_path.name
            if artifact_path.resolve() != target_path.resolve() and artifact_path.exists():
                ensure_dir(target_path.parent)
                shutil.copy2(artifact_path, target_path)
                summary["artifact"] = str(target_path.resolve())
            summary_path = weights_path.parent / "export_summary.json"
            save_json(summary_path, summary)
            summary["summary_path"] = str(summary_path.resolve())
        return summary

    def infer(self, image_path: str | Path, weights: str | Path | None = None) -> DetectionResult:
        image_path = str(Path(image_path).resolve())
        notes: list[str] = []
        if self.preferred_backend in {"auto", "rtdetr"} and HAS_ULTRALYTICS:
            try:
                result = self._infer_rtdetr(image_path, weights=weights)
                max_confidence = max((item.confidence for item in result.detections), default=0.0)
                acceptance_confidence = float(self.config.get("acceptance_confidence", 0.45))
                if result.detections and max_confidence >= acceptance_confidence:
                    return result
                if result.detections:
                    notes.extend(result.notes)
                    notes.append(
                        "RT-DETR detections were below acceptance confidence; switching to heuristic fallback."
                    )
                elif not self.config.get("fallback_on_empty", True):
                    return result
                else:
                    notes.extend(result.notes)
                    notes.append("RT-DETR returned no detections, switching to heuristic fallback.")
            except Exception as exc:  # pragma: no cover
                notes.append(f"RT-DETR inference failed: {exc}")

        fallback = self._infer_heuristic(image_path)
        fallback.notes = notes + fallback.notes
        fallback.used_fallback = True
        return fallback

    def save_crops(self, image_path: str | Path, detections: list[DetectionBox], output_dir: str | Path) -> list[str]:
        image = Image.open(image_path).convert("RGB")
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []
        for index, detection in enumerate(detections):
            x1, y1, x2, y2 = [int(value) for value in detection.bbox_xyxy]
            crop = image.crop((x1, y1, x2, y2))
            crop_path = target_dir / f"{Path(image_path).stem}_roi_{index}.png"
            crop.save(crop_path)
            detection.crop_path = str(crop_path.resolve())
            paths.append(str(crop_path.resolve()))
        return paths

    def _load_model(self, weights: str | Path | None = None):
        if weights is None and self._model is not None:
            return self._model

        default_weights = weights
        if default_weights is None:
            promoted = self.default_promoted_weights()
            default_weights = promoted if promoted.exists() else self.config.get("rtdetr_weights", "rtdetr-l.pt")
        weight_spec = self._model_spec(default_weights)
        model = RTDETR(weight_spec)
        if weights is None:
            self._model = model
        return model

    def _infer_rtdetr(self, image_path: str, weights: str | Path | None = None) -> DetectionResult:
        model = self._load_model(weights)
        results = model.predict(
            source=image_path,
            conf=self.config.get("confidence", 0.25),
            imgsz=self.config.get("image_size", 640),
            device=self.config.get("device", "cpu"),
            max_det=self.config.get("max_detections", 5),
            verbose=False,
        )
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        result = results[0]
        detections: list[DetectionBox] = []
        if getattr(result, "boxes", None) is not None and result.boxes is not None:
            boxes_xyxy = result.boxes.xyxy.cpu().numpy().tolist()
            confs = result.boxes.conf.cpu().numpy().tolist()
            classes = result.boxes.cls.cpu().numpy().astype(int).tolist()
            names = result.names
            for xyxy, conf, cls_id in zip(boxes_xyxy, confs, classes):
                feature = self._roi_feature(image, xyxy, conf, cls_id)
                area_ratio = ((xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])) / float(width * height)
                detections.append(
                    DetectionBox(
                        bbox_xyxy=[float(v) for v in xyxy],
                        confidence=float(conf),
                        class_id=int(cls_id),
                        label=str(names.get(cls_id, self.category_name)),
                        feature=feature,
                        area_ratio=float(area_ratio),
                    )
                )
        detections = self._filter_detections(detections)
        return DetectionResult(
            image_path=image_path,
            image_size=[width, height],
            backend="rtdetr",
            used_fallback=False,
            detections=detections,
            notes=["Intermediate features are ROI descriptors; true backbone hook extraction is a TODO."],
        )

    def _infer_heuristic(self, image_path: str) -> DetectionResult:
        image = Image.open(image_path).convert("RGB")
        image_np = np.array(image)
        width, height = image.size
        mask = np.any(image_np < 220, axis=2)
        coords = np.argwhere(mask)
        if coords.size == 0:
            bbox = [0.0, 0.0, float(width - 1), float(height - 1)]
        else:
            y_min, x_min = coords.min(axis=0).tolist()
            y_max, x_max = coords.max(axis=0).tolist()
            bbox = [float(x_min), float(y_min), float(x_max), float(y_max)]

        feature = self._roi_feature(image, bbox, 0.5, 0)
        area_ratio = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / float(width * height)
        return DetectionResult(
            image_path=image_path,
            image_size=[width, height],
            backend="heuristic-fallback",
            used_fallback=True,
            detections=[
                DetectionBox(
                    bbox_xyxy=bbox,
                    confidence=0.5,
                    class_id=0,
                    label=self.category_name,
                    feature=feature,
                    area_ratio=float(area_ratio),
                )
            ],
            notes=["Fallback detector uses foreground thresholding because RT-DETR did not produce usable boxes."],
        )

    def _roi_feature(self, image: Image.Image, bbox_xyxy: list[float], confidence: float, class_id: int) -> list[float]:
        width, height = image.size
        x1, y1, x2, y2 = [max(0, int(v)) for v in bbox_xyxy]
        x2 = max(x2, x1 + 1)
        y2 = max(y2, y1 + 1)
        crop = image.crop((x1, y1, x2, y2)).resize((64, 64))
        crop_np = np.asarray(crop).astype(np.float32) / 255.0
        hist_r, _ = np.histogram(crop_np[:, :, 0], bins=8, range=(0.0, 1.0), density=True)
        hist_g, _ = np.histogram(crop_np[:, :, 1], bins=8, range=(0.0, 1.0), density=True)
        hist_b, _ = np.histogram(crop_np[:, :, 2], bins=8, range=(0.0, 1.0), density=True)
        geom = np.array(
            [
                x1 / width,
                y1 / height,
                x2 / width,
                y2 / height,
                (x2 - x1) / width,
                (y2 - y1) / height,
                confidence,
                float(class_id),
            ],
            dtype=np.float32,
        )
        feature = np.concatenate([hist_r, hist_g, hist_b, geom]).astype(np.float32)
        norm = float(np.linalg.norm(feature))
        if norm > 0:
            feature = feature / norm
        return feature.tolist()

    def _filter_detections(self, detections: list[DetectionBox]) -> list[DetectionBox]:
        min_area_ratio = float(self.config.get("min_area_ratio", 0.01))
        dedup_iou_threshold = float(self.config.get("dedup_iou_threshold", 0.6))
        sorted_detections = sorted(
            [item for item in detections if item.area_ratio >= min_area_ratio],
            key=lambda item: item.confidence,
            reverse=True,
        )
        filtered: list[DetectionBox] = []
        for detection in sorted_detections:
            if all(self._iou(detection.bbox_xyxy, kept.bbox_xyxy) < dedup_iou_threshold for kept in filtered):
                filtered.append(detection)
        return filtered[: int(self.config.get("max_kept_detections", len(filtered) or 1))]

    def _iou(self, box_a: list[float], box_b: list[float]) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
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

    def _summarize_train(self, results: Any, run_name: str) -> dict[str, Any]:
        save_dir = Path(results.save_dir).resolve()
        weights_dir = save_dir / "weights"
        registry_dir = ensure_dir(self.model_registry_root / run_name)
        best_source = weights_dir / "best.pt"
        last_source = weights_dir / "last.pt"
        best_target = registry_dir / "best.pt"
        last_target = registry_dir / "last.pt"
        if best_source.exists():
            shutil.copy2(best_source, best_target)
        if last_source.exists():
            shutil.copy2(last_source, last_target)

        summary = {
            "status": "ok",
            "stage": "train",
            "run_name": run_name,
            "ultralytics_save_dir": str(save_dir),
            "promoted_model_dir": str(registry_dir.resolve()),
            "best_weights": str(best_target.resolve()) if best_target.exists() else None,
            "last_weights": str(last_target.resolve()) if last_target.exists() else None,
            "results_csv": str((save_dir / "results.csv").resolve()) if (save_dir / "results.csv").exists() else None,
            "metrics": self._serialize_metrics(getattr(results, "results_dict", {})),
            "speed": getattr(results, "speed", {}),
        }
        summary_path = registry_dir / "train_summary.json"
        save_json(summary_path, summary)
        summary["summary_path"] = str(summary_path.resolve())
        return summary

    def _model_spec(self, weights: str | Path) -> str:
        path = Path(weights)
        if not path.is_absolute() and path.parent == Path(".") and not (self.project_root / path).exists():
            return str(path)
        return self._ultra_path(path)

    def _resolve_path(self, path: str | Path) -> Path:
        target = Path(path)
        if not target.is_absolute():
            target = self.project_root / target
        return target.resolve()

    def _ultra_path(self, path: str | Path) -> str:
        target = Path(path)
        if target.is_absolute():
            try:
                return str(target.relative_to(self.project_root))
            except ValueError:
                return str(target)
        return str(target)

    def _serialize_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in metrics.items():
            if hasattr(value, "item"):
                serialized[key] = float(value.item())
            elif isinstance(value, (int, float)):
                serialized[key] = float(value)
            else:
                serialized[key] = value
        return serialized

    @contextmanager
    def _project_cwd(self):
        original = Path.cwd()
        os.chdir(self.project_root)
        try:
            yield
        finally:
            os.chdir(original)
