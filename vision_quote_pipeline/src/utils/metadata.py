from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProductRecord:
    id: str
    image_path: str
    material: str
    size_mm: float
    process: str
    base_price: float
    style: str | None = None
    category: str | None = None
    quantity: int | None = None
    urgent: bool | None = None
    region: str | None = None
