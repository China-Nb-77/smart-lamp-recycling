from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


def mask_to_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        return None
    x1, x2 = int(xs.min()), int(xs.max())
    y1, y2 = int(ys.min()), int(ys.max())
    return x1, y1, x2, y2


def bbox_to_yolo(class_id: int, bbox: tuple[int, int, int, int], width: int, height: int) -> str:
    x1, y1, x2, y2 = bbox
    xc = ((x1 + x2) / 2) / width
    yc = ((y1 + y2) / 2) / height
    w = (x2 - x1) / width
    h = (y2 - y1) / height
    return f"{class_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}"


def save_yolo_label(path: str | Path, labels: Iterable[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for item in labels:
            f.write(item + "\n")


def read_mask(path: str | Path) -> np.ndarray:
    mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"无法读取 mask: {path}")
    return mask
