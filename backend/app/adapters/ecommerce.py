from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote


def build_taobao_search_url(query: str) -> str:
    return f"https://s.taobao.com/search?q={quote(query)}"


@dataclass(slots=True)
class EcommerceSearchAdapter:
    def search_products(self, query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        normalized = str(query or "").strip()
        if not normalized:
            return []

        try:
            from image_quote_system.recommend_api import LampRecommendService

            payload = LampRecommendService().recommend(normalized, limit=limit)
            results = []
            for item in payload.get("recommendations", [])[:limit]:
                results.append(
                    {
                        "name": str(item.get("title", "")).strip(),
                        "price": float(item.get("price", 0.0) or 0.0),
                        "image": str(item.get("image", "")).strip() or None,
                        "buy_url": str(item.get("link", "")).strip() or build_taobao_search_url(normalized),
                        "platform": "taobao",
                    }
                )
            if results:
                return results
        except Exception:
            pass

        return [
            {
                "name": normalized,
                "price": 0.0,
                "image": None,
                "buy_url": build_taobao_search_url(normalized),
                "platform": "taobao-search",
            }
            for _ in range(limit)
        ]

