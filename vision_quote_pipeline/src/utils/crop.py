from __future__ import annotations

from typing import Iterable

from PIL import Image


def crop_with_padding(image: Image.Image, bbox: tuple[int, int, int, int], pad_ratio: float = 0.05) -> Image.Image:
    x1, y1, x2, y2 = bbox
    w, h = image.size
    bw = x2 - x1
    bh = y2 - y1
    pad_x = int(bw * pad_ratio)
    pad_y = int(bh * pad_ratio)

    nx1 = max(0, x1 - pad_x)
    ny1 = max(0, y1 - pad_y)
    nx2 = min(w, x2 + pad_x)
    ny2 = min(h, y2 + pad_y)
    return image.crop((nx1, ny1, nx2, ny2))
