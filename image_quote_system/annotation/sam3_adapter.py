from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .sam3_checkpoint import build_sam3_image_model_runtime

try:
    from sam3.model_builder import build_sam3_image_model  # type: ignore
    from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore

    HAS_SAM3 = True
except ImportError:
    build_sam3_image_model = None
    Sam3Processor = None
    HAS_SAM3 = False


class Sam3Annotator:
    """
    SAM3 adapter with backend priority:

    1. official in-process predictor
    2. external bridge runtime
    3. foreground-threshold placeholder
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.full_config = config or {}
        sam3_config = (self.full_config.get("annotation", {}) or {}).get("sam3", {})
        self.config = sam3_config
        project_root = (self.full_config.get("project", {}) or {}).get("root_dir", ".")
        self.project_root = Path(project_root).resolve()
        self.backend_name = "sam3-threshold-placeholder"
        self.is_placeholder = True
        self._model = None
        self._processor = None

    def prelabel(self, image_path: str | Path, category_name: str) -> dict[str, Any]:
        image_path = Path(image_path).resolve()
        prompt = self.config.get("text_prompt", category_name)
        backend_priority = self.config.get("backend_priority", ["official", "bridge", "placeholder"])
        backend_errors: list[str] = []

        for backend in backend_priority:
            try:
                if backend == "official":
                    result = self._prelabel_official(image_path, category_name, prompt)
                elif backend == "bridge":
                    result = self._prelabel_bridge(image_path, category_name, prompt)
                else:
                    result = self._prelabel_placeholder(image_path, category_name, prompt)
                result["backend_errors"] = backend_errors
                return result
            except Exception as exc:  # pragma: no cover - env dependent
                backend_errors.append(f"{backend}: {exc}")

        result = self._prelabel_placeholder(image_path, category_name, prompt)
        result["backend_errors"] = backend_errors
        return result

    def _prelabel_official(self, image_path: Path, category_name: str, prompt: str) -> dict[str, Any]:
        if not self.config.get("enabled", True):
            raise RuntimeError("SAM3 official backend disabled in config")
        if not HAS_SAM3:
            raise RuntimeError("sam3 package not installed in current runtime")

        model, processor = self._load_official_predictor()
        image = Image.open(image_path).convert("RGB")
        state = processor.set_image(image)
        output = processor.set_text_prompt(state=state, prompt=prompt)
        mask, bbox, score = self._extract_best_instance(output, image.size)
        self.backend_name = "sam3-official"
        self.is_placeholder = False
        return self._build_result(image_path, category_name, prompt, image.size, mask, bbox, score)

    def _prelabel_bridge(self, image_path: Path, category_name: str, prompt: str) -> dict[str, Any]:
        bridge_cfg = self.config.get("bridge", {})
        python_executable = self._resolve_config_value(bridge_cfg, "python_executable")
        if not python_executable:
            raise RuntimeError("SAM3 bridge python_executable is not configured")

        worker_script = self.project_root / "scripts" / "sam3_bridge_worker.py"
        if not worker_script.exists():
            raise RuntimeError(f"SAM3 bridge worker script not found: {worker_script}")
        working_dir = self._resolve_directory_value(bridge_cfg, "working_dir", default=self.project_root)
        checkpoint = self._resolve_path_value(bridge_cfg, "checkpoint")
        model_cfg = self._resolve_path_value(bridge_cfg, "model_cfg")
        device = self._resolve_config_value(bridge_cfg, "device", default=bridge_cfg.get("device", "cuda"))
        timeout_seconds = int(bridge_cfg.get("timeout_seconds", 120))
        with tempfile.TemporaryDirectory() as temp_dir:
            output_json = Path(temp_dir) / "sam3_output.json"
            command = [
                python_executable,
                str(worker_script),
                "--image",
                str(image_path),
                "--prompt",
                prompt,
                "--output-json",
                str(output_json),
            ]
            if checkpoint:
                command.extend(["--checkpoint", checkpoint])
            if model_cfg:
                command.extend(["--model-cfg", model_cfg])
            if device:
                command.extend(["--device", device])
            completed = subprocess.run(
                command,
                cwd=str(working_dir),
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            if not output_json.exists():
                raise RuntimeError(
                    "SAM3 bridge finished without producing output JSON"
                    + (f"; stdout={completed.stdout.strip()}" if completed.stdout.strip() else "")
                )
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            mask = np.asarray(payload["mask"], dtype=bool)
            bbox = payload["bbox_xyxy"]
            score = float(payload.get("score", 0.0))
        self.backend_name = "sam3-bridge"
        self.is_placeholder = False
        return self._build_result(image_path, category_name, prompt, (payload["width"], payload["height"]), mask, bbox, score)

    def _prelabel_placeholder(self, image_path: Path, category_name: str, prompt: str) -> dict[str, Any]:
        image = Image.open(image_path).convert("RGB")
        image_np = np.array(image)
        mask = self._segment_with_threshold(image_np)
        bbox = self._mask_to_bbox(mask, image_np.shape[1], image_np.shape[0])
        self.backend_name = "sam3-threshold-placeholder"
        self.is_placeholder = True
        return self._build_result(image_path, category_name, prompt, image.size, mask, bbox, 0.0)

    def _build_result(
        self,
        image_path: Path,
        category_name: str,
        prompt: str,
        image_size: tuple[int, int],
        mask: np.ndarray,
        bbox: list[int] | list[float],
        score: float,
    ) -> dict[str, Any]:
        width, height = image_size
        return {
            "image_path": str(image_path.resolve()),
            "width": int(width),
            "height": int(height),
            "sam3_backend": self.backend_name,
            "is_placeholder_backend": self.is_placeholder,
            "prompt": prompt,
            "objects": [
                {
                    "category": category_name,
                    "bbox_xyxy": [int(round(value)) for value in bbox],
                    "sam3_score": round(float(score), 6),
                    "review_status": "pending",
                    "review_note": "auto-prelabel generated",
                }
            ],
            "mask": mask.astype("uint8"),
        }

    def _load_official_predictor(self):
        if self._model is not None and self._processor is not None:
            return self._model, self._processor

        official_cfg = self.config.get("official", {})
        checkpoint = self._resolve_path_value(official_cfg, "checkpoint")
        model_cfg = self._resolve_path_value(official_cfg, "model_cfg")
        device = self._resolve_config_value(official_cfg, "device", default=official_cfg.get("device", "cuda"))
        self._model = build_sam3_image_model_runtime(
            build_sam3_image_model,
            checkpoint_path=checkpoint,
            model_cfg=model_cfg,
            device=device,
        )
        self._processor = Sam3Processor(self._model)
        return self._model, self._processor

    def _extract_best_instance(self, output: dict[str, Any], image_size: tuple[int, int]) -> tuple[np.ndarray, list[int], float]:
        masks = output["masks"]
        boxes = output["boxes"]
        scores = output["scores"]
        if hasattr(scores, "detach"):
            scores_np = scores.detach().cpu().numpy()
        else:
            scores_np = np.asarray(scores)
        if scores_np.size == 0:
            raise RuntimeError("SAM3 returned no instances")
        best_idx = int(np.argmax(scores_np))

        best_mask = masks[best_idx]
        if hasattr(best_mask, "detach"):
            best_mask = best_mask.detach().cpu().numpy()
        best_mask = np.asarray(best_mask)
        if best_mask.ndim > 2:
            best_mask = np.squeeze(best_mask)
        best_mask = best_mask > 0

        best_box = boxes[best_idx]
        if hasattr(best_box, "detach"):
            best_box = best_box.detach().cpu().numpy()
        best_box = np.asarray(best_box).tolist()
        width, height = image_size
        if len(best_box) != 4:
            best_box = self._mask_to_bbox(best_mask, width, height)
        return best_mask, [int(round(v)) for v in best_box], float(scores_np[best_idx])

    def _segment_with_threshold(self, image_np: np.ndarray) -> np.ndarray:
        return np.any(image_np < 220, axis=2)

    @staticmethod
    def _mask_to_bbox(mask: np.ndarray, width: int, height: int) -> list[int]:
        coords = np.argwhere(mask)
        if coords.size == 0:
            return [0, 0, width - 1, height - 1]
        y_min, x_min = coords.min(axis=0).tolist()
        y_max, x_max = coords.max(axis=0).tolist()
        return [int(x_min), int(y_min), int(x_max), int(y_max)]

    def _resolve_config_value(self, section: dict[str, Any], key: str, default: str = "") -> str:
        value = section.get(key, "")
        if value not in {"", None}:
            return str(value)
        env_key = section.get(f"{key}_env", "")
        if env_key:
            env_value = os.environ.get(str(env_key), "")
            if env_value:
                return env_value
        return default

    def _resolve_path_value(self, section: dict[str, Any], key: str) -> str:
        value = self._resolve_config_value(section, key)
        if not value:
            return ""
        return str(self._resolve_path(value))

    def _resolve_directory_value(self, section: dict[str, Any], key: str, default: Path) -> Path:
        value = self._resolve_config_value(section, key)
        if not value:
            return default
        return self._resolve_path(value)

    def _resolve_path(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()
