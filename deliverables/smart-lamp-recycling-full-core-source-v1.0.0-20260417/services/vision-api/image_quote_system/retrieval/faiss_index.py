from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ..types import RetrievalHit

try:
    import faiss  # type: ignore

    HAS_FAISS = True
except ImportError:
    faiss = None
    HAS_FAISS = False


class FaissCatalogIndex:
    def __init__(self, index_path: str | Path, meta_path: str | Path) -> None:
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self.index = None
        self.metadata: list[dict[str, Any]] = []
        self.backend_name = "faiss" if HAS_FAISS else "numpy-fallback"

    def build(self, vectors: list[np.ndarray], metadata: list[dict[str, Any]]) -> dict[str, Any]:
        matrix = np.stack([self._normalize(vector) for vector in vectors]).astype("float32")
        self.metadata = metadata
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if HAS_FAISS:
            index = faiss.IndexFlatIP(matrix.shape[1])
            index.add(matrix)
            serialized = faiss.serialize_index(index)
            self.index_path.write_bytes(serialized.tobytes())
            self.index = index
        else:
            np.save(self.index_path.with_suffix(".npy"), matrix)
            self.index = matrix
            self.backend_name = "numpy-fallback"
        self.meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "index_path": str(self.index_path.resolve()),
            "meta_path": str(self.meta_path.resolve()),
            "size": len(metadata),
        }

    def load(self) -> None:
        self.metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
        if HAS_FAISS and self.index_path.exists():
            raw = np.frombuffer(self.index_path.read_bytes(), dtype="uint8")
            self.index = faiss.deserialize_index(raw)
            self.backend_name = "faiss"
        else:
            self.index = np.load(self.index_path.with_suffix(".npy"))
            self.backend_name = "numpy-fallback"

    def search(self, vector: np.ndarray, topk: int = 3) -> list[RetrievalHit]:
        if self.index is None:
            self.load()
        query = self._normalize(vector.astype("float32")).reshape(1, -1)
        if HAS_FAISS and self.backend_name == "faiss":
            scores, indices = self.index.search(query, topk)
            pairs = zip(indices[0].tolist(), scores[0].tolist())
        else:
            matrix = self.index
            scores = matrix @ query[0]
            indices = np.argsort(scores)[::-1][:topk]
            pairs = [(int(idx), float(scores[idx])) for idx in indices]

        hits: list[RetrievalHit] = []
        for rank, (idx, score) in enumerate(pairs, start=1):
            if idx < 0:
                continue
            hits.append(RetrievalHit(rank=rank, score=float(score), metadata=self.metadata[idx]))
        return hits

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            return vector / norm
        return vector
