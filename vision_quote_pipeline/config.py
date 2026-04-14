from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openclip_model: str = os.getenv("OPENCLIP_MODEL", "ViT-B-32")
    openclip_pretrained: str = os.getenv("OPENCLIP_PRETRAINED", "laion2b_s34b_b79k")
    device: str = os.getenv("DEVICE", "cpu")
    image_size: int = int(os.getenv("IMAGE_SIZE", "224"))
    vector_dim: int = int(os.getenv("VECTOR_DIM", "512"))
    top_k: int = int(os.getenv("TOP_K", "5"))


settings = Settings()
