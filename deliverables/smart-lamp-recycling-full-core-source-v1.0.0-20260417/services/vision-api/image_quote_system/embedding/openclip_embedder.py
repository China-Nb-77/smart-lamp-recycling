from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

try:
    import open_clip
    import torch

    HAS_OPEN_CLIP = True
except ImportError:
    open_clip = None
    torch = None
    HAS_OPEN_CLIP = False


class OpenClipEmbedder:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config["embedding"]
        self._model = None
        self._preprocess = None
        self._device = self.config.get("device", "cpu")
        self.backend_name = "openclip" if HAS_OPEN_CLIP else "histogram-fallback"

    def embed_image(self, image_path_or_pil: str | Path | Image.Image) -> np.ndarray:
        if HAS_OPEN_CLIP:
            try:
                return self._embed_with_openclip(image_path_or_pil)
            except Exception:
                self.backend_name = "histogram-fallback"
        return self._embed_with_histogram(image_path_or_pil)

    def _embed_with_openclip(self, image_path_or_pil: str | Path | Image.Image) -> np.ndarray:
        model, preprocess = self._load_model()
        image = image_path_or_pil if isinstance(image_path_or_pil, Image.Image) else Image.open(image_path_or_pil).convert("RGB")
        tensor = preprocess(image).unsqueeze(0).to(self._device)
        with torch.no_grad():
            features = model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].cpu().numpy().astype("float32")

    def _embed_with_histogram(self, image_path_or_pil: str | Path | Image.Image) -> np.ndarray:
        image = image_path_or_pil if isinstance(image_path_or_pil, Image.Image) else Image.open(image_path_or_pil).convert("RGB")
        image = image.resize((128, 128))
        image_np = np.asarray(image).astype(np.float32) / 255.0
        vectors: list[np.ndarray] = []
        for channel in range(3):
            hist, _ = np.histogram(image_np[:, :, channel], bins=32, range=(0.0, 1.0), density=True)
            vectors.append(hist.astype("float32"))
        feature = np.concatenate(vectors).astype("float32")
        norm = np.linalg.norm(feature)
        if norm > 0:
            feature = feature / norm
        return feature

    def _load_model(self):
        if self._model is None or self._preprocess is None:
            model_name = self.config.get("model_name", "ViT-B-32")
            pretrained = self.config.get("pretrained", "laion2b_s34b_b79k")
            self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                model_name,
                pretrained=pretrained,
                device=self._device,
            )
            self._model.eval()
        return self._model, self._preprocess

