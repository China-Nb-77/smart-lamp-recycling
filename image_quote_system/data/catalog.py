from __future__ import annotations

from pathlib import Path
from typing import Any

from ..io_utils import read_csv_rows


NUMERIC_FIELDS = {"base_price", "width_mm", "height_mm"}


def load_catalog(catalog_csv: str | Path) -> list[dict[str, Any]]:
    rows = read_csv_rows(catalog_csv)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        parsed: dict[str, Any] = dict(row)
        for field in NUMERIC_FIELDS:
            if field in parsed and parsed[field] not in ("", None):
                parsed[field] = float(parsed[field])
        normalized.append(parsed)
    return normalized

