from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import open_clip
import torch
from PIL import Image

from config import settings


@dataclass
class OpenCLIPEmbedder:
    model_name: str = settings.openclip_model
    pretrained: str = settings.openclip_pretrained
    device: str = settings.device

    def __post_init__(self) -> None:
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            self.model_name,
            pretrained=self.pretrained,
        )
        self.tokenizer = open_clip.get_tokenizer(self.model_name)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def encode_image(self, image_path: str) -> np.ndarray:
        image = Image.open(image_path).convert("RGB")
        x = self.preprocess(image).unsqueeze(0).to(self.device)
        feat = self.model.encode_image(x)
        feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.squeeze(0).detach().cpu().numpy().astype("float32")

    @torch.no_grad()
    def encode_pil(self, image: Image.Image) -> np.ndarray:
        x = self.preprocess(image.convert("RGB")).unsqueeze(0).to(self.device)
        feat = self.model.encode_image(x)
        feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.squeeze(0).detach().cpu().numpy().astype("float32")
