from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
import torch
torch.cuda.is_available = lambda: False


@dataclass
class SAM3Adapter:
    """Adapter for integrating a local SAM3 checkout into this pipeline.

    The adapter supports three modes:
    1. Real SAM3 image inference via text prompt.
    2. Optional SAM3 geometric box prompt refinement.
    3. Fallback to reading pre-generated mask files when SAM3 is unavailable.
    """

    sam3_root: str | None = None
    checkpoint_path: str | None = None
    device: str = "cpu"
    text_prompt: str = "lamp"
    confidence_threshold: float = 0.5
    model_version: str = "sam3"
    _initialized: bool = field(default=False, init=False, repr=False)
    _processor: Any | None = field(default=None, init=False, repr=False)

    def _candidate_masks(self, image_path: Path) -> list[Path]:
        return [
            image_path.with_suffix(".png"),
            image_path.with_suffix(".jpg"),
            image_path.parent / f"{image_path.stem}.mask.png",
            image_path.parent / f"{image_path.stem}_mask.png",
            image_path.parent.parent / "masks" / f"{image_path.stem}.png",
            image_path.parent.parent / "masks" / f"{image_path.stem}.jpg",
            image_path.parent.parent / "annotations" / f"{image_path.stem}.png",
        ]

    def _load_mask_fallback(self, image_path: Path) -> np.ndarray:
        for candidate in self._candidate_masks(image_path):
            if candidate.exists():
                mask = cv2.imread(str(candidate), cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    return self._binarize(mask)
        raise FileNotFoundError(
            f"未找到 {image_path.name} 对应的 mask，且未成功初始化 SAM3。"
            "请传入 --sam3-root 并准备好依赖/权重，或在图片同级/../masks 下提供 mask 文件。"
        )

    @staticmethod
    def _binarize(mask: np.ndarray) -> np.ndarray:
        mask = np.asarray(mask)
        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        return ((mask > 0) * 255).astype("uint8")

    def _ensure_sys_path(self) -> None:
        if not self.sam3_root:
            return
        sam3_root = Path(self.sam3_root).resolve()
        if not sam3_root.exists():
            raise FileNotFoundError(f"sam3_root 不存在: {sam3_root}")
        if str(sam3_root) not in sys.path:
            sys.path.insert(0, str(sam3_root))

    def _init_sam3(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        if not self.sam3_root:
            return
        self._ensure_sys_path()

        from sam3.model_builder import build_sam3_image_model  # type: ignore
        from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore

        load_from_hf = self.checkpoint_path is None
        torch.set_default_device("cpu")
        model = build_sam3_image_model(
            checkpoint_path=self.checkpoint_path,
            load_from_HF=load_from_hf,
            device=self.device,
        )
        processor = Sam3Processor(
            model,
            device=self.device,
            confidence_threshold=self.confidence_threshold,
        )
        self._processor = processor

    def is_ready(self) -> bool:
        try:
            self._init_sam3()
        except Exception:
            return False
        return self._processor is not None

    def predict_mask(
        self,
        image_path: str | Path,
        text_prompt: str | None = None,
        box_prompt_xyxy: tuple[float, float, float, float] | None = None,
    ) -> np.ndarray:
        """Predict a binary mask for a single image.

        Args:
            image_path: path to input image
            text_prompt: concept prompt, e.g. "lamp", "chandelier", "package box"
            box_prompt_xyxy: optional pixel-space bounding box for refinement.

        Returns:
            uint8 binary mask with foreground as 255.
        """
        image_path = Path(image_path)

        try:
            self._init_sam3()
            if self._processor is None:
                return self._load_mask_fallback(image_path)

            image = Image.open(image_path).convert("RGB")
            state = self._processor.set_image(image)
            prompt = (text_prompt or self.text_prompt).strip()
            output = self._processor.set_text_prompt(prompt=prompt, state=state)

            if box_prompt_xyxy is not None:
                img_w, img_h = image.size
                x1, y1, x2, y2 = box_prompt_xyxy
                cx = ((x1 + x2) / 2.0) / img_w
                cy = ((y1 + y2) / 2.0) / img_h
                w = max(x2 - x1, 1.0) / img_w
                h = max(y2 - y1, 1.0) / img_h
                output = self._processor.add_geometric_prompt(
                    box=[cx, cy, w, h],
                    label=True,
                    state=state,
                )

            masks = output.get("masks") if isinstance(output, dict) else None
            scores = output.get("scores") if isinstance(output, dict) else None
            if masks is None or len(masks) == 0:
                return self._load_mask_fallback(image_path)

            best_idx = 0
            if scores is not None and len(scores) > 0:
                try:
                    best_idx = int(np.argmax(np.asarray(scores)))
                except Exception:
                    best_idx = 0

            best_mask = masks[best_idx]
            if hasattr(best_mask, "detach"):
                best_mask = best_mask.detach().cpu().numpy()
            best_mask = np.asarray(best_mask)
            if best_mask.ndim == 3:
                best_mask = best_mask[0]
            return self._binarize(best_mask)
        except Exception:
            return self._load_mask_fallback(image_path)
