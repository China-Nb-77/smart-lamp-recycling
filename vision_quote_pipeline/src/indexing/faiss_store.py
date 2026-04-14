from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
import pandas as pd

from src.utils.io import ensure_dir


@dataclass
class FaissStore:
    dim: int
    index: faiss.Index | None = None
    metadata: pd.DataFrame | None = None

    def create(self) -> None:
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata = pd.DataFrame()

    def add(self, vectors: np.ndarray, metadata: pd.DataFrame) -> None:
        if self.index is None:
            self.create()
        assert self.index is not None
        if vectors.dtype != np.float32:
            vectors = vectors.astype("float32")
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        if self.metadata is None or self.metadata.empty:
            self.metadata = metadata.reset_index(drop=True).copy()
        else:
            self.metadata = pd.concat([self.metadata, metadata.reset_index(drop=True)], ignore_index=True)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> pd.DataFrame:
        if self.index is None or self.metadata is None:
            raise RuntimeError("索引未初始化")
        q = np.asarray(query_vector, dtype="float32").reshape(1, -1)
        faiss.normalize_L2(q)
        scores, indices = self.index.search(q, top_k)
        rows = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = self.metadata.iloc[idx].to_dict()
            item["score"] = float(score)
            rows.append(item)
        return pd.DataFrame(rows)

    def save(self, index_dir: str | Path) -> None:
        if self.index is None or self.metadata is None:
            raise RuntimeError("没有可保存的索引")
        index_dir = ensure_dir(index_dir)
        faiss.write_index(self.index, str(index_dir / "faiss.index"))
        self.metadata.to_parquet(index_dir / "metadata.parquet", index=False)

    @classmethod
    def load(cls, index_dir: str | Path) -> "FaissStore":
        index_dir = Path(index_dir)
        index = faiss.read_index(str(index_dir / "faiss.index"))
        metadata = pd.read_parquet(index_dir / "metadata.parquet")
        store = cls(dim=index.d)
        store.index = index
        store.metadata = metadata
        return store
